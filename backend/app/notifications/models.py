"""
Notification models
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class ChannelType(str, enum.Enum):
    """Notification channel types"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    DISCORD = "discord"


class NotificationChannel(Base):
    """Notification channel configuration"""
    __tablename__ = "notification_channels"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Organization
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    
    # Channel info
    name = Column(String(255), nullable=False)
    channel_type = Column(Enum(ChannelType), nullable=False)
    
    # Configuration (encrypted in production)
    config = Column(JSON, default=dict)
    # Email: {"smtp_host": "", "smtp_port": 587, "username": "", "password": "", "from_email": ""}
    # Slack: {"webhook_url": "", "channel": "#alerts"}
    # Webhook: {"url": "", "headers": {}, "method": "POST"}
    # Discord: {"webhook_url": ""}
    
    # Events to notify
    notify_on = Column(JSON, default=list)
    # ["test_completed", "test_failed", "schedule_triggered"]
    
    # Status
    enabled = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="notifications")
    
    def __repr__(self):
        return f"<NotificationChannel(id={self.id}, name='{self.name}', type='{self.channel_type}')>"
