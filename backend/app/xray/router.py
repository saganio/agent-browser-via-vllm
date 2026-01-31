"""
Xray API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import math

from app.database import get_db
from app.auth.models import User, Role
from app.auth.dependencies import get_current_active_user, require_role
from app.xray.models import XrayConfig, XrayInstanceType
from app.xray.schemas import (
    XrayConfigCreate, XrayConfigUpdate, XrayConfigResponse,
    XrayTestSetResponse, XrayTestSetListResponse,
    XrayTestResponse, XrayTestListResponse, ManualStep,
    XrayStepResultResponse,
    ExecuteTestSetRequest, ExecuteTestRequest,
    SyncTestSetsRequest, SyncTestSetsResponse,
    ExportResultsRequest, ExportResultsResponse,
    TestConnectionRequest, TestConnectionResponse,
    XrayInstanceTypeEnum, XrayTestTypeEnum, XraySyncStatusEnum, XrayExportStatusEnum, XrayStepStatusEnum,
)
from app.xray.service import XrayService
from app.xray.client import get_xray_client, XrayClientError
from app.tests.service import TestService
from app.tests.schemas import TestRunResponse
from app.workers.tasks import execute_browser_test
from app.tests.models import TestRun


router = APIRouter(prefix="/xray", tags=["Xray"])


# ==================== Config helpers ====================

def config_to_response(config: XrayConfig) -> XrayConfigResponse:
    """Convert XrayConfig model to response"""
    return XrayConfigResponse(
        id=config.id,
        project_id=config.project_id,
        instance_type=XrayInstanceTypeEnum(config.instance_type.value),
        base_url=config.base_url,
        jira_project_key=config.jira_project_key,
        has_cloud_credentials=bool(config.client_id and config.client_secret),
        has_server_credentials=bool(config.username and config.api_token),
        auto_sync=config.auto_sync,
        auto_export=config.auto_export,
        sync_interval_minutes=config.sync_interval_minutes,
        last_sync_at=config.last_sync_at,
        last_sync_status=XraySyncStatusEnum(config.last_sync_status.value) if config.last_sync_status else None,
        last_sync_error=config.last_sync_error,
        is_active=config.is_active,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


def test_set_to_response(test_set) -> XrayTestSetResponse:
    """Convert XrayTestSet model to response"""
    return XrayTestSetResponse(
        id=test_set.id,
        xray_config_id=test_set.xray_config_id,
        xray_issue_key=test_set.xray_issue_key,
        xray_issue_id=test_set.xray_issue_id,
        name=test_set.name,
        description=test_set.description,
        sync_status=XraySyncStatusEnum(test_set.sync_status.value),
        last_synced_at=test_set.last_synced_at,
        labels=test_set.labels or [],
        components=test_set.components or [],
        fix_versions=test_set.fix_versions or [],
        test_count=test_set.test_count,
        is_active=test_set.is_active,
        created_at=test_set.created_at,
        updated_at=test_set.updated_at,
    )


def _extract_step_value(value) -> str:
    """Extract string value from Xray step field.
    
    Xray can return step fields as either:
    - Plain string: "do something"
    - Dict with raw/rendered: {"raw": "do something", "rendered": "<p>do something</p>"}
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        # Prefer 'raw' over 'rendered' for cleaner text
        return value.get("raw", value.get("rendered", ""))
    return str(value)


def test_to_response(test) -> XrayTestResponse:
    """Convert XrayTest model to response"""
    return XrayTestResponse(
        id=test.id,
        test_set_id=test.test_set_id,
        xray_issue_key=test.xray_issue_key,
        xray_issue_id=test.xray_issue_id,
        name=test.name,
        description=test.description,
        test_type=XrayTestTypeEnum(test.test_type.value),
        manual_steps=[
            ManualStep(
                index=s.get("index", 0),
                action=_extract_step_value(s.get("action", "")),
                data=_extract_step_value(s.get("data", "")),
                expected=_extract_step_value(s.get("expected", "")),
            )
            for s in (test.manual_steps or [])
        ],
        gherkin_scenario=test.gherkin_scenario,
        preconditions=test.preconditions,
        priority=test.priority,
        labels=test.labels or [],
        rank=test.rank,
        step_count=test.step_count,
        is_active=test.is_active,
        created_at=test.created_at,
        updated_at=test.updated_at,
    )


