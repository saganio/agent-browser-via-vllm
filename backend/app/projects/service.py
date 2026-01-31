"""
Project service layer
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
import secrets

from app.projects.models import Project
from app.tests.models import TestRun
from app.auth.models import User
from app.projects.schemas import ProjectCreate, ProjectUpdate


def create_slug(name: str) -> str:
    """Create URL-friendly slug from name"""
    slug = name.lower()
    slug = "".join(c if c.isalnum() or c == " " else "" for c in slug)
    slug = slug.replace(" ", "-")
    slug = "-".join(filter(None, slug.split("-")))  # Remove consecutive dashes
    return slug[:80] + "-" + secrets.token_hex(4)


class ProjectService:
    """Service for project operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_project(
        self,
        data: ProjectCreate,
        user: User
    ) -> Project:
        """Create a new project"""
        
        project = Project(
            name=data.name,
            slug=create_slug(data.name),
            description=data.description,
            organization_id=user.organization_id,
            created_by=user.id,
            vllm_config=data.vllm_config.model_dump() if data.vllm_config else {},
            browser_config=data.browser_config.model_dump() if data.browser_config else {},
            default_commands=data.default_commands or [],
        )
        
        self.db.add(project)
        await self.db.flush()
        await self.db.refresh(project)
        
        return project
    
    async def get_project(
        self,
        project_id: int,
        organization_id: int
    ) -> Optional[Project]:
        """Get a project by ID (with organization filter for multi-tenancy)"""
        
        result = await self.db.execute(
            select(Project)
            .where(
                Project.id == project_id,
                Project.organization_id == organization_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_project_by_slug(
        self,
        slug: str,
        organization_id: int
    ) -> Optional[Project]:
        """Get a project by slug"""
        
        result = await self.db.execute(
            select(Project)
            .where(
                Project.slug == slug,
                Project.organization_id == organization_id
            )
        )
        return result.scalar_one_or_none()
    
    async def list_projects(
        self,
        organization_id: int,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Tuple[List[Project], int]:
        """List projects for an organization with pagination"""
        
        # Base query
        query = select(Project).where(
            Project.organization_id == organization_id
        )
        
        # Apply filters
        if search:
            query = query.where(
                Project.name.ilike(f"%{search}%") |
                Project.description.ilike(f"%{search}%")
            )
        
        if is_active is not None:
            query = query.where(Project.is_active == is_active)
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination and ordering
        query = query.order_by(desc(Project.updated_at), desc(Project.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        projects = result.scalars().all()
        
        return list(projects), total
    
    async def update_project(
        self,
        project: Project,
        data: ProjectUpdate
    ) -> Project:
        """Update a project"""
        
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if field == "vllm_config" and value:
                setattr(project, field, value.model_dump() if hasattr(value, 'model_dump') else value)
            elif field == "browser_config" and value:
                setattr(project, field, value.model_dump() if hasattr(value, 'model_dump') else value)
            else:
                setattr(project, field, value)
        
        await self.db.flush()
        await self.db.refresh(project)
        
        return project
    
    async def delete_project(self, project: Project) -> None:
        """Delete a project (soft delete by setting is_active=False)"""
        project.is_active = False
        await self.db.flush()
    
    async def hard_delete_project(self, project: Project) -> None:
        """Permanently delete a project"""
        await self.db.delete(project)
        await self.db.flush()
    
    async def get_project_stats(
        self,
        project_id: int,
        organization_id: int
    ) -> dict:
        """Get statistics for a project"""
        
        # Total test runs
        total_runs_result = await self.db.execute(
            select(func.count(TestRun.id))
            .join(Project)
            .where(
                TestRun.project_id == project_id,
                Project.organization_id == organization_id
            )
        )
        total_runs = total_runs_result.scalar() or 0
        
        # Successful runs
        successful_runs_result = await self.db.execute(
            select(func.count(TestRun.id))
            .join(Project)
            .where(
                TestRun.project_id == project_id,
                Project.organization_id == organization_id,
                TestRun.status == "completed"
            )
        )
        successful_runs = successful_runs_result.scalar() or 0
        
        # Failed runs
        failed_runs_result = await self.db.execute(
            select(func.count(TestRun.id))
            .join(Project)
            .where(
                TestRun.project_id == project_id,
                Project.organization_id == organization_id,
                TestRun.status == "failed"
            )
        )
        failed_runs = failed_runs_result.scalar() or 0
        
        # Last test run
        last_run_result = await self.db.execute(
            select(TestRun)
            .join(Project)
            .where(
                TestRun.project_id == project_id,
                Project.organization_id == organization_id
            )
            .order_by(desc(TestRun.created_at))
            .limit(1)
        )
        last_run = last_run_result.scalar_one_or_none()
        
        return {
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "success_rate": (successful_runs / total_runs * 100) if total_runs > 0 else 0,
            "last_run_at": last_run.created_at if last_run else None,
            "last_run_status": last_run.status.value if last_run else None,
        }
