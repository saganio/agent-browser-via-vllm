"""
Celery tasks for browser test execution
"""

import asyncio
from celery import current_task
from typing import Optional
from datetime import datetime, timezone
import socket

from app.workers.celery_app import celery_app
from app.database import async_session_maker
from app.tests.service import TestService
from app.tests.models import TestStatus
from app.tests.orchestrator import AgentOrchestrator
from app.projects.service import ProjectService
from app.projects.schemas import VLLMConfig


def get_worker_id() -> str:
    """Get unique worker identifier"""
    return f"{socket.gethostname()}-{current_task.request.id[:8]}"


async def _execute_browser_test_async(
    test_run_id: int,
    project_id: int,
    command: str
):
    """Async implementation of browser test execution"""
    
    async with async_session_maker() as db:
        test_service = TestService(db)
        project_service = ProjectService(db)
        
        # Get test run
        # Note: We bypass org filter here since this is internal
        from sqlalchemy import select
        from app.tests.models import TestRun
        
        result = await db.execute(
            select(TestRun).where(TestRun.id == test_run_id)
        )
        test_run = result.scalar_one_or_none()
        
        if not test_run:
            return {"error": "Test run not found"}
        
        # Get project for vLLM config
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        from app.projects.models import Project
        project = result.scalar_one_or_none()
        
        if not project:
            return {"error": "Project not found"}
        
        # Mark as started
        test_run = await test_service.start_test_run(
            test_run,
            worker_id=get_worker_id(),
            celery_task_id=current_task.request.id
        )
        await db.commit()
        
        # Create orchestrator with project's vLLM config
        vllm_config = VLLMConfig(**(project.vllm_config or {}))
        orchestrator = AgentOrchestrator(vllm_config)
        
        sequence = 0
        success = True
        error_message = None
        
        try:
            async for message in orchestrator.execute_command(command, test_run_id):
                # Store each step as a result
                step_type = message.get("type", "unknown")
                data = message.get("data", {})
                
                # Determine success
                step_success = step_type not in ["error"]
                step_error = data.get("error") if step_type == "error" else None
                
                if step_type == "error":
                    success = False
                    error_message = step_error
                
                # Get screenshot path if available
                screenshot_path = None
                if step_type == "tool_result":
                    tool_result = data.get("result", {})
                    if data.get("tool_name") == "browser_screenshot":
                        screenshot_path = tool_result.get("data", {}).get("path")
                
                await test_service.add_test_result(
                    test_run_id=test_run_id,
                    sequence=sequence,
                    step_type=step_type,
                    tool_name=data.get("tool_name"),
                    content=data.get("content") or data.get("message"),
                    data=data,
                    success=step_success,
                    error_message=step_error,
                    screenshot_path=screenshot_path,
                )
                
                sequence += 1
                
                # Update task state for progress tracking
                current_task.update_state(
                    state="PROGRESS",
                    meta={
                        "test_run_id": test_run_id,
                        "sequence": sequence,
                        "step_type": step_type,
                    }
                )
            
            # Mark as completed
            await test_service.complete_test_run(
                test_run,
                success=success,
                error_message=error_message
            )
            
        except Exception as e:
            success = False
            error_message = str(e)
            
            await test_service.add_test_result(
                test_run_id=test_run_id,
                sequence=sequence,
                step_type="error",
                content=str(e),
                success=False,
                error_message=str(e),
            )
            
            await test_service.complete_test_run(
                test_run,
                success=False,
                error_message=str(e)
            )
        
        await db.commit()
        
        return {
            "test_run_id": test_run_id,
            "success": success,
            "error_message": error_message,
            "steps": sequence,
        }


@celery_app.task(bind=True, name="app.workers.tasks.execute_browser_test")
def execute_browser_test(
    self,
    test_run_id: int,
    project_id: int,
    command: str
):
    """
    Execute a browser test.
    
    This is a Celery task that runs the async orchestrator.
    """
    
    # Run the async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(
            _execute_browser_test_async(test_run_id, project_id, command)
        )
        return result
    finally:
        loop.close()
