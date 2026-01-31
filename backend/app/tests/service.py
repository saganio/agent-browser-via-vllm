"""
Test execution service layer
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional, List, Tuple
from datetime import datetime, timezone
import math

from app.tests.models import TestRun, TestResult, Schedule, TestStatus
from app.projects.models import Project
from app.auth.models import User
from app.tests.schemas import ScheduleCreate, ScheduleUpdate


class TestService:
    """Service for test execution operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_test_run(
        self,
        project_id: int,
        command: str,
        user: Optional[User] = None,
        trigger_type: str = "manual"
    ) -> TestRun:
        """Create a new test run"""
        
        test_run = TestRun(
            project_id=project_id,
            command=command,
            status=TestStatus.PENDING,
            triggered_by=user.id if user else None,
            trigger_type=trigger_type,
        )
        
        self.db.add(test_run)
        await self.db.flush()
        await self.db.refresh(test_run)
        
        return test_run
    
    async def start_test_run(
        self,
        test_run: TestRun,
        worker_id: Optional[str] = None,
        celery_task_id: Optional[str] = None
    ) -> TestRun:
        """Mark a test run as started"""
        
        test_run.status = TestStatus.RUNNING
        test_run.started_at = datetime.now(timezone.utc)
        test_run.worker_id = worker_id
        test_run.celery_task_id = celery_task_id
        
        await self.db.flush()
        return test_run
    
    async def complete_test_run(
        self,
        test_run: TestRun,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> TestRun:
        """Mark a test run as completed"""
        
        test_run.status = TestStatus.COMPLETED if success else TestStatus.FAILED
        test_run.completed_at = datetime.now(timezone.utc)
        test_run.error_message = error_message
        
        if test_run.started_at:
            duration = test_run.completed_at - test_run.started_at
            test_run.duration_ms = int(duration.total_seconds() * 1000)
        
        await self.db.flush()
        return test_run
    
    async def cancel_test_run(self, test_run: TestRun) -> TestRun:
        """Cancel a test run"""
        
        test_run.status = TestStatus.CANCELLED
        test_run.completed_at = datetime.now(timezone.utc)
        
        await self.db.flush()
        return test_run
    
    async def add_test_result(
        self,
        test_run_id: int,
        sequence: int,
        step_type: str,
        tool_name: Optional[str] = None,
        content: Optional[str] = None,
        data: Optional[dict] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        screenshot_path: Optional[str] = None,
        duration_ms: Optional[int] = None
    ) -> TestResult:
        """Add a result step to a test run"""
        
        result = TestResult(
            test_run_id=test_run_id,
            sequence=sequence,
            step_type=step_type,
            tool_name=tool_name,
            content=content,
            data=data or {},
            success=success,
            error_message=error_message,
            screenshot_path=screenshot_path,
            duration_ms=duration_ms,
        )
        
        self.db.add(result)
        await self.db.flush()
        
        return result
    
    async def get_test_run(
        self,
        test_run_id: int,
        organization_id: int
    ) -> Optional[TestRun]:
        """Get a test run by ID (with organization filter)"""
        
        result = await self.db.execute(
            select(TestRun)
            .join(Project)
            .where(
                TestRun.id == test_run_id,
                Project.organization_id == organization_id
            )
        )
        return result.scalar_one_or_none()
    
    async def list_test_runs(
        self,
        organization_id: int,
        project_id: Optional[int] = None,
        status: Optional[TestStatus] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[TestRun], int]:
        """List test runs for an organization"""
        
        query = (
            select(TestRun)
            .join(Project)
            .where(Project.organization_id == organization_id)
        )
        
        if project_id:
            query = query.where(TestRun.project_id == project_id)
        
        if status:
            query = query.where(TestRun.status == status)
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        query = query.order_by(desc(TestRun.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        test_runs = result.scalars().all()
        
        return list(test_runs), total
    
    async def get_test_results(
        self,
        test_run_id: int
    ) -> List[TestResult]:
        """Get all results for a test run"""
        
        result = await self.db.execute(
            select(TestResult)
            .where(TestResult.test_run_id == test_run_id)
            .order_by(TestResult.sequence)
        )
        return list(result.scalars().all())


class ScheduleService:
    """Service for schedule operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_schedule(
        self,
        data: ScheduleCreate,
        organization_id: int
    ) -> Schedule:
        """Create a new schedule"""
        
        # Verify project belongs to organization
        result = await self.db.execute(
            select(Project).where(
                Project.id == data.project_id,
                Project.organization_id == organization_id
            )
        )
        project = result.scalar_one_or_none()
        
        if not project:
            raise ValueError("Project not found")
        
        schedule = Schedule(
            project_id=data.project_id,
            name=data.name,
            command=data.command,
            cron_expression=data.cron_expression,
            timezone=data.timezone,
            enabled=data.enabled,
        )
        
        self.db.add(schedule)
        await self.db.flush()
        await self.db.refresh(schedule)
        
        return schedule
    
    async def get_schedule(
        self,
        schedule_id: int,
        organization_id: int
    ) -> Optional[Schedule]:
        """Get a schedule by ID"""
        
        result = await self.db.execute(
            select(Schedule)
            .join(Project)
            .where(
                Schedule.id == schedule_id,
                Project.organization_id == organization_id
            )
        )
        return result.scalar_one_or_none()
    
    async def list_schedules(
        self,
        organization_id: int,
        project_id: Optional[int] = None,
        enabled: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Schedule], int]:
        """List schedules for an organization"""
        
        query = (
            select(Schedule)
            .join(Project)
            .where(Project.organization_id == organization_id)
        )
        
        if project_id:
            query = query.where(Schedule.project_id == project_id)
        
        if enabled is not None:
            query = query.where(Schedule.enabled == enabled)
        
        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Pagination
        query = query.order_by(desc(Schedule.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        schedules = result.scalars().all()
        
        return list(schedules), total
    
    async def update_schedule(
        self,
        schedule: Schedule,
        data: ScheduleUpdate
    ) -> Schedule:
        """Update a schedule"""
        
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(schedule, field, value)
        
        await self.db.flush()
        await self.db.refresh(schedule)
        
        return schedule
    
    async def delete_schedule(self, schedule: Schedule) -> None:
        """Delete a schedule"""
        await self.db.delete(schedule)
        await self.db.flush()
    
    async def get_enabled_schedules(self) -> List[Schedule]:
        """Get all enabled schedules"""
        
        result = await self.db.execute(
            select(Schedule).where(Schedule.enabled == True)
        )
        return list(result.scalars().all())
    
    async def update_schedule_run(
        self,
        schedule: Schedule,
        status: TestStatus,
        next_run_at: Optional[datetime] = None
    ) -> Schedule:
        """Update schedule after a run"""
        
        schedule.last_run_at = datetime.now(timezone.utc)
        schedule.last_run_status = status
        schedule.run_count += 1
        
        if next_run_at:
            schedule.next_run_at = next_run_at
        
        await self.db.flush()
        return schedule
