"""
Notification API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import math

from app.database import get_db
from app.auth.models import User, Role
from app.auth.dependencies import get_current_active_user, require_role
from app.notifications.models import NotificationChannel, ChannelType
from app.notifications.channels import get_channel


router = APIRouter(prefix="/notifications", tags=["Notifications"])


# Pydantic schemas
class NotificationChannelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    channel_type: ChannelType
    config: Dict[str, Any]
    notify_on: List[str] = Field(default=["test_completed", "test_failed"])
    enabled: bool = True


class NotificationChannelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    config: Optional[Dict[str, Any]] = None
    notify_on: Optional[List[str]] = None
    enabled: Optional[bool] = None


class NotificationChannelResponse(BaseModel):
    id: int
    organization_id: int
    name: str
    channel_type: ChannelType
    config: Dict[str, Any]
    notify_on: List[str]
    enabled: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class NotificationChannelListResponse(BaseModel):
    items: List[NotificationChannelResponse]
    total: int
    page: int
    page_size: int
    pages: int


class TestNotificationRequest(BaseModel):
    message: str = "This is a test notification"
    title: str = "Test Notification"


@router.post("/channels", response_model=NotificationChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_notification_channel(
    data: NotificationChannelCreate,
    current_user: User = Depends(require_role([Role.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """Create a new notification channel"""
    
    # Validate channel config
    try:
        channel = get_channel(data.channel_type, data.config)
        if not channel.validate_config():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid channel configuration"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    notification_channel = NotificationChannel(
        organization_id=current_user.organization_id,
        name=data.name,
        channel_type=data.channel_type,
        config=data.config,
        notify_on=data.notify_on,
        enabled=data.enabled,
    )
    
    db.add(notification_channel)
    await db.commit()
    await db.refresh(notification_channel)
    
    return NotificationChannelResponse(
        id=notification_channel.id,
        organization_id=notification_channel.organization_id,
        name=notification_channel.name,
        channel_type=notification_channel.channel_type,
        config=notification_channel.config,
        notify_on=notification_channel.notify_on or [],
        enabled=notification_channel.enabled,
        created_at=notification_channel.created_at,
        updated_at=notification_channel.updated_at,
    )


@router.get("/channels", response_model=NotificationChannelListResponse)
async def list_notification_channels(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    enabled: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List notification channels for the current organization"""
    
    query = select(NotificationChannel).where(
        NotificationChannel.organization_id == current_user.organization_id
    )
    
    if enabled is not None:
        query = query.where(NotificationChannel.enabled == enabled)
    
    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    channels = result.scalars().all()
    
    return NotificationChannelListResponse(
        items=[
            NotificationChannelResponse(
                id=ch.id,
                organization_id=ch.organization_id,
                name=ch.name,
                channel_type=ch.channel_type,
                config=ch.config,
                notify_on=ch.notify_on or [],
                enabled=ch.enabled,
                created_at=ch.created_at,
                updated_at=ch.updated_at,
            )
            for ch in channels
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0
    )


@router.get("/channels/{channel_id}", response_model=NotificationChannelResponse)
async def get_notification_channel(
    channel_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a notification channel"""
    
    result = await db.execute(
        select(NotificationChannel).where(
            NotificationChannel.id == channel_id,
            NotificationChannel.organization_id == current_user.organization_id
        )
    )
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification channel not found"
        )
    
    return NotificationChannelResponse(
        id=channel.id,
        organization_id=channel.organization_id,
        name=channel.name,
        channel_type=channel.channel_type,
        config=channel.config,
        notify_on=channel.notify_on or [],
        enabled=channel.enabled,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
    )


@router.patch("/channels/{channel_id}", response_model=NotificationChannelResponse)
async def update_notification_channel(
    channel_id: int,
    data: NotificationChannelUpdate,
    current_user: User = Depends(require_role([Role.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """Update a notification channel"""
    
    result = await db.execute(
        select(NotificationChannel).where(
            NotificationChannel.id == channel_id,
            NotificationChannel.organization_id == current_user.organization_id
        )
    )
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification channel not found"
        )
    
    update_data = data.model_dump(exclude_unset=True)
    
    # If config is being updated, validate it
    if "config" in update_data:
        try:
            ch = get_channel(channel.channel_type, update_data["config"])
            if not ch.validate_config():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid channel configuration"
                )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    
    for field, value in update_data.items():
        setattr(channel, field, value)
    
    await db.commit()
    await db.refresh(channel)
    
    return NotificationChannelResponse(
        id=channel.id,
        organization_id=channel.organization_id,
        name=channel.name,
        channel_type=channel.channel_type,
        config=channel.config,
        notify_on=channel.notify_on or [],
        enabled=channel.enabled,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
    )


@router.delete("/channels/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification_channel(
    channel_id: int,
    current_user: User = Depends(require_role([Role.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """Delete a notification channel"""
    
    result = await db.execute(
        select(NotificationChannel).where(
            NotificationChannel.id == channel_id,
            NotificationChannel.organization_id == current_user.organization_id
        )
    )
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification channel not found"
        )
    
    await db.delete(channel)
    await db.commit()
    
    return None


@router.post("/channels/{channel_id}/test")
async def test_notification_channel(
    channel_id: int,
    data: TestNotificationRequest,
    current_user: User = Depends(require_role([Role.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """Send a test notification to a channel"""
    
    result = await db.execute(
        select(NotificationChannel).where(
            NotificationChannel.id == channel_id,
            NotificationChannel.organization_id == current_user.organization_id
        )
    )
    channel_model = result.scalar_one_or_none()
    
    if not channel_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification channel not found"
        )
    
    try:
        channel = get_channel(channel_model.channel_type, channel_model.config)
        success = await channel.send(
            message=data.message,
            title=data.title,
            metadata={"Triggered by": current_user.email}
        )
        
        if success:
            return {"status": "success", "message": "Test notification sent"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send test notification"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending notification: {str(e)}"
        )


@router.get("/events")
async def list_notification_events():
    """List available notification events"""
    return {
        "events": [
            {
                "id": "test_completed",
                "name": "Test Completed",
                "description": "Triggered when a test run completes successfully"
            },
            {
                "id": "test_failed",
                "name": "Test Failed",
                "description": "Triggered when a test run fails"
            },
            {
                "id": "schedule_triggered",
                "name": "Schedule Triggered",
                "description": "Triggered when a scheduled test starts"
            },
        ]
    }
