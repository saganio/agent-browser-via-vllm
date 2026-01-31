"""
Main FastAPI application
"""

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import init_db, close_db
from app.auth.router import router as auth_router
from app.projects.router import router as projects_router
from app.tests.router import router as tests_router
from app.notifications.router import router as notifications_router
from app.xray.router import router as xray_router
from app.tests.scheduler import test_scheduler
from app.websocket import websocket_execute_test

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Browser Test Platform...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Start scheduler
    await test_scheduler.start()
    logger.info("Test scheduler started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Browser Test Platform...")
    
    # Stop scheduler
    await test_scheduler.stop()
    
    # Close database
    await close_db()
    
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise Browser Test Platform with AI-powered automation",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(tests_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")
app.include_router(xray_router, prefix="/api")


# WebSocket endpoint for test execution
@app.websocket("/ws/tests/{test_run_id}/execute")
async def ws_execute_test(websocket: WebSocket, test_run_id: int):
    """WebSocket endpoint for real-time test execution"""
    await websocket_execute_test(websocket, test_run_id)


# Health check
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


# Dashboard stats endpoint
@app.get("/api/dashboard/stats")
async def dashboard_stats():
    """Get dashboard statistics"""
    from sqlalchemy import select, func
    from app.database import async_session_maker
    from app.projects.models import Project
    from app.tests.models import TestRun, TestStatus
    from app.auth.models import Organization
    
    async with async_session_maker() as db:
        # Total organizations
        org_count = await db.execute(select(func.count(Organization.id)))
        total_orgs = org_count.scalar()
        
        # Total projects
        project_count = await db.execute(select(func.count(Project.id)))
        total_projects = project_count.scalar()
        
        # Total test runs
        test_count = await db.execute(select(func.count(TestRun.id)))
        total_tests = test_count.scalar()
        
        # Successful tests
        success_count = await db.execute(
            select(func.count(TestRun.id)).where(TestRun.status == TestStatus.COMPLETED)
        )
        successful_tests = success_count.scalar()
        
        # Failed tests
        failed_count = await db.execute(
            select(func.count(TestRun.id)).where(TestRun.status == TestStatus.FAILED)
        )
        failed_tests = failed_count.scalar()
        
        # Running tests
        running_count = await db.execute(
            select(func.count(TestRun.id)).where(TestRun.status == TestStatus.RUNNING)
        )
        running_tests = running_count.scalar()
        
        return {
            "organizations": total_orgs,
            "projects": total_projects,
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": failed_tests,
            "running_tests": running_tests,
            "success_rate": (successful_tests / total_tests * 100) if total_tests > 0 else 0,
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.DEBUG,
    )
