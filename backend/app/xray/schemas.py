"""
Xray Pydantic schemas for API request/response
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class XrayInstanceTypeEnum(str, Enum):
    CLOUD = "cloud"
    SERVER = "server"


class XrayTestTypeEnum(str, Enum):
    MANUAL = "manual"
    GHERKIN = "gherkin"


class XraySyncStatusEnum(str, Enum):
    PENDING = "pending"
    SYNCING = "syncing"
    SYNCED = "synced"
    FAILED = "failed"


class XrayExportStatusEnum(str, Enum):
    PENDING = "pending"
    EXPORTING = "exporting"
    EXPORTED = "exported"
    FAILED = "failed"
    SKIPPED = "skipped"


class XrayStepStatusEnum(str, Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


# ==================== Config Schemas ====================

class XrayConfigCreate(BaseModel):
    """Create Xray configuration for a project"""
    project_id: int
    instance_type: XrayInstanceTypeEnum
    base_url: str = Field(..., min_length=1, max_length=500)
    
    # Cloud auth
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    
    # Server auth
    username: Optional[str] = None
    api_token: Optional[str] = None
    
    # Jira settings
    jira_project_key: str = Field(..., min_length=1, max_length=50)
    
    # Options
    auto_sync: bool = False
    auto_export: bool = True
    sync_interval_minutes: int = Field(default=60, ge=5, le=1440)


class XrayConfigUpdate(BaseModel):
    """Update Xray configuration"""
    instance_type: Optional[XrayInstanceTypeEnum] = None
    base_url: Optional[str] = Field(None, max_length=500)
    
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    username: Optional[str] = None
    api_token: Optional[str] = None
    
    jira_project_key: Optional[str] = Field(None, max_length=50)
    
    auto_sync: Optional[bool] = None
    auto_export: Optional[bool] = None
    sync_interval_minutes: Optional[int] = Field(None, ge=5, le=1440)
    is_active: Optional[bool] = None


class XrayConfigResponse(BaseModel):
    """Xray configuration response"""
    id: int
    project_id: int
    instance_type: XrayInstanceTypeEnum
    base_url: str
    jira_project_key: str
    
    # Don't expose secrets
    has_cloud_credentials: bool = False
    has_server_credentials: bool = False
    
    auto_sync: bool
    auto_export: bool
    sync_interval_minutes: int
    
    last_sync_at: Optional[datetime] = None
    last_sync_status: Optional[XraySyncStatusEnum] = None
    last_sync_error: Optional[str] = None
    
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== Test Set Schemas ====================

class XrayTestSetResponse(BaseModel):
    """Test Set response"""
    id: int
    xray_config_id: int
    xray_issue_key: str
    xray_issue_id: Optional[str] = None
    
    name: str
    description: Optional[str] = None
    
    sync_status: XraySyncStatusEnum
    last_synced_at: Optional[datetime] = None
    
    labels: List[str] = []
    components: List[str] = []
    fix_versions: List[str] = []
    
    test_count: int
    is_active: bool
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class XrayTestSetListResponse(BaseModel):
    """Paginated test set list"""
    items: List[XrayTestSetResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ==================== Test Schemas ====================

class ManualStep(BaseModel):
    """Manual test step"""
    index: int
    action: str
    data: Optional[str] = ""
    expected: Optional[str] = ""


class XrayTestResponse(BaseModel):
    """Individual test response"""
    id: int
    test_set_id: int
    xray_issue_key: str
    xray_issue_id: Optional[str] = None
    
    name: str
    description: Optional[str] = None
    
    test_type: XrayTestTypeEnum
    manual_steps: List[ManualStep] = []
    gherkin_scenario: Optional[str] = None
    preconditions: Optional[str] = None
    
    priority: Optional[str] = None
    labels: List[str] = []
    rank: int
    
    step_count: int = 0
    is_active: bool
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class XrayTestListResponse(BaseModel):
    """Paginated test list"""
    items: List[XrayTestResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ==================== Step Result Schemas ====================

class XrayStepResultResponse(BaseModel):
    """Step execution result"""
    id: int
    xray_test_id: int
    test_run_id: int
    step_index: int
    step_action: Optional[str] = None
    step_expected: Optional[str] = None
    
    status: XrayStepStatusEnum
    actual_result: Optional[str] = None
    
    screenshot_path: Optional[str] = None
    comment: Optional[str] = None
    
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    
    export_status: XrayExportStatusEnum
    xray_execution_id: Optional[str] = None
    exported_at: Optional[datetime] = None
    export_error: Optional[str] = None
    
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== Execution Schemas ====================

class ExecuteTestSetRequest(BaseModel):
    """Request to execute a test set"""
    test_set_id: int
    test_ids: Optional[List[int]] = None  # Specific tests to run, or all if None
    auto_export: Optional[bool] = None  # Override config setting


class ExecuteTestRequest(BaseModel):
    """Request to execute a single test"""
    xray_test_id: int
    auto_export: Optional[bool] = None


class ExportResultsRequest(BaseModel):
    """Manual export to Xray"""
    test_run_id: int
    comment: Optional[str] = None


class ExportResultsResponse(BaseModel):
    """Export results response"""
    success: bool
    xray_execution_key: Optional[str] = None
    message: str
    exported_count: int = 0
    failed_count: int = 0


# ==================== Sync Schemas ====================

class SyncTestSetsRequest(BaseModel):
    """Request to sync test sets from Xray"""
    test_set_keys: Optional[List[str]] = None  # Specific issue keys (e.g., ["UOTP-1", "UOTP-5"]), or all if None
    force: bool = False  # Force re-sync even if recently synced
    sync_all_project_test_sets: bool = True  # If True and no keys provided, sync all test sets in project


class SyncTestSetsResponse(BaseModel):
    """Sync response"""
    success: bool
    message: str
    synced_count: int = 0
    failed_count: int = 0
    errors: List[str] = []
    debug_info: Optional[dict] = None  # Debug information for troubleshooting


# ==================== Connection Test ====================

class TestConnectionRequest(BaseModel):
    """Test Xray connection"""
    instance_type: XrayInstanceTypeEnum
    base_url: str
    
    # Cloud auth
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    
    # Server auth  
    username: Optional[str] = None
    api_token: Optional[str] = None
    
    jira_project_key: str


class TestConnectionResponse(BaseModel):
    """Connection test result"""
    success: bool
    message: str
    xray_version: Optional[str] = None
    project_name: Optional[str] = None
