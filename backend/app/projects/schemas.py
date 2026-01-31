"""
Project Pydantic schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class VLLMConfig(BaseModel):
    """vLLM configuration schema"""
    api_url: str = Field(default="http://localhost:8000")
    model_name: str = Field(default="")
    api_key: Optional[str] = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=32768)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)


class TestVLLMConnectionRequest(BaseModel):
    """Schema for testing vLLM connection"""
    api_url: str
    model_name: str
    api_key: Optional[str] = None
    
    
class TestVLLMConnectionResponse(BaseModel):
    """Schema for vLLM connection test response"""
    success: bool
    message: str
    model_name: Optional[str] = None


class BrowserConfig(BaseModel):
    """Browser configuration schema"""
    headless: bool = True
    timeout: int = Field(default=30000, ge=1000, le=120000)
    viewport: Optional[Dict[str, int]] = None
    user_agent: Optional[str] = None


class ProjectCreate(BaseModel):
    """Schema for creating a project"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    vllm_config: Optional[VLLMConfig] = None
    browser_config: Optional[BrowserConfig] = None
    default_commands: Optional[List[str]] = None


class ProjectUpdate(BaseModel):
    """Schema for updating a project"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    vllm_config: Optional[VLLMConfig] = None
    browser_config: Optional[BrowserConfig] = None
    default_commands: Optional[List[str]] = None
    is_active: Optional[bool] = None


class ProjectResponse(BaseModel):
    """Schema for project response"""
    id: int
    name: str
    slug: str
    description: Optional[str]
    organization_id: int
    created_by: int
    created_by_name: Optional[str] = None
    vllm_config: Dict[str, Any]
    browser_config: Dict[str, Any]
    default_commands: List[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    test_run_count: Optional[int] = None
    last_test_run: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Schema for paginated project list"""
    items: List[ProjectResponse]
    total: int
    page: int
    page_size: int
    pages: int
