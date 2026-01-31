"""
Test execution models
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class TestStatus(str, enum.Enum):
    """Test run status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TestRun(Base):
    """Test run model - represents a single test execution"""
    __tablename__ = "test_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Project
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    
    # Command/Task
    command = Column(Text, nullable=False)  # Natural language command
    
    # Status
    status = Column(Enum(TestStatus), default=TestStatus.PENDING, nullable=False)
    
    # Execution info
    triggered_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Null for scheduled runs
    trigger_type = Column(String(50), default="manual")  # manual, scheduled, api
    
    # Worker info
    worker_id = Column(String(100), nullable=True)
    celery_task_id = Column(String(100), nullable=True)
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    
    # Error info
    error_message = Column(Text, nullable=True)
    
    # Extra data
    extra_data = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="test_runs")
    triggered_by_user = relationship("User", back_populates="test_runs", foreign_keys=[triggered_by])
    results = relationship("TestResult", back_populates="test_run", lazy="selectin", order_by="TestResult.sequence")
    
    def __repr__(self):
        return f"<TestRun(id={self.id}, status='{self.status}')>"
    
    @property
    def is_finished(self) -> bool:
        return self.status in [TestStatus.COMPLETED, TestStatus.FAILED, TestStatus.CANCELLED]


class TestResult(Base):
    """Individual test step result"""
    __tablename__ = "test_results"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Test run
    test_run_id = Column(Integer, ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False)
    
    # Sequence number (order of execution)
    sequence = Column(Integer, nullable=False)
    
    # Step info
    step_type = Column(String(50), nullable=False)  # tool_call, tool_result, assistant, error, etc.
    tool_name = Column(String(100), nullable=True)
    
    # Content
    content = Column(Text, nullable=True)
    data = Column(JSON, default=dict)
    
    # Success/Failure
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    # Artifacts
    screenshot_path = Column(String(500), nullable=True)
    video_path = Column(String(500), nullable=True)
    
    # Timing
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    test_run = relationship("TestRun", back_populates="results")
    
    def __repr__(self):
        return f"<TestResult(id={self.id}, step_type='{self.step_type}')>"


class Schedule(Base):
    """Scheduled test execution"""
    __tablename__ = "schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Project
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    
    # Schedule name
    name = Column(String(255), nullable=False)
    
    # Command to run
    command = Column(Text, nullable=False)
    
    # Cron expression
    cron_expression = Column(String(100), nullable=False)  # e.g., "0 9 * * *" for daily at 9am
    
    # Timezone
    timezone = Column(String(50), default="UTC")
    
    # Status
    enabled = Column(Boolean, default=True)
    
    # Execution history
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    last_run_status = Column(Enum(TestStatus), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    run_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="schedules")
    
    def __repr__(self):
        return f"<Schedule(id={self.id}, name='{self.name}', cron='{self.cron_expression}')>"
