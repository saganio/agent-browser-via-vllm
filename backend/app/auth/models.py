"""
Authentication and authorization models
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from typing import Optional, List

from app.database import Base


class Role(str, enum.Enum):
    """User roles for RBAC"""
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class Organization(Base):
    """Organization/Tenant model for multi-tenancy"""
    __tablename__ = "organizations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Settings stored as JSON
    settings = Column(JSON, default=dict)
    
    # Limits
    max_concurrent_tests = Column(Integer, default=5)
    max_projects = Column(Integer, default=50)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    users = relationship("User", back_populates="organization", lazy="selectin")
    projects = relationship("Project", back_populates="organization", lazy="selectin")
    notifications = relationship("NotificationChannel", back_populates="organization", lazy="selectin")
    
    def __repr__(self):
        return f"<Organization(id={self.id}, name='{self.name}')>"


class User(Base):
    """User model with OIDC support"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # OIDC fields
    oidc_sub = Column(String(255), unique=True, nullable=True, index=True)  # OIDC subject identifier
    oidc_provider = Column(String(100), nullable=True)  # Provider name
    
    # User info
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    # Local auth (fallback)
    hashed_password = Column(String(255), nullable=True)
    
    # Organization & Role
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    role = Column(Enum(Role, values_callable=lambda obj: [e.value for e in obj]), default=Role.VIEWER, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    created_projects = relationship("Project", back_populates="created_by_user", foreign_keys="Project.created_by")
    test_runs = relationship("TestRun", back_populates="triggered_by_user", foreign_keys="TestRun.triggered_by")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
    
    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN
    
    @property
    def can_create_projects(self) -> bool:
        return self.role in [Role.ADMIN, Role.DEVELOPER]
    
    @property
    def can_run_tests(self) -> bool:
        return self.role in [Role.ADMIN, Role.DEVELOPER]


class RefreshToken(Base):
    """Refresh token storage for JWT authentication"""
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(500), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User")
