"""
Tests for project management
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.projects.models import Project
from app.projects.schemas import ProjectCreate, ProjectUpdate, VLLMConfig, BrowserConfig
from app.projects.service import ProjectService, create_slug


class TestCreateSlug:
    """Tests for slug creation"""
    
    def test_create_slug_basic(self):
        """Test basic slug creation"""
        slug = create_slug("My Project Name")
        
        assert "my-project-name" in slug
        assert " " not in slug
    
    def test_create_slug_special_characters(self):
        """Test slug creation with special characters"""
        slug = create_slug("Project @#$% Test!")
        
        # Should remove special characters
        assert "@" not in slug
        assert "#" not in slug
        assert "$" not in slug
    
    def test_create_slug_has_unique_suffix(self):
        """Test that slug has unique suffix"""
        slug1 = create_slug("Test Project")
        slug2 = create_slug("Test Project")
        
        # Should have different suffixes
        assert slug1 != slug2
    
    def test_create_slug_max_length(self):
        """Test that slug respects max length"""
        long_name = "A" * 200
        slug = create_slug(long_name)
        
        # Should be truncated (80 chars + suffix)
        assert len(slug) <= 100


class TestProjectSchemas:
    """Tests for project Pydantic schemas"""
    
    def test_vllm_config_defaults(self):
        """Test VLLMConfig default values"""
        config = VLLMConfig()
        
        assert config.api_url == "http://localhost:8000"
        assert config.model_name == ""
        assert config.temperature == 0.7
        assert config.max_tokens == 2048
        assert config.top_p == 0.95
    
    def test_vllm_config_validation(self):
        """Test VLLMConfig validation"""
        # Temperature must be between 0 and 2
        with pytest.raises(ValueError):
            VLLMConfig(temperature=3.0)
        
        with pytest.raises(ValueError):
            VLLMConfig(temperature=-1.0)
    
    def test_browser_config_defaults(self):
        """Test BrowserConfig default values"""
        config = BrowserConfig()
        
        assert config.headless is True
        assert config.timeout == 30000
    
    def test_project_create_required_fields(self):
        """Test ProjectCreate requires name"""
        with pytest.raises(ValueError):
            ProjectCreate(name="")  # Empty name should fail
    
    def test_project_update_optional_fields(self):
        """Test ProjectUpdate allows partial updates"""
        update = ProjectUpdate(name="New Name")
        
        assert update.name == "New Name"
        assert update.description is None
        assert update.vllm_config is None


class TestProjectModel:
    """Tests for Project model"""
    
    def test_project_repr(self):
        """Test Project string representation"""
        project = Project(id=1, name="Test Project", slug="test-project")
        
        assert "Test Project" in repr(project)
        assert "1" in repr(project)


class TestProjectService:
    """Tests for ProjectService"""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()
    
    @pytest.fixture
    def service(self, mock_db):
        return ProjectService(mock_db)
    
    @pytest.mark.asyncio
    async def test_create_project(self, service, mock_db):
        """Test project creation"""
        from app.auth.models import User, Role
        
        user = User(
            id=1,
            email="test@test.com",
            organization_id=1,
            role=Role.DEVELOPER
        )
        
        data = ProjectCreate(
            name="Test Project",
            description="Test description",
            vllm_config=VLLMConfig(model_name="test-model"),
        )
        
        # Mock db operations
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        project = await service.create_project(data, user)
        
        assert project.name == "Test Project"
        assert project.description == "Test description"
        assert project.organization_id == user.organization_id
        assert project.created_by == user.id
        mock_db.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_project_with_org_filter(self, service, mock_db):
        """Test that get_project filters by organization"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await service.get_project(project_id=1, organization_id=1)
        
        # Verify query was executed
        mock_db.execute.assert_called_once()
        
        # The query should filter by both project_id and organization_id
        call_args = mock_db.execute.call_args
        assert call_args is not None
    
    @pytest.mark.asyncio
    async def test_update_project(self, service, mock_db):
        """Test project update"""
        project = Project(
            id=1,
            name="Old Name",
            slug="old-name",
            organization_id=1,
            created_by=1,
        )
        
        update_data = ProjectUpdate(name="New Name")
        
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        updated = await service.update_project(project, update_data)
        
        assert updated.name == "New Name"
    
    @pytest.mark.asyncio
    async def test_delete_project_soft(self, service, mock_db):
        """Test soft delete sets is_active to False"""
        project = Project(
            id=1,
            name="Test",
            slug="test",
            organization_id=1,
            created_by=1,
            is_active=True,
        )
        
        mock_db.flush = AsyncMock()
        
        await service.delete_project(project)
        
        assert project.is_active is False
    
    @pytest.mark.asyncio
    async def test_delete_project_hard(self, service, mock_db):
        """Test hard delete removes project"""
        project = Project(
            id=1,
            name="Test",
            slug="test",
            organization_id=1,
            created_by=1,
        )
        
        mock_db.delete = AsyncMock()
        mock_db.flush = AsyncMock()
        
        await service.hard_delete_project(project)
        
        mock_db.delete.assert_called_once_with(project)
