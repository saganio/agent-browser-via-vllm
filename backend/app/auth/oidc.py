"""
OIDC Authentication Client
"""

from authlib.integrations.starlette_client import OAuth
from authlib.integrations.base_client import OAuthError
from starlette.requests import Request
from typing import Optional, Dict, Any
import httpx

from app.config import settings


# Initialize OAuth client
oauth = OAuth()

# Register OIDC provider if configured
if settings.OIDC_DISCOVERY_URL:
    oauth.register(
        name='oidc',
        client_id=settings.OIDC_CLIENT_ID,
        client_secret=settings.OIDC_CLIENT_SECRET,
        server_metadata_url=settings.OIDC_DISCOVERY_URL,
        client_kwargs={
            'scope': 'openid profile email',
            'token_endpoint_auth_method': 'client_secret_post',
        }
    )


class OIDCClient:
    """OIDC client for handling authentication flows"""
    
    def __init__(self):
        self.discovery_url = settings.OIDC_DISCOVERY_URL
        self.client_id = settings.OIDC_CLIENT_ID
        self.client_secret = settings.OIDC_CLIENT_SECRET
        self.redirect_uri = settings.OIDC_REDIRECT_URI
        self._metadata: Optional[Dict[str, Any]] = None
    
    @property
    def is_configured(self) -> bool:
        """Check if OIDC is properly configured"""
        return all([
            self.discovery_url,
            self.client_id,
            self.client_secret,
        ])
    
    async def get_metadata(self) -> Dict[str, Any]:
        """Fetch OIDC provider metadata"""
        if self._metadata:
            return self._metadata
        
        if not self.discovery_url:
            raise ValueError("OIDC discovery URL not configured")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.discovery_url)
            response.raise_for_status()
            self._metadata = response.json()
            return self._metadata
    
    async def get_authorization_url(self, state: str) -> str:
        """Generate authorization URL for OIDC login"""
        metadata = await self.get_metadata()
        auth_endpoint = metadata.get('authorization_endpoint')
        
        if not auth_endpoint:
            raise ValueError("Authorization endpoint not found in OIDC metadata")
        
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'openid profile email',
            'state': state,
        }
        
        query = '&'.join(f"{k}={v}" for k, v in params.items())
        return f"{auth_endpoint}?{query}"
    
    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens"""
        metadata = await self.get_metadata()
        token_endpoint = metadata.get('token_endpoint')
        
        if not token_endpoint:
            raise ValueError("Token endpoint not found in OIDC metadata")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_endpoint,
                data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': self.redirect_uri,
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def get_userinfo(self, access_token: str) -> Dict[str, Any]:
        """Fetch user information from OIDC provider"""
        metadata = await self.get_metadata()
        userinfo_endpoint = metadata.get('userinfo_endpoint')
        
        if not userinfo_endpoint:
            raise ValueError("Userinfo endpoint not found in OIDC metadata")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                userinfo_endpoint,
                headers={'Authorization': f'Bearer {access_token}'}
            )
            response.raise_for_status()
            return response.json()
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token"""
        metadata = await self.get_metadata()
        token_endpoint = metadata.get('token_endpoint')
        
        if not token_endpoint:
            raise ValueError("Token endpoint not found in OIDC metadata")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_endpoint,
                data={
                    'grant_type': 'refresh_token',
                    'refresh_token': refresh_token,
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                }
            )
            response.raise_for_status()
            return response.json()


# Global OIDC client instance
oidc_client = OIDCClient()
