"""
WebSocket handler for real-time test execution
"""

from fastapi import WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Set
import json
import asyncio
import logging

from app.database import get_db, async_session_maker
from app.auth.jwt import decode_token
from app.auth.models import User
from app.projects.models import Project
from app.projects.schemas import VLLMConfig
from app.tests.models import TestRun, TestStatus
from app.tests.service import TestService
from app.tests.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        # Map of test_run_id -> set of websockets
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # Map of websocket -> user_id
        self.websocket_users: Dict[WebSocket, int] = {}
    
    async def connect(self, websocket: WebSocket, test_run_id: int, user_id: int):
        """Connect a websocket to a test run"""
        await websocket.accept()
        
        if test_run_id not in self.active_connections:
            self.active_connections[test_run_id] = set()
        
        self.active_connections[test_run_id].add(websocket)
        self.websocket_users[websocket] = user_id
        
        logger.info(f"WebSocket connected for test run {test_run_id}, user {user_id}")
    
    def disconnect(self, websocket: WebSocket, test_run_id: int):
        """Disconnect a websocket"""
        if test_run_id in self.active_connections:
            self.active_connections[test_run_id].discard(websocket)
            
            if not self.active_connections[test_run_id]:
                del self.active_connections[test_run_id]
        
        if websocket in self.websocket_users:
            del self.websocket_users[websocket]
        
        logger.info(f"WebSocket disconnected for test run {test_run_id}")
    
    async def broadcast(self, test_run_id: int, message: dict):
        """Broadcast a message to all connections watching a test run"""
        if test_run_id not in self.active_connections:
            return
        
        dead_connections = set()
        
        for websocket in self.active_connections[test_run_id]:
            try:
                await websocket.send_json(message)
            except Exception:
                dead_connections.add(websocket)
        
        # Clean up dead connections
        for websocket in dead_connections:
            self.disconnect(websocket, test_run_id)


# Global connection manager
manager = ConnectionManager()


async def authenticate_websocket(websocket: WebSocket) -> tuple[int, int]:
    """
    Authenticate a WebSocket connection.
    Returns (user_id, organization_id) or raises exception.
    """
    # Get token from query params or first message
    token = websocket.query_params.get("token")
    
    if not token:
        # Try to get from subprotocol
        token = websocket.headers.get("sec-websocket-protocol")
    
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        raise Exception("Missing authentication token")
    
    payload = decode_token(token)
    
    if not payload or payload.get("type") != "access":
        await websocket.close(code=4001, reason="Invalid token")
        raise Exception("Invalid token")
    
    user_id = int(payload.get("sub"))
    
    # Get user's organization
    async with async_session_maker() as db:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            await websocket.close(code=4001, reason="User not found or inactive")
            raise Exception("User not found or inactive")
        
        return user_id, user.organization_id


async def websocket_execute_test(
    websocket: WebSocket,
    test_run_id: int
):
    """
    WebSocket endpoint for executing and watching a test run.
    
    Connect to /ws/tests/{test_run_id}/execute?token=<jwt_token>
    """
    
    try:
        user_id, organization_id = await authenticate_websocket(websocket)
    except Exception:
        return
    
    # Verify test run exists and belongs to user's org
    async with async_session_maker() as db:
        result = await db.execute(
            select(TestRun)
            .join(Project)
            .where(
                TestRun.id == test_run_id,
                Project.organization_id == organization_id
            )
        )
        test_run = result.scalar_one_or_none()
        
        if not test_run:
            await websocket.close(code=4004, reason="Test run not found")
            return
        
        # Get project for vLLM config
        result = await db.execute(
            select(Project).where(Project.id == test_run.project_id)
        )
        project = result.scalar_one_or_none()
    
    await manager.connect(websocket, test_run_id, user_id)
    
    try:
        # If test is pending, start execution
        if test_run.status == TestStatus.PENDING:
            await execute_test_with_websocket(
                test_run_id=test_run_id,
                project=project,
                command=test_run.command,
                websocket=websocket
            )
        else:
            # Test already started/finished, just send current status
            await websocket.send_json({
                "type": "status",
                "test_run_id": test_run_id,
                "data": {
                    "status": test_run.status.value,
                    "message": f"Test is {test_run.status.value}"
                }
            })
        
        # Keep connection alive for watching
        while True:
            try:
                # Wait for any messages from client (e.g., cancel request)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                
                message = json.loads(data)
                
                if message.get("action") == "cancel":
                    async with async_session_maker() as db:
                        test_service = TestService(db)
                        result = await db.execute(
                            select(TestRun).where(TestRun.id == test_run_id)
                        )
                        test_run = result.scalar_one_or_none()
                        
                        if test_run and not test_run.is_finished:
                            await test_service.cancel_test_run(test_run)
                            await db.commit()
                            
                            await websocket.send_json({
                                "type": "cancelled",
                                "test_run_id": test_run_id,
                                "data": {"message": "Test cancelled"}
                            })
                
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_json({"type": "ping"})
                
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, test_run_id)


async def execute_test_with_websocket(
    test_run_id: int,
    project: Project,
    command: str,
    websocket: WebSocket
):
    """Execute a test and stream results via WebSocket"""
    
    async with async_session_maker() as db:
        test_service = TestService(db)
        
        # Get test run
        result = await db.execute(
            select(TestRun).where(TestRun.id == test_run_id)
        )
        test_run = result.scalar_one_or_none()
        
        if not test_run:
            return
        
        # Mark as started
        await test_service.start_test_run(test_run, worker_id="websocket")
        await db.commit()
        
        # Create orchestrator
        vllm_config = VLLMConfig(**(project.vllm_config or {}))
        orchestrator = AgentOrchestrator(vllm_config)
        
        success = True
        error_message = None
        sequence = 0
        
        try:
            async for message in orchestrator.execute_command(command, test_run_id):
                # Send to websocket
                await websocket.send_json(message)
                
                # Also broadcast to other watchers
                await manager.broadcast(test_run_id, message)
                
                # Store result
                step_type = message.get("type", "unknown")
                data = message.get("data", {})
                
                step_success = step_type not in ["error"]
                step_error = data.get("error") if step_type == "error" else None
                
                if step_type == "error":
                    success = False
                    error_message = step_error
                
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
            
            # Mark as completed
            result = await db.execute(
                select(TestRun).where(TestRun.id == test_run_id)
            )
            test_run = result.scalar_one_or_none()
            
            if test_run:
                await test_service.complete_test_run(
                    test_run,
                    success=success,
                    error_message=error_message
                )
            
            await db.commit()
            
        except Exception as e:
            logger.error(f"Error executing test {test_run_id}: {e}")
            
            await websocket.send_json({
                "type": "error",
                "test_run_id": test_run_id,
                "sequence": sequence,
                "data": {"error": str(e)}
            })
            
            result = await db.execute(
                select(TestRun).where(TestRun.id == test_run_id)
            )
            test_run = result.scalar_one_or_none()
            
            if test_run:
                await test_service.complete_test_run(
                    test_run,
                    success=False,
                    error_message=str(e)
                )
            
            await db.commit()
