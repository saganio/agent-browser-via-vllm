"""
Tests for Xray API clients
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import ClientResponseError

from app.xray.client import (
    XrayCloudClient, XrayServerClient, get_xray_client,
    XrayClientError, XrayAuthError, XrayNotFoundError
)
from app.xray.models import XrayConfig, XrayInstanceType


@pytest.fixture
def cloud_config():
    """Create a mock Xray Cloud config"""
    config = MagicMock(spec=XrayConfig)
    config.instance_type = XrayInstanceType.CLOUD
    config.base_url = "https://xray.cloud.getxray.app"
    config.client_id = "test_client_id"
    config.client_secret = "test_client_secret"
    config.jira_project_key = "PROJ"
    config.username = None
    config.api_token = None
    return config


@pytest.fixture
def server_config():
    """Create a mock Xray Server config"""
    config = MagicMock(spec=XrayConfig)
    config.instance_type = XrayInstanceType.SERVER
    config.base_url = "https://jira.example.com"
    config.client_id = None
    config.client_secret = None
    config.username = "testuser"
    config.api_token = "test_token"
    config.jira_project_key = "PROJ"
    return config


class TestGetXrayClient:
    """Tests for the client factory function"""
    
    def test_returns_cloud_client_for_cloud_config(self, cloud_config):
        """Should return XrayCloudClient for cloud instance type"""
        client = get_xray_client(cloud_config)
        assert isinstance(client, XrayCloudClient)
    
    def test_returns_server_client_for_server_config(self, server_config):
        """Should return XrayServerClient for server instance type"""
        client = get_xray_client(server_config)
        assert isinstance(client, XrayServerClient)


class TestXrayCloudClient:
    """Tests for XrayCloudClient"""
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, cloud_config):
        """Should authenticate successfully with valid credentials"""
        client = XrayCloudClient(cloud_config)
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='"test_token"')
        
        with patch.object(client, '_ensure_session', new_callable=AsyncMock):
            client._session = MagicMock()
            client._session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            
            result = await client.authenticate()
            
            assert result is True
            assert client._token == "test_token"
    
    @pytest.mark.asyncio
    async def test_authenticate_failure(self, cloud_config):
        """Should raise XrayAuthError on authentication failure"""
        client = XrayCloudClient(cloud_config)
        
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value='Invalid credentials')
        
        with patch.object(client, '_ensure_session', new_callable=AsyncMock):
            client._session = MagicMock()
            client._session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            
            with pytest.raises(XrayAuthError):
                await client.authenticate()
    
    @pytest.mark.asyncio
    async def test_authenticate_requires_credentials(self, cloud_config):
        """Should raise error when credentials are missing"""
        cloud_config.client_id = None
        cloud_config.client_secret = None
        
        client = XrayCloudClient(cloud_config)
        
        with pytest.raises(XrayAuthError, match="Client ID and Client Secret are required"):
            await client.authenticate()
    
    def test_auth_headers(self, cloud_config):
        """Should return proper bearer token headers"""
        client = XrayCloudClient(cloud_config)
        client._token = "test_token"
        
        headers = client._auth_headers()
        
        assert headers["Authorization"] == "Bearer test_token"
        assert headers["Content-Type"] == "application/json"
    
    def test_map_status(self, cloud_config):
        """Should map internal status to Xray Cloud status"""
        assert XrayCloudClient._map_status("PENDING") == "TODO"
        assert XrayCloudClient._map_status("PASSED") == "PASSED"
        assert XrayCloudClient._map_status("FAILED") == "FAILED"
        assert XrayCloudClient._map_status("SKIPPED") == "SKIPPED"
        assert XrayCloudClient._map_status("BLOCKED") == "BLOCKED"
        assert XrayCloudClient._map_status("UNKNOWN") == "TODO"


class TestXrayServerClient:
    """Tests for XrayServerClient"""
    
    def test_auth_headers(self, server_config):
        """Should return proper basic auth headers"""
        client = XrayServerClient(server_config)
        
        headers = client._auth_headers()
        
        # Base64 encoded "testuser:test_token"
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")
        assert headers["Content-Type"] == "application/json"
    
    def test_auth_headers_requires_credentials(self, server_config):
        """Should raise error when credentials are missing"""
        server_config.username = None
        server_config.api_token = None
        
        client = XrayServerClient(server_config)
        
        with pytest.raises(XrayAuthError, match="Username and API token are required"):
            client._auth_headers()
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self, server_config):
        """Should return success for valid connection"""
        client = XrayServerClient(server_config)
        
        mock_result = {
            "serverTitle": "Test Jira",
            "version": "8.20.0"
        }
        
        with patch.object(client, '_ensure_session', new_callable=AsyncMock):
            with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
                mock_request.return_value = mock_result
                
                result = await client.test_connection()
                
                assert result["success"] is True
                assert "Test Jira" in result["message"]
                assert result["xray_version"] == "8.20.0"
    
    def test_map_status(self, server_config):
        """Should map internal status to Xray Server status"""
        assert XrayServerClient._map_status("PENDING") == "TODO"
        assert XrayServerClient._map_status("PASSED") == "PASS"
        assert XrayServerClient._map_status("FAILED") == "FAIL"
        assert XrayServerClient._map_status("SKIPPED") == "SKIPPED"
        assert XrayServerClient._map_status("BLOCKED") == "BLOCKED"


class TestBaseXrayClientRequest:
    """Tests for the base request method"""
    
    @pytest.mark.asyncio
    async def test_request_handles_401(self, cloud_config):
        """Should raise XrayAuthError on 401 response"""
        client = XrayCloudClient(cloud_config)
        
        mock_response = MagicMock()
        mock_response.status = 401
        
        with patch.object(client, '_ensure_session', new_callable=AsyncMock):
            client._session = MagicMock()
            client._session.request = MagicMock(
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
            )
            
            with pytest.raises(XrayAuthError):
                await client._request("GET", "https://test.com/api")
    
    @pytest.mark.asyncio
    async def test_request_handles_404(self, cloud_config):
        """Should raise XrayNotFoundError on 404 response"""
        client = XrayCloudClient(cloud_config)
        
        mock_response = MagicMock()
        mock_response.status = 404
        
        with patch.object(client, '_ensure_session', new_callable=AsyncMock):
            client._session = MagicMock()
            client._session.request = MagicMock(
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
            )
            
            with pytest.raises(XrayNotFoundError):
                await client._request("GET", "https://test.com/api/missing")
    
    @pytest.mark.asyncio
    async def test_request_handles_other_errors(self, cloud_config):
        """Should raise XrayClientError on other error responses"""
        client = XrayCloudClient(cloud_config)
        
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        
        with patch.object(client, '_ensure_session', new_callable=AsyncMock):
            client._session = MagicMock()
            client._session.request = MagicMock(
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
            )
            
            with pytest.raises(XrayClientError) as exc_info:
                await client._request("GET", "https://test.com/api")
            
            assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_request_returns_json(self, cloud_config):
        """Should return JSON response for successful requests"""
        client = XrayCloudClient(cloud_config)
        
        expected_data = {"key": "value"}
        
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.content_type = "application/json"
        mock_response.json = AsyncMock(return_value=expected_data)
        
        with patch.object(client, '_ensure_session', new_callable=AsyncMock):
            client._session = MagicMock()
            client._session.request = MagicMock(
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
            )
            
            result = await client._request("GET", "https://test.com/api")
            
            assert result == expected_data
