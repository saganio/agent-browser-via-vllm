"""
Test scheduler using APScheduler
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from datetime import datetime, timezone
from typing import Optional
import logging

from app.database import async_session_maker
from app.tests.models import Schedule, TestStatus
from app.tests.service import TestService, ScheduleService
from app.workers.tasks import execute_browser_test

logger = logging.getLogger(__name__)


class TestScheduler:
    """Manages scheduled test execution"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler(
            jobstores={"default": MemoryJobStore()},
            job_defaults={
                "coalesce": True,  # Combine missed runs
                "max_instances": 1,  # Only one instance per job
            }
        )
        self._started = False
    
    async def start(self):
        """Start the scheduler and load existing schedules"""
        if self._started:
            return
        
        self.scheduler.start()
        self._started = True
        
        # Load existing schedules from database
        await self.load_schedules()
        
        logger.info("Test scheduler started")
    
    async def stop(self):
        """Stop the scheduler"""
        if not self._started:
            return
        
        self.scheduler.shutdown(wait=False)
        self._started = False
        
        logger.info("Test scheduler stopped")
    
    async def load_schedules(self):
        """Load all enabled schedules from database"""
        async with async_session_maker() as db:
            schedule_service = ScheduleService(db)
            schedules = await schedule_service.get_enabled_schedules()
            
            for schedule in schedules:
                self.add_schedule(schedule)
            
            logger.info(f"Loaded {len(schedules)} schedules")
    
    def add_schedule(self, schedule: Schedule):
        """Add a schedule to the scheduler"""
        job_id = f"schedule_{schedule.id}"
        
        # Remove existing job if any
        self.remove_schedule(schedule.id)
        
        try:
            trigger = CronTrigger.from_crontab(
                schedule.cron_expression,
                timezone=schedule.timezone
            )
            
            self.scheduler.add_job(
                self._run_scheduled_test,
                trigger=trigger,
                id=job_id,
                args=[schedule.id],
                name=f"Schedule: {schedule.name}",
                replace_existing=True,
            )
            
            # Calculate next run time
            next_run = trigger.get_next_fire_time(None, datetime.now(timezone.utc))
            
            logger.info(f"Added schedule {schedule.id}: {schedule.name}, next run: {next_run}")
            
        except Exception as e:
            logger.error(f"Failed to add schedule {schedule.id}: {e}")
    
    def remove_schedule(self, schedule_id: int):
        """Remove a schedule from the scheduler"""
        job_id = f"schedule_{schedule_id}"
        
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed schedule {schedule_id}")
        except Exception:
            pass  # Job might not exist
    
    def update_schedule(self, schedule: Schedule):
        """Update a schedule in the scheduler"""
        if schedule.enabled:
            self.add_schedule(schedule)
        else:
            self.remove_schedule(schedule.id)
    
    async def _run_scheduled_test(self, schedule_id: int):
        """Execute a scheduled test"""
        logger.info(f"Running scheduled test {schedule_id}")
        
        async with async_session_maker() as db:
            from sqlalchemy import select
            
            # Get schedule
            result = await db.execute(
                select(Schedule).where(Schedule.id == schedule_id)
            )
            schedule = result.scalar_one_or_none()
            
            if not schedule or not schedule.enabled:
                logger.warning(f"Schedule {schedule_id} not found or disabled")
                return
            
            # Create test run
            test_service = TestService(db)
            test_run = await test_service.create_test_run(
                project_id=schedule.project_id,
                command=schedule.command,
                user=None,  # Scheduled runs have no user
                trigger_type="scheduled"
            )
            
            await db.commit()
            
            # Queue the task
            execute_browser_test.delay(
                test_run_id=test_run.id,
                project_id=schedule.project_id,
                command=schedule.command
            )
            
            # Update schedule run info
            schedule_service = ScheduleService(db)
            
            # Calculate next run
            trigger = CronTrigger.from_crontab(
                schedule.cron_expression,
                timezone=schedule.timezone
            )
            next_run = trigger.get_next_fire_time(None, datetime.now(timezone.utc))
            
            await schedule_service.update_schedule_run(
                schedule,
                status=TestStatus.PENDING,  # Will be updated when task completes
                next_run_at=next_run
            )
            
            await db.commit()
            
            logger.info(f"Scheduled test {schedule_id} queued as test run {test_run.id}")


# Global scheduler instance
test_scheduler = TestScheduler()
