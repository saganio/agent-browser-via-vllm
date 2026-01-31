"""
Test execution API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import math
import json

from app.database import get_db
from app.auth.models import User, Role
from app.auth.dependencies import get_current_active_user, require_role
from app.projects.models import Project
from app.projects.service import ProjectService
from app.projects.schemas import VLLMConfig
from app.tests.models import TestRun, TestResult, TestStatus
from app.tests.schemas import (
    ExecuteTestRequest,
    TestRunResponse,
    TestRunDetailResponse,
    TestRunListResponse,
    TestResultResponse,
    ScheduleCreate,
    ScheduleUpdate,
    ScheduleResponse,
    ScheduleListResponse,
    TestStatusEnum,
)
from app.tests.service import TestService, ScheduleService
from app.tests.orchestrator import AgentOrchestrator
from app.workers.tasks import execute_browser_test


router = APIRouter(prefix="/tests", tags=["Tests"])


def test_run_to_response(test_run: TestRun, project_name: Optional[str] = None, triggered_by_name: Optional[str] = None) -> TestRunResponse:
    """Convert TestRun model to response schema"""
    return TestRunResponse(
        id=test_run.id,
        project_id=test_run.project_id,
        project_name=project_name,
        command=test_run.command,
        status=TestStatusEnum(test_run.status.value),
        triggered_by=test_run.triggered_by,
        triggered_by_name=triggered_by_name,
        trigger_type=test_run.trigger_type,
        worker_id=test_run.worker_id,
        started_at=test_run.started_at,
        completed_at=test_run.completed_at,
        duration_ms=test_run.duration_ms,
        error_message=test_run.error_message,
        created_at=test_run.created_at,
    )


def test_result_to_response(result: TestResult) -> TestResultResponse:
    """Convert TestResult model to response schema"""
    return TestResultResponse(
        id=result.id,
        test_run_id=result.test_run_id,
        sequence=result.sequence,
        step_type=result.step_type,
        tool_name=result.tool_name,
        content=result.content,
        data=result.data or {},
        success=result.success,
        error_message=result.error_message,
        screenshot_path=result.screenshot_path,
        duration_ms=result.duration_ms,
        created_at=result.created_at,
    )


@router.post("/execute", response_model=TestRunResponse, status_code=status.HTTP_201_CREATED)
async def execute_test(
    request: ExecuteTestRequest,
    current_user: User = Depends(require_role([Role.ADMIN, Role.DEVELOPER])),
    db: AsyncSession = Depends(get_db)
):
    """Create a new test run (execution happens via WebSocket or worker)"""
    
    # Verify project exists and belongs to user's org
    project_service = ProjectService(db)
    project = await project_service.get_project(request.project_id, current_user.organization_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Create test run
    test_service = TestService(db)
    test_run = await test_service.create_test_run(
        project_id=request.project_id,
        command=request.command,
        user=current_user,
        trigger_type="manual"
    )
    
    await db.commit()
    
    # Trigger background execution
    execute_browser_test.delay(
        test_run_id=test_run.id,
        project_id=request.project_id,
        command=request.command
    )
    
    return test_run_to_response(test_run, project.name, current_user.name)


@router.get("", response_model=TestRunListResponse)
async def list_test_runs(
    project_id: Optional[int] = None,
    status_filter: Optional[TestStatusEnum] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List test runs for the current organization"""
    
    test_service = TestService(db)
    
    status_enum = TestStatus(status_filter.value) if status_filter else None
    
    test_runs, total = await test_service.list_test_runs(
        organization_id=current_user.organization_id,
        project_id=project_id,
        status=status_enum,
        page=page,
        page_size=page_size
    )
    
    return TestRunListResponse(
        items=[test_run_to_response(tr) for tr in test_runs],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0
    )





# Schedule routes
schedule_router = APIRouter(prefix="/schedules", tags=["Schedules"])


