"""
Xray integration SQLAlchemy models
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from typing import Optional, List

from app.database import Base


class XrayInstanceType(str, enum.Enum):
    """Xray instance type"""
    CLOUD = "cloud"
    SERVER = "server"  # Server/Data Center


class XrayTestType(str, enum.Enum):
    """Type of test in Xray"""
    MANUAL = "manual"
    GHERKIN = "gherkin"  # BDD/Cucumber


class XraySyncStatus(str, enum.Enum):
    """Sync status for test sets"""
    PENDING = "pending"
    SYNCING = "syncing"
    SYNCED = "synced"
    FAILED = "failed"


class XrayExportStatus(str, enum.Enum):
    """Export status for test executions"""
    PENDING = "pending"
    EXPORTING = "exporting"
    EXPORTED = "exported"
    FAILED = "failed"
    SKIPPED = "skipped"


class XrayStepStatus(str, enum.Enum):
    """Status for individual test steps"""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class XrayConfig(Base):
    """Xray configuration per project"""
    __tablename__ = "xray_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Project association
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Instance type
    instance_type = Column(Enum(XrayInstanceType), nullable=False)
    
    # Connection settings
    # For Cloud: base_url is cloud.getxray.app
    # For Server: base_url is your Jira Server URL
    base_url = Column(String(500), nullable=False)
    
    # Authentication
    # Cloud: client_id and client_secret for API key auth
    # Server: username and api_token (PAT) for basic auth
    client_id = Column(String(255), nullable=True)  # Cloud only
    client_secret = Column(String(500), nullable=True)  # Cloud only (encrypted)
    username = Column(String(255), nullable=True)  # Server only
    api_token = Column(String(500), nullable=True)  # Server PAT (encrypted)
    
    # Jira project settings
    jira_project_key = Column(String(50), nullable=False)  # e.g., "PROJ"
    
    # Sync settings
    auto_sync = Column(Boolean, default=False)  # Auto-sync test sets periodically
    auto_export = Column(Boolean, default=True)  # Auto-export results after execution
    sync_interval_minutes = Column(Integer, default=60)  # Sync interval
    
    # Last sync info
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_status = Column(Enum(XraySyncStatus), nullable=True)
    last_sync_error = Column(Text, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", backref="xray_config")
    test_sets = relationship("XrayTestSet", back_populates="xray_config", lazy="selectin", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<XrayConfig(id={self.id}, project_id={self.project_id}, type='{self.instance_type}')>"


class XrayTestSet(Base):
    """Cached Test Set from Xray"""
    __tablename__ = "xray_test_sets"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Xray config reference
    xray_config_id = Column(Integer, ForeignKey("xray_configs.id", ondelete="CASCADE"), nullable=False)
    
    # Xray identifiers
    xray_issue_key = Column(String(50), nullable=False, index=True)  # e.g., "PROJ-123"
    xray_issue_id = Column(String(50), nullable=True)  # Internal Xray/Jira ID
    
    # Test set info
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # Sync status
    sync_status = Column(Enum(XraySyncStatus), default=XraySyncStatus.PENDING)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata from Xray
    labels = Column(JSON, default=list)  # Jira labels
    components = Column(JSON, default=list)  # Jira components
    fix_versions = Column(JSON, default=list)  # Fix versions
    
    # Statistics
    test_count = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    xray_config = relationship("XrayConfig", back_populates="test_sets")
    tests = relationship("XrayTest", back_populates="test_set", lazy="selectin", cascade="all, delete-orphan")
    
    # Unique constraint: one test set per xray_issue_key per config
    __table_args__ = (
        # UniqueConstraint('xray_config_id', 'xray_issue_key', name='uq_xray_test_set_key'),
    )
    
    def __repr__(self):
        return f"<XrayTestSet(id={self.id}, key='{self.xray_issue_key}', name='{self.name}')>"


class XrayTest(Base):
    """Individual test within a Test Set"""
    __tablename__ = "xray_tests"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Test set reference
    test_set_id = Column(Integer, ForeignKey("xray_test_sets.id", ondelete="CASCADE"), nullable=False)
    
    # Xray identifiers
    xray_issue_key = Column(String(50), nullable=False, index=True)  # e.g., "PROJ-456"
    xray_issue_id = Column(String(50), nullable=True)
    
    # Test info
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # Test type
    test_type = Column(Enum(XrayTestType), nullable=False)
    
    # For MANUAL tests: array of step objects
    # [{"index": 1, "action": "Click login", "data": "", "expected": "Login form appears"}]
    manual_steps = Column(JSON, default=list)
    
    # For GHERKIN tests: the scenario text
    # "Given I am on the login page\nWhen I enter valid credentials\nThen I should see dashboard"
    gherkin_scenario = Column(Text, nullable=True)
    
    # Pre-conditions and post-conditions
    preconditions = Column(Text, nullable=True)
    
    # Metadata
    priority = Column(String(50), nullable=True)
    labels = Column(JSON, default=list)
    
    # Execution order within test set
    rank = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    test_set = relationship("XrayTestSet", back_populates="tests")
    step_results = relationship("XrayStepResult", back_populates="xray_test", lazy="selectin", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<XrayTest(id={self.id}, key='{self.xray_issue_key}', type='{self.test_type}')>"
    
    @property
    def step_count(self) -> int:
        """Get number of steps/scenarios"""
        if self.test_type == XrayTestType.MANUAL:
            return len(self.manual_steps or [])
        elif self.test_type == XrayTestType.GHERKIN and self.gherkin_scenario:
            # Count Given/When/Then lines
            lines = [l.strip() for l in self.gherkin_scenario.split('\n') if l.strip()]
            return len([l for l in lines if l.lower().startswith(('given', 'when', 'then', 'and', 'but'))])
        return 0


class XrayStepResult(Base):
    """Per-step execution result for Xray reporting"""
    __tablename__ = "xray_step_results"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # References
    xray_test_id = Column(Integer, ForeignKey("xray_tests.id", ondelete="CASCADE"), nullable=False)
    test_run_id = Column(Integer, ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False)
    
    # Step identification
    step_index = Column(Integer, nullable=False)  # 0-based index
    step_action = Column(Text, nullable=True)  # The action/step text
    step_expected = Column(Text, nullable=True)  # Expected result (for manual)
    
    # Result
    status = Column(Enum(XrayStepStatus), default=XrayStepStatus.PENDING)
    actual_result = Column(Text, nullable=True)  # What actually happened
    
    # Evidence
    screenshot_path = Column(String(500), nullable=True)
    comment = Column(Text, nullable=True)
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    
    # Export tracking
    export_status = Column(Enum(XrayExportStatus), default=XrayExportStatus.PENDING)
    xray_execution_id = Column(String(100), nullable=True)  # Xray Test Execution issue key
    exported_at = Column(DateTime(timezone=True), nullable=True)
    export_error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    xray_test = relationship("XrayTest", back_populates="step_results")
    test_run = relationship("TestRun", backref="xray_step_results")
    
    def __repr__(self):
        return f"<XrayStepResult(id={self.id}, test_id={self.xray_test_id}, step={self.step_index}, status='{self.status}')>"
