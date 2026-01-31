"""
Tests for Xray service layer
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.xray.service import XrayService
from app.xray.models import (
    XrayConfig, XrayTestSet, XrayTest, XrayStepResult,
    XrayInstanceType, XrayTestType, XraySyncStatus, XrayStepStatus
)
from app.xray.schemas import XrayConfigCreate, SyncTestSetsRequest
from app.projects.models import Project


@pytest.fixture
def mock_db():
    """Create a mock database session"""
    db = AsyncMock()
    db.add = MagicMock()
    db.delete = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.fixture
def xray_service(mock_db):
    """Create an XrayService instance with mock db"""
    return XrayService(mock_db)


@pytest.fixture
def mock_config():
    """Create a mock XrayConfig"""
    config = MagicMock(spec=XrayConfig)
    config.id = 1
    config.project_id = 1
    config.instance_type = XrayInstanceType.CLOUD
    config.base_url = "https://xray.cloud.getxray.app"
    config.client_id = "test_client"
    config.client_secret = "test_secret"
    config.jira_project_key = "PROJ"
    config.auto_sync = False
    config.auto_export = True
    config.sync_interval_minutes = 60
    return config


@pytest.fixture
def mock_test_set():
    """Create a mock XrayTestSet"""
    test_set = MagicMock(spec=XrayTestSet)
    test_set.id = 1
    test_set.xray_config_id = 1
    test_set.xray_issue_key = "PROJ-100"
    test_set.name = "Login Test Set"
    test_set.description = "Tests for login functionality"
    test_set.test_count = 3
    test_set.sync_status = XraySyncStatus.SYNCED
    return test_set


@pytest.fixture
def mock_test():
    """Create a mock XrayTest"""
    test = MagicMock(spec=XrayTest)
    test.id = 1
    test.test_set_id = 1
    test.xray_issue_key = "PROJ-101"
    test.name = "Valid login test"
    test.description = "Test valid user login"
    test.test_type = XrayTestType.MANUAL
    test.manual_steps = [
        {"index": 0, "action": "Go to login page", "data": "", "expected": "Login page is displayed"},
        {"index": 1, "action": "Enter valid credentials", "data": "user@test.com", "expected": "Credentials accepted"},
        {"index": 2, "action": "Click login button", "data": "", "expected": "User is logged in"},
    ]
    test.gherkin_scenario = None
    test.preconditions = "User must exist in the system"
    test.priority = "High"
    test.rank = 0
    return test


class TestTestToCommand:
    """Tests for converting tests to commands"""
    
    def test_manual_test_to_command(self, xray_service, mock_test):
        """Should convert manual test steps to command"""
        command = xray_service.test_to_command(mock_test)
        
        assert "Valid login test" in command
        assert "Steps to execute" in command
        assert "Go to login page" in command
        assert "Enter valid credentials" in command
        assert "Click login button" in command
    
    def test_manual_test_with_preconditions(self, xray_service, mock_test):
        """Should include preconditions in command"""
        command = xray_service.test_to_command(mock_test)
        
        assert "Preconditions" in command
        assert "User must exist" in command
    
    def test_gherkin_test_to_command(self, xray_service, mock_test):
        """Should convert Gherkin test to command"""
        mock_test.test_type = XrayTestType.GHERKIN
        mock_test.manual_steps = []
        mock_test.gherkin_scenario = """
        Scenario: User login
        Given I am on the login page
        When I enter valid credentials
        Then I should be logged in
        """
        
        command = xray_service.test_to_command(mock_test)
        
        # The command should contain the scenario steps
        assert "login" in command.lower()


class TestGetConfig:
    """Tests for getting Xray config"""
    
    @pytest.mark.asyncio
    async def test_get_config_found(self, xray_service, mock_db, mock_config):
        """Should return config when found"""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_config
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await xray_service.get_config(1, 1)
        
        assert result == mock_config
    
    @pytest.mark.asyncio
    async def test_get_config_not_found(self, xray_service, mock_db):
        """Should return None when config not found"""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await xray_service.get_config(999, 1)
        
        assert result is None


class TestCreateConfig:
    """Tests for creating Xray config"""
    
    @pytest.mark.asyncio
    async def test_create_config_project_not_found(self, xray_service, mock_db):
        """Should raise error when project not found"""
        from app.xray.schemas import XrayInstanceTypeEnum
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        create_data = XrayConfigCreate(
            project_id=999,
            instance_type=XrayInstanceTypeEnum.CLOUD,
            base_url="https://xray.cloud.getxray.app",
            jira_project_key="PROJ",
        )
        
        with pytest.raises(ValueError, match="Project not found"):
            await xray_service.create_config(create_data, 1)


class TestSyncTestSets:
    """Tests for syncing test sets from Xray"""
    
    def test_sync_request_defaults(self):
        """SyncTestSetsRequest should have sensible defaults"""
        request = SyncTestSetsRequest()
        assert request.test_set_keys is None
        assert request.force is False
    
    def test_sync_request_with_keys(self):
        """SyncTestSetsRequest should accept test set keys"""
        request = SyncTestSetsRequest(test_set_keys=["PROJ-1", "PROJ-2"], force=True)
        assert request.test_set_keys == ["PROJ-1", "PROJ-2"]
        assert request.force is True


class TestListTestSets:
    """Tests for listing test sets"""
    
    @pytest.mark.asyncio
    async def test_list_test_sets_with_results(self, xray_service, mock_db, mock_config, mock_test_set):
        """Should return test sets with pagination"""
        # Mock get_config_by_id
        mock_config_result = MagicMock()
        mock_config_result.scalars.return_value.first.return_value = mock_config
        
        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 5
        
        # Mock list query
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value.all.return_value = [mock_test_set]
        
        mock_db.execute = AsyncMock(side_effect=[
            mock_config_result,  # get_config_by_id
            mock_count_result,   # count
            mock_list_result,    # list
        ])
        
        result, total = await xray_service.list_test_sets(
            config_id=1,
            organization_id=1,
            page=1,
            page_size=20
        )
        
        assert total == 5
        assert len(result) == 1
        assert result[0] == mock_test_set


class TestCreateStepResults:
    """Tests for creating step results"""
    
    def test_gherkin_parser_integration(self, xray_service):
        """Should have a Gherkin parser available"""
        assert xray_service.gherkin_parser is not None
    
    def test_test_to_command_generates_output(self, xray_service, mock_test):
        """Should generate a command string from a test"""
        command = xray_service.test_to_command(mock_test)
        assert isinstance(command, str)
        assert len(command) > 0


class TestUpdateStepResult:
    """Tests for updating step results"""
    
    @pytest.mark.asyncio
    async def test_update_step_result_success(self, xray_service, mock_db):
        """Should update step result status"""
        mock_step_result = MagicMock(spec=XrayStepResult)
        mock_step_result.id = 1
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_step_result
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await xray_service.update_step_result(
            step_result_id=1,
            status=XrayStepStatus.PASSED,
            actual_result="Test passed successfully",
            duration_ms=1500
        )
        
        assert result.status == XrayStepStatus.PASSED
        assert result.actual_result == "Test passed successfully"
        assert result.duration_ms == 1500
        assert mock_db.flush.called


class TestGetStepResults:
    """Tests for getting step results"""
    
    @pytest.mark.asyncio
    async def test_get_step_results(self, xray_service, mock_db):
        """Should return step results for a test run"""
        mock_step_results = [
            MagicMock(spec=XrayStepResult, step_index=0),
            MagicMock(spec=XrayStepResult, step_index=1),
            MagicMock(spec=XrayStepResult, step_index=2),
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_step_results
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        results = await xray_service.get_step_results(test_run_id=1)
        
        assert len(results) == 3
