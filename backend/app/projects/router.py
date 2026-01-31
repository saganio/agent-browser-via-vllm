"""
Project API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import math

from app.database import get_db
from app.auth.models import User, Role
from app.auth.dependencies import get_current_active_user, require_role
from app.projects.models import Project
from app.projects.schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    TestVLLMConnectionRequest,
    TestVLLMConnectionResponse,
)
from app.projects.service import ProjectService
import aiohttp


router = APIRouter(prefix="/projects", tags=["Projects"])


def project_to_response(project: Project, created_by_name: Optional[str] = None) -> ProjectResponse:
    """Convert Project model to response schema"""
    return ProjectResponse(
        id=project.id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        organization_id=project.organization_id,
        created_by=project.created_by,
        created_by_name=created_by_name,
        vllm_config=project.vllm_config or {},
        browser_config=project.browser_config or {},
        default_commands=project.default_commands or [],
        is_active=project.is_active,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    current_user: User = Depends(require_role([Role.ADMIN, Role.DEVELOPER])),
    db: AsyncSession = Depends(get_db)
):
    """Create a new project"""
    
    service = ProjectService(db)
    project = await service.create_project(data, current_user)
    
    return project_to_response(project, current_user.name)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List projects for the current organization"""
    
    service = ProjectService(db)
    projects, total = await service.list_projects(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        search=search,
        is_active=is_active
    )
    
    return ProjectListResponse(
        items=[project_to_response(p) for p in projects],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a project by ID"""
    
    service = ProjectService(db)
    project = await service.get_project(project_id, current_user.organization_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    return project_to_response(project)


@router.get("/{project_id}/stats")
async def get_project_stats(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get statistics for a project"""
    
    service = ProjectService(db)
    
    # Verify project exists and belongs to user's org
    project = await service.get_project(project_id, current_user.organization_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    stats = await service.get_project_stats(project_id, current_user.organization_id)
    return stats


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    data: ProjectUpdate,
    current_user: User = Depends(require_role([Role.ADMIN, Role.DEVELOPER])),
    db: AsyncSession = Depends(get_db)
):
    """Update a project"""
    
    service = ProjectService(db)
    project = await service.get_project(project_id, current_user.organization_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    updated_project = await service.update_project(project, data)
    
    return project_to_response(updated_project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    permanent: bool = False,
    current_user: User = Depends(require_role([Role.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """Delete a project (soft delete by default, permanent with ?permanent=true)"""
    
    service = ProjectService(db)
    project = await service.get_project(project_id, current_user.organization_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if permanent:
        await service.hard_delete_project(project)
    else:
        await service.delete_project(project)
    
    return None


@router.post("/test-vllm-connection", response_model=TestVLLMConnectionResponse)
async def test_vllm_connection(
    data: TestVLLMConnectionRequest,
    current_user: User = Depends(require_role([Role.ADMIN, Role.DEVELOPER, Role.VIEWER])),
):
    """Test connection to vLLM server"""
    
    # Clean up URL
    api_url = data.api_url.rstrip("/")
    
    headers = {"Content-Type": "application/json"}
    if data.api_key:
        headers["Authorization"] = f"Bearer {data.api_key}"
        
    try:
        # Try to list models to verify connection and auth
        async with aiohttp.ClientSession(headers=headers) as session:
            # First check models endpoint
            async with session.get(
                f"{api_url}/v1/models",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    models_data = await response.json()
                    
                    # specific check if model exists if models data structure is standard
                    # but simple validation is enough for now
                    
                    return TestVLLMConnectionResponse(
                        success=True,
                        message="Successfully connected to vLLM",
                        model_name=data.model_name
                    )
                
                # If models endpoint fails (some proxies block it), try a minimal completion
                elif response.status in [401, 403]:
                    return TestVLLMConnectionResponse(
                        success=False,
                        message=f"Authentication failed: {response.status}"
                    )
        
        # Fallback: try minimal completion if listing models fails or isn't supported
        async with aiohttp.ClientSession(headers=headers) as session:
            payload = {
                "model": data.model_name,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1
            }
            
            async with session.post(
                f"{api_url}/v1/chat/completions",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                   return TestVLLMConnectionResponse(
                        success=True,
                        message="Successfully connected to vLLM (verified via completion)",
                        model_name=data.model_name
                    )
                else:
                    error_text = await response.text()
                    return TestVLLMConnectionResponse(
                        success=False,
                        message=f"Connection failed ({response.status}): {error_text[:200]}"
                    )
                    
    except Exception as e:
        return TestVLLMConnectionResponse(
            success=False,
            message=f"Connection error: {str(e)}"
        )