def step_result_to_response(result) -> XrayStepResultResponse:
    """Convert XrayStepResult to response"""
    return XrayStepResultResponse(
        id=result.id,
        xray_test_id=result.xray_test_id,
        test_run_id=result.test_run_id,
        step_index=result.step_index,
        step_action=result.step_action,
        step_expected=result.step_expected,
        status=XrayStepStatusEnum(result.status.value),
        actual_result=result.actual_result,
        screenshot_path=result.screenshot_path,
        comment=result.comment,
        started_at=result.started_at,
        completed_at=result.completed_at,
        duration_ms=result.duration_ms,
        export_status=XrayExportStatusEnum(result.export_status.value),
        xray_execution_id=result.xray_execution_id,
        exported_at=result.exported_at,
        export_error=result.export_error,
        created_at=result.created_at,
    )


# ==================== Config Routes ====================

@router.post("/config", response_model=XrayConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_xray_config(
    data: XrayConfigCreate,
    current_user: User = Depends(require_role([Role.ADMIN, Role.DEVELOPER])),
    db: AsyncSession = Depends(get_db),
):
    """Create Xray configuration for a project"""
    service = XrayService(db)
    
    try:
        config = await service.create_config(data, current_user.organization_id)
        await db.commit()
        return config_to_response(config)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/config/{project_id}", response_model=XrayConfigResponse)
async def get_xray_config(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get Xray configuration for a project"""
    service = XrayService(db)
    config = await service.get_config(project_id, current_user.organization_id)
    
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Xray configuration not found")
    
    return config_to_response(config)


@router.patch("/config/{project_id}", response_model=XrayConfigResponse)
async def update_xray_config(
    project_id: int,
    data: XrayConfigUpdate,
    current_user: User = Depends(require_role([Role.ADMIN, Role.DEVELOPER])),
    db: AsyncSession = Depends(get_db),
):
    """Update Xray configuration"""
    service = XrayService(db)
    config = await service.get_config(project_id, current_user.organization_id)
    
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Xray configuration not found")
    
    config = await service.update_config(config, data)
    await db.commit()
    return config_to_response(config)


@router.delete("/config/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_xray_config(
    project_id: int,
    current_user: User = Depends(require_role([Role.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """Delete Xray configuration"""
    service = XrayService(db)
    config = await service.get_config(project_id, current_user.organization_id)
    
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Xray configuration not found")
    
    await service.delete_config(config)
    await db.commit()
    return None


@router.post("/config/test-connection", response_model=TestConnectionResponse)
async def test_xray_connection(
    data: TestConnectionRequest,
    current_user: User = Depends(require_role([Role.ADMIN, Role.DEVELOPER])),
    db: AsyncSession = Depends(get_db),
):
    """Test Xray connection without saving config"""
    # Create a temporary config object
    temp_config = XrayConfig(
        project_id=0,
        instance_type=XrayInstanceType(data.instance_type.value),
        base_url=data.base_url,
        client_id=data.client_id,
        client_secret=data.client_secret,
        username=data.username,
        api_token=data.api_token,
        jira_project_key=data.jira_project_key,
    )
    
    try:
        async with get_xray_client(temp_config) as client:
            result = await client.test_connection()
            return TestConnectionResponse(
                success=result.get("success", False),
                message=result.get("message", ""),
                xray_version=result.get("xray_version"),
            )
    except XrayClientError as e:
        return TestConnectionResponse(
            success=False,
            message=str(e),
        )


# ==================== Sync Routes ====================

@router.get("/debug/{project_id}")
async def debug_xray_connection(
    project_id: int,
    current_user: User = Depends(require_role([Role.ADMIN, Role.DEVELOPER])),
    db: AsyncSession = Depends(get_db),
):
    """Debug Xray connection - list available issue types and test a search"""
    import urllib.parse
    
    service = XrayService(db)
    config = await service.get_config(project_id, current_user.organization_id)
    
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Xray configuration not found")
    
    debug_info = {
        "project_key": config.jira_project_key,
        "instance_type": config.instance_type.value,
        "base_url": config.base_url,
    }
    
    try:
        async with get_xray_client(config) as client:
            await client.authenticate()
            debug_info["auth_status"] = "success"
            
            # Get all issue types
            try:
                types_url = f"{config.base_url}/rest/api/2/issuetype"
                headers = client._get_auth_headers()
                
                async with client._session.get(types_url, headers=headers) as response:
                    if response.status == 200:
                        all_types = await response.json()
                        debug_info["all_issue_types"] = [t.get("name") for t in all_types]
                        debug_info["xray_related_types"] = [
                            t.get("name") for t in all_types 
                            if "test" in t.get("name", "").lower() or "xray" in t.get("name", "").lower()
                        ]
            except Exception as e:
                debug_info["issue_types_error"] = str(e)
            
            # Try to search for different issue types
            search_results = {}
            for issue_type in ["Test Set", "Test", "Xray Test Set", "Xray Test", "Test Execution"]:
                try:
                    jql = f'project = "{config.jira_project_key}" AND issuetype = "{issue_type}"'
                    encoded_jql = urllib.parse.quote(jql, safe='')
                    search_url = f"{config.base_url}/rest/api/2/search?jql={encoded_jql}&maxResults=5&fields=key,summary"
                    
                    async with client._session.get(search_url, headers=headers) as response:
                        if response.status == 200:
                            result = await response.json()
                            count = result.get("total", 0)
                            issues = [{"key": i.get("key"), "summary": i.get("fields", {}).get("summary")} for i in result.get("issues", [])]
                            search_results[issue_type] = {"count": count, "sample": issues}
                        else:
                            text = await response.text()
                            search_results[issue_type] = {"error": f"Status {response.status}: {text[:200]}"}
                except Exception as e:
                    search_results[issue_type] = {"error": str(e)}
            
            debug_info["search_results"] = search_results
            
    except XrayClientError as e:
        debug_info["auth_status"] = "failed"
        debug_info["auth_error"] = str(e)
    
    return debug_info


@router.post("/sync/{project_id}", response_model=SyncTestSetsResponse)
async def sync_test_sets(
    project_id: int,
    request: SyncTestSetsRequest = SyncTestSetsRequest(),
    current_user: User = Depends(require_role([Role.ADMIN, Role.DEVELOPER])),
    db: AsyncSession = Depends(get_db),
):
    """Sync test sets from Xray"""
    service = XrayService(db)
    config = await service.get_config(project_id, current_user.organization_id)
    
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Xray configuration not found")
    
    result = await service.sync_test_sets(config, request)
    await db.commit()
    return result


# ==================== Test Set Routes ====================

@router.get("/test-sets", response_model=XrayTestSetListResponse)
async def list_test_sets(
    project_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List test sets for a project"""
    service = XrayService(db)
    config = await service.get_config(project_id, current_user.organization_id)
    
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Xray configuration not found")
    
    test_sets, total = await service.list_test_sets(
        config_id=config.id,
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        search=search,
    )
    
    return XrayTestSetListResponse(
        items=[test_set_to_response(ts) for ts in test_sets],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/test-sets/{test_set_id}", response_model=XrayTestSetResponse)
async def get_test_set(
    test_set_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a test set by ID"""
    service = XrayService(db)
    test_set = await service.get_test_set(test_set_id, current_user.organization_id)
    
    if not test_set:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test set not found")
    
    return test_set_to_response(test_set)


@router.get("/test-sets/{test_set_id}/tests", response_model=XrayTestListResponse)
async def list_tests_in_test_set(
    test_set_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List tests in a test set"""
    service = XrayService(db)
    
    tests, total = await service.list_tests(
        test_set_id=test_set_id,
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
    )
    
    return XrayTestListResponse(
        items=[test_to_response(t) for t in tests],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
    )


# ==================== Test Routes ====================

@router.get("/tests/{test_id}", response_model=XrayTestResponse)
async def get_test(
    test_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a test by ID"""
    service = XrayService(db)
    test = await service.get_test(test_id, current_user.organization_id)
    
    if not test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")
    
    return test_to_response(test)


@router.get("/tests/{test_id}/command")
async def get_test_command(
    test_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the natural language command for a test"""
    service = XrayService(db)
    test = await service.get_test(test_id, current_user.organization_id)
    
    if not test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")
    
    command = service.test_to_command(test)
    return {"command": command}


# ==================== Execution Routes ====================

@router.post("/execute/test-set")
async def execute_test_set(
    request: ExecuteTestSetRequest,
    current_user: User = Depends(require_role([Role.ADMIN, Role.DEVELOPER])),
    db: AsyncSession = Depends(get_db),
):
    """Execute a test set (creates test runs for each test)"""
    xray_service = XrayService(db)
    test_service = TestService(db)
    
    # Get test set
    test_set = await xray_service.get_test_set(request.test_set_id, current_user.organization_id)
    if not test_set:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test set not found")
    
    # Get config
    config = await xray_service.get_config_by_id(test_set.xray_config_id, current_user.organization_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Xray configuration not found")
    
    # Get tests to execute
    tests, _ = await xray_service.list_tests(test_set.id, current_user.organization_id, page_size=1000)
    
    if request.test_ids:
        tests = [t for t in tests if t.id in request.test_ids]
    
    if not tests:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No tests to execute")
    
    # Create test runs for each test
    test_runs = []
    for test in tests:
        command = xray_service.test_to_command(test)
        test_run = await test_service.create_test_run(
            project_id=config.project_id,
            command=command,
            user=current_user,
            trigger_type="xray",
        )
        
        # Create step results
        await xray_service.create_step_results(test, test_run)
        
        test_runs.append({
            "test_run_id": test_run.id,
            "xray_test_id": test.id,
            "xray_test_key": test.xray_issue_key,
            "test_name": test.name,
        })
        
        # Trigger background execution
        execute_browser_test.delay(
            test_run_id=test_run.id,
            project_id=config.project_id,
            command=command
        )
    
    await db.commit()
    
    return {
        "message": f"Created {len(test_runs)} test runs",
        "test_set_key": test_set.xray_issue_key,
        "test_runs": test_runs,
        "auto_export": request.auto_export if request.auto_export is not None else config.auto_export,
    }


@router.post("/execute/test")
async def execute_single_test(
    request: ExecuteTestRequest,
    current_user: User = Depends(require_role([Role.ADMIN, Role.DEVELOPER])),
    db: AsyncSession = Depends(get_db),
):
    """Execute a single test"""
    xray_service = XrayService(db)
    test_service = TestService(db)
    
    # Get test
    test = await xray_service.get_test(request.xray_test_id, current_user.organization_id)
    if not test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")
    
    # Get test set and config
    test_set = await xray_service.get_test_set(test.test_set_id, current_user.organization_id)
    if not test_set:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test set not found")
    
    config = await xray_service.get_config_by_id(test_set.xray_config_id, current_user.organization_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Xray configuration not found")
    
    # Create test run
    command = xray_service.test_to_command(test)
    test_run = await test_service.create_test_run(
        project_id=config.project_id,
        command=command,
        user=current_user,
        trigger_type="xray",
    )
    
    # Create step results
    await xray_service.create_step_results(test, test_run)
    
    await db.commit()
    
    # Trigger background execution
    execute_browser_test.delay(
        test_run_id=test_run.id,
        project_id=config.project_id,
        command=command
    )
    
    return {
        "test_run_id": test_run.id,
        "xray_test_id": test.id,
        "xray_test_key": test.xray_issue_key,
        "command": command,
        "auto_export": request.auto_export if request.auto_export is not None else config.auto_export,
    }


# ==================== Export Routes ====================

@router.post("/export/{test_run_id}", response_model=ExportResultsResponse)
async def export_results_to_xray(
    test_run_id: int,
    request: ExportResultsRequest = ExportResultsRequest(test_run_id=0),
    current_user: User = Depends(require_role([Role.ADMIN, Role.DEVELOPER])),
    db: AsyncSession = Depends(get_db),
):
    """Export test run results to Xray"""
    xray_service = XrayService(db)
    test_service = TestService(db)
    
    # Get test run
    test_run = await test_service.get_test_run(test_run_id, current_user.organization_id)
    if not test_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test run not found")
    
    result = await xray_service.export_results(test_run, current_user.organization_id, request.comment)
    await db.commit()
    
    return result


@router.get("/step-results/{test_run_id}")
async def get_step_results(
    test_run_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get Xray step results for a test run"""
    xray_service = XrayService(db)
    test_service = TestService(db)
    
    # Verify access
    test_run = await test_service.get_test_run(test_run_id, current_user.organization_id)
    if not test_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test run not found")
    
    step_results = await xray_service.get_step_results(test_run_id)
    
    return {
        "test_run_id": test_run_id,
        "step_results": [step_result_to_response(sr) for sr in step_results],
    }