@schedule_router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    data: ScheduleCreate,
    current_user: User = Depends(require_role([Role.ADMIN, Role.DEVELOPER])),
    db: AsyncSession = Depends(get_db)
):
    """Create a new scheduled test"""
    
    schedule_service = ScheduleService(db)
    
    try:
        schedule = await schedule_service.create_schedule(data, current_user.organization_id)
        await db.commit()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    return ScheduleResponse(
        id=schedule.id,
        project_id=schedule.project_id,
        name=schedule.name,
        command=schedule.command,
        cron_expression=schedule.cron_expression,
        timezone=schedule.timezone,
        enabled=schedule.enabled,
        last_run_at=schedule.last_run_at,
        last_run_status=TestStatusEnum(schedule.last_run_status.value) if schedule.last_run_status else None,
        next_run_at=schedule.next_run_at,
        run_count=schedule.run_count,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at,
    )


@schedule_router.get("", response_model=ScheduleListResponse)
async def list_schedules(
    project_id: Optional[int] = None,
    enabled: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List schedules for the current organization"""
    
    schedule_service = ScheduleService(db)
    schedules, total = await schedule_service.list_schedules(
        organization_id=current_user.organization_id,
        project_id=project_id,
        enabled=enabled,
        page=page,
        page_size=page_size
    )
    
    return ScheduleListResponse(
        items=[
            ScheduleResponse(
                id=s.id,
                project_id=s.project_id,
                name=s.name,
                command=s.command,
                cron_expression=s.cron_expression,
                timezone=s.timezone,
                enabled=s.enabled,
                last_run_at=s.last_run_at,
                last_run_status=TestStatusEnum(s.last_run_status.value) if s.last_run_status else None,
                next_run_at=s.next_run_at,
                run_count=s.run_count,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in schedules
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0
    )


@schedule_router.patch("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int,
    data: ScheduleUpdate,
    current_user: User = Depends(require_role([Role.ADMIN, Role.DEVELOPER])),
    db: AsyncSession = Depends(get_db)
):
    """Update a schedule"""
    
    schedule_service = ScheduleService(db)
    schedule = await schedule_service.get_schedule(schedule_id, current_user.organization_id)
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
    schedule = await schedule_service.update_schedule(schedule, data)
    await db.commit()
    
    return ScheduleResponse(
        id=schedule.id,
        project_id=schedule.project_id,
        name=schedule.name,
        command=schedule.command,
        cron_expression=schedule.cron_expression,
        timezone=schedule.timezone,
        enabled=schedule.enabled,
        last_run_at=schedule.last_run_at,
        last_run_status=TestStatusEnum(schedule.last_run_status.value) if schedule.last_run_status else None,
        next_run_at=schedule.next_run_at,
        run_count=schedule.run_count,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at,
    )


@schedule_router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: int,
    current_user: User = Depends(require_role([Role.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """Delete a schedule"""
    
    schedule_service = ScheduleService(db)
    schedule = await schedule_service.get_schedule(schedule_id, current_user.organization_id)
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
    await schedule_service.delete_schedule(schedule)
    await db.commit()
    
    return None


# Include schedule router
router.include_router(schedule_router)


@router.get("/{test_run_id}", response_model=TestRunDetailResponse)
async def get_test_run(
    test_run_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a test run with its results"""
    
    test_service = TestService(db)
    test_run = await test_service.get_test_run(test_run_id, current_user.organization_id)
    
    if not test_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test run not found"
        )
    
    results = await test_service.get_test_results(test_run_id)
    
    response = TestRunDetailResponse(
        id=test_run.id,
        project_id=test_run.project_id,
        command=test_run.command,
        status=TestStatusEnum(test_run.status.value),
        triggered_by=test_run.triggered_by,
        trigger_type=test_run.trigger_type,
        worker_id=test_run.worker_id,
        started_at=test_run.started_at,
        completed_at=test_run.completed_at,
        duration_ms=test_run.duration_ms,
        error_message=test_run.error_message,
        created_at=test_run.created_at,
        results=[test_result_to_response(r) for r in results]
    )
    
    return response


@router.post("/{test_run_id}/cancel", response_model=TestRunResponse)
async def cancel_test_run(
    test_run_id: int,
    current_user: User = Depends(require_role([Role.ADMIN, Role.DEVELOPER])),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a running test"""
    
    test_service = TestService(db)
    test_run = await test_service.get_test_run(test_run_id, current_user.organization_id)
    
    if not test_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test run not found"
        )
    
    if test_run.is_finished:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test run is already finished"
        )
    
    test_run = await test_service.cancel_test_run(test_run)
    await db.commit()
    
    return test_run_to_response(test_run)
