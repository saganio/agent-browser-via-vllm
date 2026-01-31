"""
Test execution Pydantic schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class TestStatusEnum(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecuteTestRequest(BaseModel):
    """Request to execute a test"""
    command: str = Field(..., min_length=1, max_length=5000)
    project_id: int


class TestRunResponse(BaseModel):
    """Test run response"""
    id: int
    project_id: int
    project_name: Optional[str] = None
    command: str
    status: TestStatusEnum
    triggered_by: Optional[int]
    triggered_by_name: Optional[str] = None
    trigger_type: str
    worker_id: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_ms: Optional[int]
    error_message: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TestResultResponse(BaseModel):
    """Test result step response"""
    id: int
    test_run_id: int
    sequence: int
    step_type: str
    tool_name: Optional[str]
    content: Optional[str]
    data: Dict[str, Any]
    success: bool
    error_message: Optional[str]
    screenshot_path: Optional[str]
    duration_ms: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TestRunDetailResponse(TestRunResponse):
    """Detailed test run response with results"""
    results: List[TestResultResponse] = []


class TestRunListResponse(BaseModel):
    """Paginated test run list"""
    items: List[TestRunResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ScheduleCreate(BaseModel):
    """Create a scheduled test"""
    name: str = Field(..., min_length=1, max_length=255)
    project_id: int
    command: str = Field(..., min_length=1, max_length=5000)
    cron_expression: str = Field(..., min_length=9, max_length=100)
    timezone: str = Field(default="UTC", max_length=50)
    enabled: bool = True


class ScheduleUpdate(BaseModel):
    """Update a scheduled test"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    command: Optional[str] = Field(None, min_length=1, max_length=5000)
    cron_expression: Optional[str] = Field(None, min_length=9, max_length=100)
    timezone: Optional[str] = Field(None, max_length=50)
    enabled: Optional[bool] = None


class ScheduleResponse(BaseModel):
    """Schedule response"""
    id: int
    project_id: int
    project_name: Optional[str] = None
    name: str
    command: str
    cron_expression: str
    timezone: str
    enabled: bool
    last_run_at: Optional[datetime]
    last_run_status: Optional[TestStatusEnum]
    next_run_at: Optional[datetime]
    run_count: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ScheduleListResponse(BaseModel):
    """Paginated schedule list"""
    items: List[ScheduleResponse]
    total: int
    page: int
    page_size: int
    pages: int


# WebSocket message types
class WSMessageType(str, Enum):
    STATUS = "status"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    LLM_RESPONSE = "llm_response"
    ERROR = "error"
    COMPLETE = "complete"


class WSMessage(BaseModel):
    """WebSocket message"""
    type: WSMessageType
    test_run_id: int
    sequence: int
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
