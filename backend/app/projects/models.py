"""
Project models
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Project(Base):
    """Project model - represents a browser testing project"""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Organization (multi-tenant)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    
    # Creator
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # vLLM Configuration (stored as JSON)
    vllm_config = Column(JSON, default=dict)
    # Example: {
    #   "api_url": "http://localhost:8000",
    #   "model_name": "llama-3.1-8b",
    #   "temperature": 0.7,
    #   "max_tokens": 2048
    # }
    
    # Browser Configuration
    browser_config = Column(JSON, default=dict)
    # Example: {
    #   "headless": true,
    #   "timeout": 30000,
    #   "viewport": {"width": 1920, "height": 1080}
    # }
    
    # Default test commands/scenarios
    default_commands = Column(JSON, default=list)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="projects")
    created_by_user = relationship("User", back_populates="created_projects", foreign_keys=[created_by])
    test_runs = relationship("TestRun", back_populates="project", lazy="selectin")
    schedules = relationship("Schedule", back_populates="project", lazy="selectin")
    
    # Unique constraint: slug must be unique within organization
    __table_args__ = (
        # UniqueConstraint('organization_id', 'slug', name='uq_project_org_slug'),
    )
    
    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}')>"
