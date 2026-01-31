"""
Notification service
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, List, Optional
import logging

from app.notifications.models import NotificationChannel as NotificationChannelModel, ChannelType
from app.notifications.channels import get_channel
from app.tests.models import TestRun, TestStatus

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_channels_for_event(
        self,
        organization_id: int,
        event: str
    ) -> List[NotificationChannelModel]:
        """Get all enabled channels that should be notified for an event"""
        
        result = await self.db.execute(
            select(NotificationChannelModel).where(
                NotificationChannelModel.organization_id == organization_id,
                NotificationChannelModel.enabled == True,
            )
        )
        channels = result.scalars().all()
        
        # Filter by event
        return [
            ch for ch in channels
            if event in (ch.notify_on or [])
        ]
    
    async def notify_test_completed(self, test_run: TestRun):
        """Send notifications for a completed test"""
        
        # Determine event type
        if test_run.status == TestStatus.COMPLETED:
            event = "test_completed"
        elif test_run.status == TestStatus.FAILED:
            event = "test_failed"
        else:
            return  # Don't notify for other statuses
        
        # Get project's organization
        from app.projects.models import Project
        result = await self.db.execute(
            select(Project).where(Project.id == test_run.project_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            return
        
        # Get channels
        channels = await self.get_channels_for_event(
            project.organization_id,
            event
        )
        
        if not channels:
            return
        
        # Build notification
        status_emoji = "✅" if test_run.status == TestStatus.COMPLETED else "❌"
        title = f"{status_emoji} Test {test_run.status.value.title()}"
        
        message = f"Test run #{test_run.id} has {test_run.status.value}."
        if test_run.error_message:
            message += f"\n\nError: {test_run.error_message}"
        
        metadata = {
            "Project": project.name,
            "Command": test_run.command[:100] + "..." if len(test_run.command) > 100 else test_run.command,
            "Duration": f"{test_run.duration_ms / 1000:.2f}s" if test_run.duration_ms else "N/A",
            "Trigger": test_run.trigger_type,
        }
        
        # Send to all channels
        for channel_model in channels:
            try:
                channel = get_channel(channel_model.channel_type, channel_model.config)
                await channel.send(message, title, metadata)
            except Exception as e:
                logger.error(f"Failed to send notification via {channel_model.name}: {e}")
    
    async def notify_schedule_triggered(
        self,
        schedule_id: int,
        test_run_id: int
    ):
        """Send notifications when a scheduled test is triggered"""
        
        from app.tests.models import Schedule
        from app.projects.models import Project
        
        result = await self.db.execute(
            select(Schedule).where(Schedule.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()
        
        if not schedule:
            return
        
        result = await self.db.execute(
            select(Project).where(Project.id == schedule.project_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            return
        
        channels = await self.get_channels_for_event(
            project.organization_id,
            "schedule_triggered"
        )
        
        if not channels:
            return
        
        title = "🕐 Scheduled Test Started"
        message = f"Schedule '{schedule.name}' has been triggered."
        
        metadata = {
            "Project": project.name,
            "Schedule": schedule.name,
            "Test Run ID": str(test_run_id),
            "Cron": schedule.cron_expression,
        }
        
        for channel_model in channels:
            try:
                channel = get_channel(channel_model.channel_type, channel_model.config)
                await channel.send(message, title, metadata)
            except Exception as e:
                logger.error(f"Failed to send notification via {channel_model.name}: {e}")
