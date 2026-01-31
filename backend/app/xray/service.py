"""
Xray service layer for business logic
"""

from typing import Optional, List, Tuple
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
import logging
import asyncio

from app.xray.models import (
    XrayConfig, XrayTestSet, XrayTest, XrayStepResult,
    XrayInstanceType, XrayTestType, XraySyncStatus, XrayExportStatus, XrayStepStatus
)
from app.xray.schemas import (
    XrayConfigCreate, XrayConfigUpdate,
    ExecuteTestSetRequest, ExecuteTestRequest,
    SyncTestSetsRequest, SyncTestSetsResponse,
    ExportResultsRequest, ExportResultsResponse,
)
from app.xray.client import get_xray_client, XrayClientError, XrayNotFoundError, XrayRateLimitError
from app.xray.gherkin import GherkinParser, gherkin_to_prompt
from app.tests.models import TestRun, TestStatus
from app.projects.models import Project

logger = logging.getLogger(__name__)


class XrayService:
    """Service for Xray integration operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.gherkin_parser = GherkinParser()
    
    # ==================== Config Operations ====================
    
    async def get_config(self, project_id: int, organization_id: int) -> Optional[XrayConfig]:
        """Get Xray config for a project"""
        result = await self.db.execute(
            select(XrayConfig)
            .join(Project)
            .where(
                and_(
                    XrayConfig.project_id == project_id,
                    Project.organization_id == organization_id
                )
            )
        )
        return result.scalars().first()
    
    async def get_config_by_id(self, config_id: int, organization_id: int) -> Optional[XrayConfig]:
        """Get Xray config by ID"""
        result = await self.db.execute(
            select(XrayConfig)
            .join(Project)
            .where(
                and_(
                    XrayConfig.id == config_id,
                    Project.organization_id == organization_id
                )
            )
        )
        return result.scalars().first()
    
    async def create_config(self, data: XrayConfigCreate, organization_id: int) -> XrayConfig:
        """Create Xray configuration for a project"""
        # Verify project belongs to organization
        project_result = await self.db.execute(
            select(Project).where(
                and_(
                    Project.id == data.project_id,
                    Project.organization_id == organization_id
                )
            )
        )
        project = project_result.scalars().first()
        if not project:
            raise ValueError("Project not found")
        
        # Check if config already exists
        existing = await self.get_config(data.project_id, organization_id)
        if existing:
            raise ValueError("Xray configuration already exists for this project")
        
        config = XrayConfig(
            project_id=data.project_id,
            instance_type=XrayInstanceType(data.instance_type.value),
            base_url=data.base_url,
            client_id=data.client_id,
            client_secret=data.client_secret,
            username=data.username,
            api_token=data.api_token,
            jira_project_key=data.jira_project_key,
            auto_sync=data.auto_sync,
            auto_export=data.auto_export,
            sync_interval_minutes=data.sync_interval_minutes,
        )
        
        self.db.add(config)
        await self.db.flush()
        return config
    
    async def update_config(self, config: XrayConfig, data: XrayConfigUpdate) -> XrayConfig:
        """Update Xray configuration"""
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if field == "instance_type" and value is not None:
                value = XrayInstanceType(value.value)
            setattr(config, field, value)
        
        await self.db.flush()
        return config
    
    async def delete_config(self, config: XrayConfig) -> None:
        """Delete Xray configuration"""
        await self.db.delete(config)
        await self.db.flush()
    
    async def test_connection(self, config: XrayConfig) -> dict:
        """Test Xray connection"""
        try:
            async with get_xray_client(config) as client:
                result = await client.test_connection()
                return result
        except XrayClientError as e:
            return {
                "success": False,
                "message": str(e),
            }
    
    # ==================== Test Set Operations ====================
    
    async def sync_test_sets(
        self,
        config: XrayConfig,
        request: SyncTestSetsRequest
    ) -> SyncTestSetsResponse:
        """Sync test sets from Xray"""
        synced = 0
        failed = 0
        errors: List[str] = []
        
        logger.info(f"Starting sync for project key: {config.jira_project_key}")
        
        try:
            async with get_xray_client(config) as client:
                await client.authenticate()
                logger.info("Successfully authenticated with Xray")
                
                # Get test sets from Xray
                if request.test_set_keys:
                    # Sync specific test sets with throttling
                    from app.config import settings
                    request_delay = getattr(settings, 'XRAY_REQUEST_DELAY_MS', 200) / 1000
                    
                    test_sets_data = []
                    for idx, key in enumerate(request.test_set_keys):
                        try:
                            ts_data = await client.get_test_set(key)
                            test_sets_data.append(ts_data)
                            
                            # Add delay between fetches to avoid rate limiting
                            if idx < len(request.test_set_keys) - 1:
                                await asyncio.sleep(request_delay)
                        except XrayNotFoundError:
                            errors.append(f"Test set not found: {key}")
                            failed += 1
                        except XrayRateLimitError as e:
                            logger.warning(f"Rate limited while fetching {key}: {e}")
                            errors.append(f"Failed to sync {key}: {str(e)}")
                            failed += 1
                            # Wait longer after rate limit
                            await asyncio.sleep(e.retry_after or 5)
                else:
                    # Sync all test sets for the project
                    logger.info(f"Fetching all test sets for project: {config.jira_project_key}")
                    test_sets_data = await client.get_test_sets(config.jira_project_key)
                    logger.info(f"Found {len(test_sets_data)} test sets from Xray")
                
                # Process each test set with throttling
                from app.config import settings
                request_delay = getattr(settings, 'XRAY_REQUEST_DELAY_MS', 200) / 1000
                
                for idx, ts_data in enumerate(test_sets_data):
                    try:
                        await self._sync_test_set(config, client, ts_data)
                        synced += 1
                        
                        # Add delay between syncs to avoid rate limiting
                        if idx < len(test_sets_data) - 1:
                            await asyncio.sleep(request_delay)
                    except XrayRateLimitError as e:
                        logger.warning(f"Rate limited while syncing {ts_data.get('key')}: {e}")
                        errors.append(f"Failed to sync {ts_data.get('key')}: {str(e)}")
                        failed += 1
                        # Wait longer after rate limit
                        await asyncio.sleep(e.retry_after or 5)
                    except Exception as e:
                        logger.error(f"Failed to sync test set {ts_data.get('key')}: {e}")
                        errors.append(f"Failed to sync {ts_data.get('key')}: {str(e)}")
                        failed += 1
                
                # Update config sync status
                config.last_sync_at = datetime.now(timezone.utc)
                config.last_sync_status = XraySyncStatus.SYNCED if failed == 0 else XraySyncStatus.FAILED
                config.last_sync_error = "; ".join(errors) if errors else None
                
        except XrayClientError as e:
            config.last_sync_status = XraySyncStatus.FAILED
            config.last_sync_error = str(e)
            errors.append(str(e))
        
        await self.db.flush()
        
        # Build debug info
        debug_info = {
            "project_key": config.jira_project_key,
            "instance_type": config.instance_type.value,
            "test_sets_found": len(test_sets_data) if 'test_sets_data' in locals() else 0,
        }
        
        return SyncTestSetsResponse(
            success=failed == 0 and synced > 0,
            message=f"Synced {synced} test sets" + (f", {failed} failed" if failed else "") + (f" (0 test sets found in Xray for project {config.jira_project_key})" if synced == 0 and failed == 0 else ""),
            synced_count=synced,
            failed_count=failed,
            errors=errors,
            debug_info=debug_info,
        )
    
    async def _sync_test_set(self, config: XrayConfig, client, ts_data: dict) -> XrayTestSet:
        """Sync a single test set and its tests"""
        issue_key = ts_data.get("key")
        
        # Find or create test set
        result = await self.db.execute(
            select(XrayTestSet).where(
                and_(
                    XrayTestSet.xray_config_id == config.id,
                    XrayTestSet.xray_issue_key == issue_key
                )
            )
        )
        test_set = result.scalars().first()
        
        if not test_set:
            test_set = XrayTestSet(
                xray_config_id=config.id,
                xray_issue_key=issue_key,
            )
            self.db.add(test_set)
        
        # Update test set data
        test_set.xray_issue_id = ts_data.get("issue_id")
        test_set.name = ts_data.get("summary", issue_key)
        test_set.description = ts_data.get("description")
        test_set.labels = ts_data.get("labels", [])
        test_set.components = ts_data.get("components", [])
        test_set.fix_versions = ts_data.get("fix_versions", [])
        test_set.sync_status = XraySyncStatus.SYNCING
        
        await self.db.flush()
        
        # Get and sync tests in this test set
        tests_data = await client.get_tests_in_test_set(issue_key)
        
        synced_test_keys = set()
        for test_data in tests_data:
            await self._sync_test(test_set, test_data)
            synced_test_keys.add(test_data.get("key"))
        
        # Deactivate tests that are no longer in the test set
        result = await self.db.execute(
            select(XrayTest).where(XrayTest.test_set_id == test_set.id)
        )
        existing_tests = result.scalars().all()
        for test in existing_tests:
            if test.xray_issue_key not in synced_test_keys:
                test.is_active = False
        
        # Update test set counts and status
        test_set.test_count = len(tests_data)
        test_set.sync_status = XraySyncStatus.SYNCED
        test_set.last_synced_at = datetime.now(timezone.utc)
        
        await self.db.flush()
        return test_set
    
    async def _sync_test(self, test_set: XrayTestSet, test_data: dict) -> XrayTest:
        """Sync a single test"""
        issue_key = test_data.get("key")
        
        # Find or create test
        result = await self.db.execute(
            select(XrayTest).where(
                and_(
                    XrayTest.test_set_id == test_set.id,
                    XrayTest.xray_issue_key == issue_key
                )
            )
        )
        test = result.scalars().first()
        
        if not test:
            test = XrayTest(
                test_set_id=test_set.id,
                xray_issue_key=issue_key,
            )
            self.db.add(test)
        
        # Update test data
        test.xray_issue_id = test_data.get("issue_id")
        test.name = test_data.get("summary", issue_key)
        test.description = test_data.get("description")
        test.test_type = XrayTestType(test_data.get("test_type", "manual"))
        test.manual_steps = test_data.get("manual_steps", [])
        test.gherkin_scenario = test_data.get("gherkin_scenario")
        test.preconditions = test_data.get("preconditions")
        test.priority = test_data.get("priority")
        test.labels = test_data.get("labels", [])
        test.rank = test_data.get("rank", 0)
        test.is_active = True
        
        await self.db.flush()
        return test
    
    async def list_test_sets(
        self,
        config_id: int,
        organization_id: int,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
    ) -> Tuple[List[XrayTestSet], int]:
        """List test sets for a config"""
        # Verify config belongs to org
        config = await self.get_config_by_id(config_id, organization_id)
        if not config:
            return [], 0
        
        query = select(XrayTestSet).where(
            and_(
                XrayTestSet.xray_config_id == config_id,
                XrayTestSet.is_active == True
            )
        )
        
        if search:
            query = query.where(
                XrayTestSet.name.ilike(f"%{search}%") |
                XrayTestSet.xray_issue_key.ilike(f"%{search}%")
            )
        
        # Count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0
        
        # Paginate
        query = query.order_by(XrayTestSet.name).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        test_sets = result.scalars().all()
        
        return list(test_sets), total
    
    async def get_test_set(self, test_set_id: int, organization_id: int) -> Optional[XrayTestSet]:
        """Get a test set by ID"""
        result = await self.db.execute(
            select(XrayTestSet)
            .options(selectinload(XrayTestSet.tests))
            .join(XrayConfig)
            .join(Project)
            .where(
                and_(
                    XrayTestSet.id == test_set_id,
                    Project.organization_id == organization_id
                )
            )
        )
        return result.scalars().first()
    
    async def get_test_set_by_key(self, config_id: int, issue_key: str) -> Optional[XrayTestSet]:
        """Get a test set by Xray issue key"""
        result = await self.db.execute(
            select(XrayTestSet)
            .options(selectinload(XrayTestSet.tests))
            .where(
                and_(
                    XrayTestSet.xray_config_id == config_id,
                    XrayTestSet.xray_issue_key == issue_key
                )
            )
        )
        return result.scalars().first()
    
    # ==================== Test Operations ====================
    
    async def list_tests(
        self,
        test_set_id: int,
        organization_id: int,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[XrayTest], int]:
        """List tests in a test set"""
        # Verify access
        test_set = await self.get_test_set(test_set_id, organization_id)
        if not test_set:
            return [], 0
        
        query = select(XrayTest).where(
            and_(
                XrayTest.test_set_id == test_set_id,
                XrayTest.is_active == True
            )
        ).order_by(XrayTest.rank)
        
        # Count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0
        
        # Paginate
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        tests = result.scalars().all()
        
        return list(tests), total
    
    async def get_test(self, test_id: int, organization_id: int) -> Optional[XrayTest]:
        """Get a test by ID"""
        result = await self.db.execute(
            select(XrayTest)
            .join(XrayTestSet)
            .join(XrayConfig)
            .join(Project)
            .where(
                and_(
                    XrayTest.id == test_id,
                    Project.organization_id == organization_id
                )
            )
        )
        return result.scalars().first()
    
    # ==================== Execution Operations ====================
    
    def test_to_command(self, test: XrayTest) -> str:
        """Convert an Xray test to a natural language command for the orchestrator"""
        if test.test_type == XrayTestType.GHERKIN and test.gherkin_scenario:
            # Parse Gherkin and convert to prompt
            return gherkin_to_prompt(test.gherkin_scenario)
        else:
            # Convert manual steps to prompt
            steps_text = []
            if test.preconditions:
                steps_text.append(f"Preconditions: {test.preconditions}")
            
            steps_text.append(f"Test: {test.name}")
            
            if test.description:
                steps_text.append(f"Description: {test.description}")
            
            steps_text.append("\nSteps to execute:")
            for step in test.manual_steps or []:
                idx = step.get("index", 0) + 1
                action = step.get("action", "")
                data = step.get("data", "")
                expected = step.get("expected", "")
                
                step_line = f"{idx}. {action}"
                if data:
                    step_line += f" (with data: {data})"
                if expected:
                    step_line += f" → Expected: {expected}"
                
                steps_text.append(step_line)
            
            return "\n".join(steps_text)
    
    async def create_step_results(
        self,
        test: XrayTest,
        test_run: TestRun
    ) -> List[XrayStepResult]:
        """Create step result placeholders for a test execution"""
        step_results = []
        
        if test.test_type == XrayTestType.GHERKIN and test.gherkin_scenario:
            # Parse Gherkin steps
            scenario = self.gherkin_parser.parse(test.gherkin_scenario)
            for idx, step in enumerate(scenario.steps):
                result = XrayStepResult(
                    xray_test_id=test.id,
                    test_run_id=test_run.id,
                    step_index=idx,
                    step_action=step.text,
                    status=XrayStepStatus.PENDING,
                )
                self.db.add(result)
                step_results.append(result)
        else:
            # Use manual steps
            for idx, step in enumerate(test.manual_steps or []):
                result = XrayStepResult(
                    xray_test_id=test.id,
                    test_run_id=test_run.id,
                    step_index=idx,
                    step_action=step.get("action", ""),
                    step_expected=step.get("expected", ""),
                    status=XrayStepStatus.PENDING,
                )
                self.db.add(result)
                step_results.append(result)
        
        await self.db.flush()
        return step_results
    
    async def update_step_result(
        self,
        step_result_id: int,
        status: XrayStepStatus,
        actual_result: Optional[str] = None,
        screenshot_path: Optional[str] = None,
        comment: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> XrayStepResult:
        """Update a step result"""
        result = await self.db.execute(
            select(XrayStepResult).where(XrayStepResult.id == step_result_id)
        )
        step_result = result.scalars().first()
        
        if step_result:
            step_result.status = status
            step_result.actual_result = actual_result
            step_result.screenshot_path = screenshot_path
            step_result.comment = comment
            step_result.duration_ms = duration_ms
            step_result.completed_at = datetime.now(timezone.utc)
            await self.db.flush()
        
        return step_result
    
    async def get_step_results(self, test_run_id: int) -> List[XrayStepResult]:
        """Get all step results for a test run"""
        result = await self.db.execute(
            select(XrayStepResult)
            .where(XrayStepResult.test_run_id == test_run_id)
            .order_by(XrayStepResult.xray_test_id, XrayStepResult.step_index)
        )
        return list(result.scalars().all())
    
    # ==================== Export Operations ====================
    
    async def export_results(
        self,
        test_run: TestRun,
        organization_id: int,
        comment: Optional[str] = None,
    ) -> ExportResultsResponse:
        """Export test results to Xray"""
        # Get step results for this test run
        step_results = await self.get_step_results(test_run.id)
        
        if not step_results:
            return ExportResultsResponse(
                success=False,
                message="No Xray step results found for this test run",
                exported_count=0,
                failed_count=0,
            )
        
        # Group by test
        tests_by_id: dict = {}
        for sr in step_results:
            if sr.xray_test_id not in tests_by_id:
                tests_by_id[sr.xray_test_id] = []
            tests_by_id[sr.xray_test_id].append(sr)
        
        # Get config from first test
        first_test_id = next(iter(tests_by_id.keys()))
        test = await self.get_test(first_test_id, organization_id)
        if not test:
            return ExportResultsResponse(
                success=False,
                message="Could not find test information",
                exported_count=0,
                failed_count=0,
            )
        
        # Get config
        test_set = await self.get_test_set(test.test_set_id, organization_id)
        if not test_set:
            return ExportResultsResponse(
                success=False,
                message="Could not find test set information",
                exported_count=0,
                failed_count=0,
            )
        
        config = await self.get_config_by_id(test_set.xray_config_id, organization_id)
        if not config:
            return ExportResultsResponse(
                success=False,
                message="Xray configuration not found",
                exported_count=0,
                failed_count=0,
            )
        
        # Build test results for Xray
        test_results = []
        for test_id, steps in tests_by_id.items():
            test_obj = await self.get_test(test_id, organization_id)
            if not test_obj:
                continue
            
            # Determine overall test status
            statuses = [s.status for s in steps]
            if XrayStepStatus.FAILED in statuses:
                overall_status = "FAILED"
            elif all(s == XrayStepStatus.PASSED for s in statuses):
                overall_status = "PASSED"
            elif all(s == XrayStepStatus.SKIPPED for s in statuses):
                overall_status = "SKIPPED"
            else:
                overall_status = "PENDING"
            
            test_result = {
                "test_key": test_obj.xray_issue_key,
                "status": overall_status,
                "comment": comment or f"Executed via Browser Test Platform at {datetime.now(timezone.utc).isoformat()}",
                "steps": [
                    {
                        "status": s.status.value.upper(),
                        "actual_result": s.actual_result or "",
                        "comment": s.comment or "",
                    }
                    for s in sorted(steps, key=lambda x: x.step_index)
                ]
            }
            test_results.append(test_result)
        
        # Export to Xray
        try:
            async with get_xray_client(config) as client:
                await client.authenticate()
                result = await client.create_test_execution(
                    project_key=config.jira_project_key,
                    test_results=test_results,
                    summary=f"Test Execution - {test_run.command[:50]}..." if test_run.command else None,
                    description=comment,
                )
                
                execution_key = result.get("execution_key")
                
                # Update step results with export info
                for sr in step_results:
                    sr.export_status = XrayExportStatus.EXPORTED
                    sr.xray_execution_id = execution_key
                    sr.exported_at = datetime.now(timezone.utc)
                
                await self.db.flush()
                
                return ExportResultsResponse(
                    success=True,
                    xray_execution_key=execution_key,
                    message=f"Successfully exported to Xray: {execution_key}",
                    exported_count=len(test_results),
                    failed_count=0,
                )
                
        except XrayClientError as e:
            # Mark as failed
            for sr in step_results:
                sr.export_status = XrayExportStatus.FAILED
                sr.export_error = str(e)
            
            await self.db.flush()
            
            return ExportResultsResponse(
                success=False,
                message=f"Export failed: {str(e)}",
                exported_count=0,
                failed_count=len(test_results),
            )
