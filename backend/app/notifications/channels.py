"""
Notification channel implementations
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import aiohttp
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

from app.notifications.models import ChannelType

logger = logging.getLogger(__name__)


class NotificationChannel(ABC):
    """Base class for notification channels"""
    
    @abstractmethod
    async def send(
        self,
        message: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send a notification. Returns True if successful."""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate the channel configuration."""
        pass


class EmailChannel(NotificationChannel):
    """Email notification channel"""
    
    def __init__(self, config: Dict[str, Any]):
        self.smtp_host = config.get("smtp_host", "localhost")
        self.smtp_port = config.get("smtp_port", 587)
        self.username = config.get("username")
        self.password = config.get("password")
        self.from_email = config.get("from_email")
        self.to_emails = config.get("to_emails", [])
        self.use_tls = config.get("use_tls", True)
    
    def validate_config(self) -> bool:
        return all([
            self.smtp_host,
            self.from_email,
            self.to_emails,
        ])
    
    async def send(
        self,
        message: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        if not self.validate_config():
            logger.error("Email channel not properly configured")
            return False
        
        try:
            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = ", ".join(self.to_emails)
            msg["Subject"] = title or "Browser Test Notification"
            
            # Build email body
            body = message
            if metadata:
                body += "\n\n---\nDetails:\n"
                for key, value in metadata.items():
                    body += f"- {key}: {value}\n"
            
            msg.attach(MIMEText(body, "plain"))
            
            # Send email
            async with aiosmtplib.SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port,
                use_tls=self.use_tls,
            ) as smtp:
                if self.username and self.password:
                    await smtp.login(self.username, self.password)
                await smtp.send_message(msg)
            
            logger.info(f"Email sent to {self.to_emails}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False


class SlackChannel(NotificationChannel):
    """Slack webhook notification channel"""
    
    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config.get("webhook_url")
        self.channel = config.get("channel")  # Optional override
        self.username = config.get("username", "Browser Test Bot")
        self.icon_emoji = config.get("icon_emoji", ":robot_face:")
    
    def validate_config(self) -> bool:
        return bool(self.webhook_url)
    
    async def send(
        self,
        message: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        if not self.validate_config():
            logger.error("Slack channel not properly configured")
            return False
        
        try:
            # Build Slack message
            blocks = []
            
            if title:
                blocks.append({
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": title,
                    }
                })
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message,
                }
            })
            
            if metadata:
                fields = []
                for key, value in metadata.items():
                    fields.append({
                        "type": "mrkdwn",
                        "text": f"*{key}:*\n{value}"
                    })
                
                # Slack allows max 10 fields per section
                for i in range(0, len(fields), 10):
                    blocks.append({
                        "type": "section",
                        "fields": fields[i:i+10]
                    })
            
            payload = {
                "username": self.username,
                "icon_emoji": self.icon_emoji,
                "blocks": blocks,
            }
            
            if self.channel:
                payload["channel"] = self.channel
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload
                ) as response:
                    if response.status == 200:
                        logger.info("Slack notification sent")
                        return True
                    else:
                        text = await response.text()
                        logger.error(f"Slack API error: {response.status} - {text}")
                        return False
                        
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False


class WebhookChannel(NotificationChannel):
    """Generic webhook notification channel"""
    
    def __init__(self, config: Dict[str, Any]):
        self.url = config.get("url")
        self.method = config.get("method", "POST")
        self.headers = config.get("headers", {})
        self.auth_token = config.get("auth_token")
    
    def validate_config(self) -> bool:
        return bool(self.url)
    
    async def send(
        self,
        message: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        if not self.validate_config():
            logger.error("Webhook channel not properly configured")
            return False
        
        try:
            headers = {"Content-Type": "application/json", **self.headers}
            
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            payload = {
                "title": title,
                "message": message,
                "metadata": metadata or {},
                "source": "browser-test-platform",
            }
            
            async with aiohttp.ClientSession(headers=headers) as session:
                if self.method.upper() == "POST":
                    async with session.post(self.url, json=payload) as response:
                        success = 200 <= response.status < 300
                else:
                    async with session.request(
                        self.method.upper(),
                        self.url,
                        json=payload
                    ) as response:
                        success = 200 <= response.status < 300
                
                if success:
                    logger.info(f"Webhook notification sent to {self.url}")
                    return True
                else:
                    text = await response.text()
                    logger.error(f"Webhook error: {response.status} - {text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False


class DiscordChannel(NotificationChannel):
    """Discord webhook notification channel"""
    
    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config.get("webhook_url")
        self.username = config.get("username", "Browser Test Bot")
        self.avatar_url = config.get("avatar_url")
    
    def validate_config(self) -> bool:
        return bool(self.webhook_url)
    
    async def send(
        self,
        message: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        if not self.validate_config():
            logger.error("Discord channel not properly configured")
            return False
        
        try:
            # Build Discord embed
            embed = {
                "description": message,
                "color": 5814783,  # Blue color
            }
            
            if title:
                embed["title"] = title
            
            if metadata:
                embed["fields"] = [
                    {"name": key, "value": str(value), "inline": True}
                    for key, value in metadata.items()
                ]
            
            payload = {
                "username": self.username,
                "embeds": [embed],
            }
            
            if self.avatar_url:
                payload["avatar_url"] = self.avatar_url
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload
                ) as response:
                    if response.status in [200, 204]:
                        logger.info("Discord notification sent")
                        return True
                    else:
                        text = await response.text()
                        logger.error(f"Discord API error: {response.status} - {text}")
                        return False
                        
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False


def get_channel(channel_type: ChannelType, config: Dict[str, Any]) -> NotificationChannel:
    """Factory function to get the appropriate channel"""
    
    channel_map = {
        ChannelType.EMAIL: EmailChannel,
        ChannelType.SLACK: SlackChannel,
        ChannelType.WEBHOOK: WebhookChannel,
        ChannelType.DISCORD: DiscordChannel,
    }
    
    channel_class = channel_map.get(channel_type)
    if not channel_class:
        raise ValueError(f"Unknown channel type: {channel_type}")
    
    return channel_class(config)
