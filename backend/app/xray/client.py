"""
Xray API clients for Cloud and Server/Data Center
"""

import aiohttp
import base64
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from app.xray.models import XrayConfig, XrayInstanceType

logger = logging.getLogger(__name__)


class XrayClientError(Exception):
    """Base exception for Xray client errors"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class XrayAuthError(XrayClientError):
    """Authentication error"""
    pass


class XrayNotFoundError(XrayClientError):
    """Resource not found"""
    pass


class XrayRateLimitError(XrayClientError):
    """Rate limit exceeded error"""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class BaseXrayClient(ABC):
    """Abstract base class for Xray API clients"""
    
    def __init__(self, config: XrayConfig):
        self.config = config
        self.base_url = config.base_url.rstrip('/')
        self._session: Optional[aiohttp.ClientSession] = None
        self._token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
    
    async def __aenter__(self):
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def _ensure_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the Xray API"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """Test the connection and return info"""
        pass
    
    @abstractmethod
    async def get_test_sets(self, project_key: str) -> List[Dict[str, Any]]:
        """Get all test sets for a project"""
        pass
    
    @abstractmethod
    async def get_test_set(self, issue_key: str) -> Dict[str, Any]:
        """Get a specific test set by key"""
        pass
    
    @abstractmethod
    async def get_tests_in_test_set(self, test_set_key: str) -> List[Dict[str, Any]]:
        """Get all tests in a test set"""
        pass
    
    @abstractmethod
    async def get_test(self, issue_key: str) -> Dict[str, Any]:
        """Get a specific test by key"""
        pass
    
    @abstractmethod
    async def create_test_execution(
        self,
        project_key: str,
        test_results: List[Dict[str, Any]],
        summary: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a test execution with results"""
        pass
    
    async def _request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        max_retries: int = 3,
        retry_base_delay_ms: int = 1000,
    ) -> Dict[str, Any]:
        """Make an HTTP request with retry logic for rate limiting"""
        import asyncio
        from app.config import settings
        
        await self._ensure_session()
        
        # Use settings if available, otherwise use defaults
        max_retries = getattr(settings, 'XRAY_MAX_RETRIES', max_retries)
        retry_base_delay_ms = getattr(settings, 'XRAY_RETRY_BASE_DELAY_MS', retry_base_delay_ms)
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                async with self._session.request(method, url, headers=headers, json=json, data=data) as response:
                    if response.status == 401:
                        raise XrayAuthError("Authentication failed (401 Unauthorized)", status_code=401)
                    elif response.status == 403:
                        text = await response.text()
                        # Extract meaningful error from HTML if present
                        error_detail = ""
                        if "AUTHENTICATION_DENIED" in text:
                            error_detail = " - Basic authentication may be disabled or CAPTCHA required"
                        elif "CAPTCHA" in text.upper():
                            error_detail = " - CAPTCHA challenge required, please log in via browser"
                        raise XrayAuthError(f"Access forbidden (403){error_detail}", status_code=403)
                    elif response.status == 404:
                        raise XrayNotFoundError(f"Resource not found: {url}", status_code=404)
                    elif response.status == 429:
                        # Rate limit exceeded
                        text = await response.text()
                        retry_after = response.headers.get('Retry-After')
                        retry_seconds = int(retry_after) if retry_after and retry_after.isdigit() else None
                        
                        if attempt < max_retries:
                            # Calculate delay with exponential backoff
                            if retry_seconds:
                                delay = retry_seconds
                            else:
                                delay = (retry_base_delay_ms * (2 ** attempt)) / 1000  # Convert to seconds
                            
                            logger.warning(
                                f"Rate limited (429). Attempt {attempt + 1}/{max_retries + 1}. "
                                f"Retrying in {delay:.1f}s. URL: {url}"
                            )
                            await asyncio.sleep(delay)
                            continue
                        else:
                            raise XrayRateLimitError(
                                f"Rate limit exceeded after {max_retries + 1} attempts: {text[:500]}",
                                retry_after=retry_seconds
                            )
                    elif response.status >= 400:
                        text = await response.text()
                        raise XrayClientError(f"Request failed ({response.status}): {text[:500]}", status_code=response.status)
                    
                    if response.content_type == 'application/json':
                        return await response.json()
                    return {"text": await response.text()}
                    
            except (XrayAuthError, XrayNotFoundError, XrayRateLimitError):
                # Don't retry auth or not found errors
                raise
            except XrayClientError as e:
                last_exception = e
                if attempt < max_retries and e.status_code not in (401, 403, 404):
                    delay = (retry_base_delay_ms * (2 ** attempt)) / 1000
                    logger.warning(f"Request failed, retrying in {delay:.1f}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    raise
        
        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
        raise XrayClientError("Request failed after retries")


class XrayCloudClient(BaseXrayClient):
    """Xray Cloud API client (cloud.getxray.app)"""
    
    CLOUD_AUTH_URL = "https://xray.cloud.getxray.app/api/v2/authenticate"
    CLOUD_API_BASE = "https://xray.cloud.getxray.app/api/v2"
    GRAPHQL_URL = "https://xray.cloud.getxray.app/api/v2/graphql"
    
    def __init__(self, config: XrayConfig):
        super().__init__(config)
        self.client_id = config.client_id
        self.client_secret = config.client_secret
    
    async def authenticate(self) -> bool:
        """Authenticate with Xray Cloud using client credentials"""
        if not self.client_id or not self.client_secret:
            raise XrayAuthError("Client ID and Client Secret are required for Cloud authentication")
        
        await self._ensure_session()
        
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        async with self._session.post(self.CLOUD_AUTH_URL, json=payload) as response:
            if response.status != 200:
                text = await response.text()
                raise XrayAuthError(f"Authentication failed: {text}", status_code=response.status)
            
            # Response is the token string directly
            self._token = await response.text()
            self._token = self._token.strip('"')  # Remove quotes if present
            return True
    
    def _auth_headers(self) -> Dict[str, str]:
        """Get headers with authentication"""
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json"
        }
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection by authenticating"""
        await self.authenticate()
        return {
            "success": True,
            "message": "Successfully connected to Xray Cloud",
            "xray_version": "Cloud",
        }
    
    async def get_test_sets(self, project_key: str) -> List[Dict[str, Any]]:
        """Get test sets using GraphQL"""
        await self._ensure_authenticated()
        
        query = """
        query GetTestSets($projectKey: String!, $limit: Int!) {
            getTestSets(projectId: $projectKey, limit: $limit) {
                total
                results {
                    issueId
                    jira(fields: ["key", "summary", "description", "labels"])
                }
            }
        }
        """
        
        variables = {
            "projectKey": project_key,
            "limit": 100
        }
        
        result = await self._graphql_request(query, variables)
        
        test_sets = []
        for item in result.get("data", {}).get("getTestSets", {}).get("results", []):
            jira_data = item.get("jira", {})
            test_sets.append({
                "issue_id": item.get("issueId"),
                "key": jira_data.get("key"),
                "summary": jira_data.get("summary"),
                "description": jira_data.get("description"),
                "labels": jira_data.get("labels", []),
            })
        
        return test_sets
    
    async def get_test_set(self, issue_key: str) -> Dict[str, Any]:
        """Get a specific test set"""
        await self._ensure_authenticated()
        
        query = """
        query GetTestSet($issueId: String!) {
            getTestSet(issueId: $issueId) {
                issueId
                jira(fields: ["key", "summary", "description", "labels", "components", "fixVersions"])
                tests(limit: 100) {
                    total
                    results {
                        issueId
                        jira(fields: ["key", "summary"])
                    }
                }
            }
        }
        """
        
        variables = {"issueId": issue_key}
        result = await self._graphql_request(query, variables)
        
        test_set_data = result.get("data", {}).get("getTestSet", {})
        if not test_set_data:
            raise XrayNotFoundError(f"Test set not found: {issue_key}")
        
        jira_data = test_set_data.get("jira", {})
        tests_data = test_set_data.get("tests", {})
        
        return {
            "issue_id": test_set_data.get("issueId"),
            "key": jira_data.get("key"),
            "summary": jira_data.get("summary"),
            "description": jira_data.get("description"),
            "labels": jira_data.get("labels", []),
            "components": [c.get("name") for c in jira_data.get("components", [])],
            "fix_versions": [v.get("name") for v in jira_data.get("fixVersions", [])],
            "test_count": tests_data.get("total", 0),
            "tests": [
                {"issue_id": t.get("issueId"), "key": t.get("jira", {}).get("key"), "summary": t.get("jira", {}).get("summary")}
                for t in tests_data.get("results", [])
            ]
        }
    
    async def get_tests_in_test_set(self, test_set_key: str) -> List[Dict[str, Any]]:
        """Get all tests in a test set"""
        await self._ensure_authenticated()
        
        query = """
        query GetTestsInTestSet($issueId: String!, $limit: Int!) {
            getTestSet(issueId: $issueId) {
                tests(limit: $limit) {
                    total
                    results {
                        issueId
                        testType { name }
                        gherkin
                        steps {
                            id
                            action
                            data
                            result
                        }
                        preconditions(limit: 10) {
                            results {
                                definition
                            }
                        }
                        jira(fields: ["key", "summary", "description", "labels", "priority"])
                    }
                }
            }
        }
        """
        
        variables = {"issueId": test_set_key, "limit": 100}
        result = await self._graphql_request(query, variables)
        
        tests = []
        for idx, item in enumerate(result.get("data", {}).get("getTestSet", {}).get("tests", {}).get("results", [])):
            jira_data = item.get("jira", {})
            test_type = item.get("testType", {}).get("name", "Manual")
            
            # Get preconditions
            preconditions = []
            for pc in item.get("preconditions", {}).get("results", []):
                if pc.get("definition"):
                    preconditions.append(pc["definition"])
            
            test_data = {
                "issue_id": item.get("issueId"),
                "key": jira_data.get("key"),
                "summary": jira_data.get("summary"),
                "description": jira_data.get("description"),
                "labels": jira_data.get("labels", []),
                "priority": jira_data.get("priority", {}).get("name") if isinstance(jira_data.get("priority"), dict) else jira_data.get("priority"),
                "test_type": "gherkin" if test_type.lower() in ["cucumber", "gherkin"] else "manual",
                "preconditions": "\n".join(preconditions) if preconditions else None,
                "rank": idx,
            }
            
            if test_data["test_type"] == "gherkin":
                test_data["gherkin_scenario"] = item.get("gherkin", "")
            else:
                test_data["manual_steps"] = [
                    {
                        "index": i,
                        "action": step.get("action", ""),
                        "data": step.get("data", ""),
                        "expected": step.get("result", "")
                    }
                    for i, step in enumerate(item.get("steps", []))
                ]
            
            tests.append(test_data)
        
        return tests
    
    async def get_test(self, issue_key: str) -> Dict[str, Any]:
        """Get a specific test"""
        await self._ensure_authenticated()
        
        query = """
        query GetTest($issueId: String!) {
            getTest(issueId: $issueId) {
                issueId
                testType { name }
                gherkin
                steps {
                    id
                    action
                    data
                    result
                }
                preconditions(limit: 10) {
                    results {
                        definition
                    }
                }
                jira(fields: ["key", "summary", "description", "labels", "priority"])
            }
        }
        """
        
        variables = {"issueId": issue_key}
        result = await self._graphql_request(query, variables)
        
        test_data = result.get("data", {}).get("getTest", {})
        if not test_data:
            raise XrayNotFoundError(f"Test not found: {issue_key}")
        
        jira_data = test_data.get("jira", {})
        test_type = test_data.get("testType", {}).get("name", "Manual")
        
        response = {
            "issue_id": test_data.get("issueId"),
            "key": jira_data.get("key"),
            "summary": jira_data.get("summary"),
            "description": jira_data.get("description"),
            "labels": jira_data.get("labels", []),
            "priority": jira_data.get("priority", {}).get("name") if isinstance(jira_data.get("priority"), dict) else jira_data.get("priority"),
            "test_type": "gherkin" if test_type.lower() in ["cucumber", "gherkin"] else "manual",
        }
        
        if response["test_type"] == "gherkin":
            response["gherkin_scenario"] = test_data.get("gherkin", "")
        else:
            response["manual_steps"] = [
                {
                    "index": i,
                    "action": step.get("action", ""),
                    "data": step.get("data", ""),
                    "expected": step.get("result", "")
                }
                for i, step in enumerate(test_data.get("steps", []))
            ]
        
        return response
    
    async def create_test_execution(
        self,
        project_key: str,
        test_results: List[Dict[str, Any]],
        summary: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a test execution with results"""
        await self._ensure_authenticated()
        
        # Build the execution payload for Xray Cloud REST API
        execution_payload = {
            "info": {
                "project": project_key,
                "summary": summary or f"Test Execution - {datetime.now().isoformat()}",
                "description": description or "Automated test execution from Browser Test Platform",
            },
            "tests": []
        }
        
        for result in test_results:
            test_entry = {
                "testKey": result.get("test_key"),
                "status": self._map_status(result.get("status", "PENDING")),
                "comment": result.get("comment", ""),
            }
            
            # Add step results if available
            if result.get("steps"):
                test_entry["steps"] = [
                    {
                        "status": self._map_status(step.get("status", "PENDING")),
                        "actualResult": step.get("actual_result", ""),
                        "comment": step.get("comment", ""),
                    }
                    for step in result["steps"]
                ]
            
            execution_payload["tests"].append(test_entry)
        
        # POST to create execution
        url = f"{self.CLOUD_API_BASE}/import/execution"
        response = await self._request("POST", url, headers=self._auth_headers(), json=execution_payload)
        
        return {
            "execution_key": response.get("key"),
            "execution_id": response.get("id"),
            "self": response.get("self"),
        }
    
    async def _ensure_authenticated(self):
        """Ensure we have a valid token"""
        if not self._token:
            await self.authenticate()
    
    async def _graphql_request(self, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Make a GraphQL request"""
        payload = {"query": query, "variables": variables}
        return await self._request("POST", self.GRAPHQL_URL, headers=self._auth_headers(), json=payload)
    
    @staticmethod
    def _map_status(status: str) -> str:
        """Map internal status to Xray status"""
        status_map = {
            "PENDING": "TODO",
            "PASSED": "PASSED",
            "FAILED": "FAILED",
            "SKIPPED": "SKIPPED",
            "BLOCKED": "BLOCKED",
        }
        return status_map.get(status.upper(), "TODO")


class XrayServerClient(BaseXrayClient):
    """Xray Server/Data Center API client"""
    
    def __init__(self, config: XrayConfig):
        super().__init__(config)
        self.username = config.username
        self.api_token = config.api_token
        self._use_bearer = False  # Will be set during authentication
        self._authenticated = False
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get auth headers using the authentication method determined during auth"""
        return self._auth_headers(use_bearer=self._use_bearer)
    
    def _auth_headers(self, use_bearer: bool = False) -> Dict[str, str]:
        """Get headers with authentication.
        
        Args:
            use_bearer: If True, use Bearer token auth with PAT only.
                       If False (default), use Basic auth with username:PAT.
        """
        if not self.api_token:
            raise XrayAuthError("API token (PAT) is required for Server authentication")
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Atlassian-Token": "no-check"  # Helps bypass some CSRF checks
        }
        
        if use_bearer:
            # Bearer token auth - PAT only
            headers["Authorization"] = f"Bearer {self.api_token}"
        else:
            # Basic auth - username:PAT
            if not self.username:
                raise XrayAuthError("Username is required for Basic authentication")
            credentials = base64.b64encode(f"{self.username}:{self.api_token}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        
        return headers
    
    async def authenticate(self) -> bool:
        """Verify authentication by making a simple request"""
        await self._ensure_session()
        
        # Try Bearer token first (modern PAT auth), then fall back to Basic auth
        url = f"{self.base_url}/rest/api/2/serverInfo"
        
        try:
            await self._request("GET", url, headers=self._auth_headers(use_bearer=True))
            self._use_bearer = True
            return True
        except XrayAuthError:
            # Fall back to Basic auth
            try:
                await self._request("GET", url, headers=self._auth_headers(use_bearer=False))
                self._use_bearer = False
                return True
            except XrayAuthError:
                raise XrayAuthError(
                    "Authentication failed. Please check: "
                    "1) Your username and PAT are correct. "
                    "2) PAT has sufficient permissions. "
                    "3) Basic/Bearer authentication is enabled on your Jira instance. "
                    "4) You may need to solve a CAPTCHA by logging in via browser first."
                )
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection by getting server info"""
        await self._ensure_session()
        
        url = f"{self.base_url}/rest/api/2/serverInfo"
        
        # Try Bearer token auth first
        try:
            result = await self._request("GET", url, headers=self._auth_headers(use_bearer=True))
            self._use_bearer = True
            return {
                "success": True,
                "message": f"Successfully connected to {result.get('serverTitle', 'Jira Server')} (Bearer auth)",
                "xray_version": result.get("version", "Unknown"),
            }
        except (XrayAuthError, XrayClientError) as bearer_error:
            logger.debug(f"Bearer auth failed: {bearer_error}, trying Basic auth")
        
        # Fall back to Basic auth
        try:
            result = await self._request("GET", url, headers=self._auth_headers(use_bearer=False))
            self._use_bearer = False
            return {
                "success": True,
                "message": f"Successfully connected to {result.get('serverTitle', 'Jira Server')} (Basic auth)",
                "xray_version": result.get("version", "Unknown"),
            }
        except XrayClientError as e:
            # Provide more helpful error message
            error_msg = str(e)
            if "403" in error_msg or "Forbidden" in error_msg:
                raise XrayAuthError(
                    "Authentication failed with 403 Forbidden. Possible causes: "
                    "1) Invalid username or PAT. "
                    "2) PAT lacks required permissions (needs at least Browse Projects). "
                    "3) CAPTCHA challenge required - please log in via browser first. "
                    "4) IP or user may be blocked. "
                    "5) Basic/Token authentication may be disabled on your Jira server."
                )
            elif "401" in error_msg:
                raise XrayAuthError(
                    "Authentication failed with 401 Unauthorized. "
                    "Please verify your username and PAT are correct."
                )
            raise
    
    async def _ensure_authenticated(self):
        """Ensure we have authenticated and know which auth method to use"""
        if not self._authenticated:
            await self.authenticate()
            self._authenticated = True
    
    async def get_test_sets(self, project_key: str) -> List[Dict[str, Any]]:
        """Get test sets using JQL search"""
        import urllib.parse
        
        await self._ensure_session()
        await self._ensure_authenticated()
        
        # Try different possible issue type names for Test Sets
        # Xray uses "Test Set" but some installations may vary
        issue_type_names = ["Test Set", "Xray Test Set", "Test-Set"]
        
        test_sets = []
        
        for issue_type in issue_type_names:
            jql = f'project = "{project_key}" AND issuetype = "{issue_type}"'
            encoded_jql = urllib.parse.quote(jql, safe='')
            url = f"{self.base_url}/rest/api/2/search?jql={encoded_jql}&maxResults=100&fields=key,summary,description,labels"
            
            logger.info(f"Searching for test sets with JQL: {jql}")
            
            try:
                result = await self._request("GET", url, headers=self._get_auth_headers())
                
                issues = result.get("issues", [])
                logger.info(f"Found {len(issues)} test sets with issuetype='{issue_type}'")
                
                for issue in issues:
                    fields = issue.get("fields", {})
                    test_sets.append({
                        "issue_id": issue.get("id"),
                        "key": issue.get("key"),
                        "summary": fields.get("summary"),
                        "description": fields.get("description"),
                        "labels": fields.get("labels", []),
                    })
                
                if test_sets:
                    break  # Found test sets, no need to try other issue type names
                    
            except XrayClientError as e:
                # JQL might have failed due to invalid issue type, try next
                logger.debug(f"JQL search failed for issuetype='{issue_type}': {e}")
                continue
        
        # If still no results, try to find all Xray-related issue types
        if not test_sets:
            logger.warning(f"No test sets found for project {project_key}. Trying to discover issue types...")
            try:
                # Get all issue types to help debug
                types_url = f"{self.base_url}/rest/api/2/issuetype"
                types_result = await self._request("GET", types_url, headers=self._get_auth_headers())
                
                xray_types = [t.get("name") for t in types_result if isinstance(types_result, list) 
                              and t.get("name") and ("test" in t.get("name", "").lower() or "xray" in t.get("name", "").lower())]
                
                if xray_types:
                    logger.info(f"Available Xray-related issue types: {xray_types}")
                    
                    # Try to search with these types
                    for issue_type in xray_types:
                        if "set" in issue_type.lower():
                            jql = f'project = "{project_key}" AND issuetype = "{issue_type}"'
                            encoded_jql = urllib.parse.quote(jql, safe='')
                            url = f"{self.base_url}/rest/api/2/search?jql={encoded_jql}&maxResults=100&fields=key,summary,description,labels"
                            
                            try:
                                result = await self._request("GET", url, headers=self._get_auth_headers())
                                issues = result.get("issues", [])
                                
                                for issue in issues:
                                    fields = issue.get("fields", {})
                                    test_sets.append({
                                        "issue_id": issue.get("id"),
                                        "key": issue.get("key"),
                                        "summary": fields.get("summary"),
                                        "description": fields.get("description"),
                                        "labels": fields.get("labels", []),
                                    })
                                
                                if test_sets:
                                    break
                            except XrayClientError:
                                continue
            except Exception as e:
                logger.error(f"Failed to discover issue types: {e}")
        
        logger.info(f"Total test sets found: {len(test_sets)}")
        return test_sets
    
    async def _throttle(self):
        """Throttle requests based on configuration"""
        import asyncio
        from app.config import settings
        request_delay = getattr(settings, 'XRAY_REQUEST_DELAY_MS', 500) / 1000
        if request_delay > 0:
            await asyncio.sleep(request_delay)

    async def _get_jira_details_bulk(self, issue_keys: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get Jira issue details for multiple keys in one request"""
        import urllib.parse
        
        if not issue_keys:
            return {}
            
        logger.info(f"Bulk fetching Jira details for {len(issue_keys)} issues")
        
        # JQL has a length limit, so we chunk requests if needed (e.g., 50 keys at a time)
        chunk_size = 50
        results = {}
        
        for i in range(0, len(issue_keys), chunk_size):
            chunk = issue_keys[i:i + chunk_size]
            jql = f"key in ({','.join(chunk)})"
            encoded_jql = urllib.parse.quote(jql, safe='')
            
            # Fetch minimal fields needed
            url = f"{self.base_url}/rest/api/2/search?jql={encoded_jql}&maxResults={chunk_size}&fields=key,summary,description,labels,priority"
            
            await self._throttle()
            
            try:
                response = await self._request("GET", url, headers=self._get_auth_headers())
                issues = response.get("issues", [])
                
                for issue in issues:
                    key = issue.get("key")
                    fields = issue.get("fields", {})
                    results[key] = {
                        "issue_id": issue.get("id"),
                        "key": key,
                        "summary": fields.get("summary"),
                        "description": fields.get("description"),
                        "labels": fields.get("labels", []),
                        "priority": fields.get("priority", {}).get("name") if fields.get("priority") else None,
                    }
            except Exception as e:
                logger.error(f"Failed to bulk fetch Jira details for chunk: {e}")
                
        return results

    async def get_test_set(self, issue_key: str) -> Dict[str, Any]:
        """Get a specific test set"""
        await self._ensure_session()
        await self._ensure_authenticated()
        
        await self._throttle()
        
        # Get issue details
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}"
        result = await self._request("GET", url, headers=self._get_auth_headers())
        
        fields = result.get("fields", {})
        
        # Get tests in test set via Xray API
        await self._throttle()
            
        tests_url = f"{self.base_url}/rest/raven/1.0/api/testset/{issue_key}/test"
        try:
            tests_result = await self._request("GET", tests_url, headers=self._get_auth_headers())
            tests = tests_result if isinstance(tests_result, list) else []
        except XrayNotFoundError:
            tests = []
        
        return {
            "issue_id": result.get("id"),
            "key": result.get("key"),
            "summary": fields.get("summary"),
            "description": fields.get("description"),
            "labels": fields.get("labels", []),
            "components": [c.get("name") for c in fields.get("components", [])],
            "fix_versions": [v.get("name") for v in fields.get("fixVersions", [])],
            "test_count": len(tests),
            "tests": [
                {"issue_id": t.get("id"), "key": t.get("key"), "summary": t.get("summary")}
                for t in tests
            ]
        }
    
    async def get_tests_in_test_set(self, test_set_key: str) -> List[Dict[str, Any]]:
        """Get all tests in a test set with optimized bulk fetching"""
        import asyncio
        
        await self._ensure_session()
        await self._ensure_authenticated()
        
        # 1. Get List of Tests
        await self._throttle()
        url = f"{self.base_url}/rest/raven/1.0/api/testset/{test_set_key}/test"
        tests_list = await self._request("GET", url, headers=self._get_auth_headers())
        
        if not isinstance(tests_list, list):
            tests_list = []
        
        if not tests_list:
            return []
            
        # 2. Bulk Fetch Jira Details (Summary, Description, etc.)
        test_keys = [t.get("key") for t in tests_list if t.get("key")]
        jira_details_map = await self._get_jira_details_bulk(test_keys)
        
        # 3. Fetch Xray Specific Details (Steps/Gherkin) individually but throttled
        tests = []
        
        for idx, test_info in enumerate(tests_list):
            test_key = test_info.get("key")
            if not test_key:
                continue
                
            jira_details = jira_details_map.get(test_key, {})
            
            # Use cached summary if available, otherwise use what we have
            summary = jira_details.get("summary") or test_info.get("summary")
            
            # Fetch Xray specific details (Type, Steps)
            await self._throttle()
            
            test_url = f"{self.base_url}/rest/raven/1.0/api/test/{test_key}"
            try:
                test_result = await self._request("GET", test_url, headers=self._get_auth_headers())
            except XrayNotFoundError:
                test_result = {}
            
            test_type = test_result.get("type", "Manual").lower()
            is_gherkin = test_type in ["cucumber", "gherkin"]
            
            test_data = {
                "issue_id": jira_details.get("issue_id") or test_info.get("id"),
                "key": test_key,
                "summary": summary,
                "description": jira_details.get("description"),
                "labels": jira_details.get("labels", []),
                "priority": jira_details.get("priority"),
                "test_type": "gherkin" if is_gherkin else "manual",
                "preconditions": test_result.get("precondition"),
                "rank": idx
            }
            
            if is_gherkin:
                test_data["gherkin_scenario"] = test_result.get("definition", "")
            else:
                # Get manual steps
                await self._throttle()
                    
                steps_url = f"{self.base_url}/rest/raven/1.0/api/test/{test_key}/step"
                try:
                    steps_result = await self._request("GET", steps_url, headers=self._get_auth_headers())
                    steps = steps_result if isinstance(steps_result, list) else []
                except XrayNotFoundError:
                    steps = []
                
                test_data["manual_steps"] = [
                    {
                        "index": i,
                        "action": step.get("step", ""),
                        "data": step.get("data", ""),
                        "expected": step.get("result", "")
                    }
                    for i, step in enumerate(steps)
                ]
            
            tests.append(test_data)
        
        return tests
    
    async def get_test(self, issue_key: str) -> Dict[str, Any]:
        """Get a specific test"""
        await self._ensure_session()
        await self._ensure_authenticated()
        
        await self._throttle()
        
        # Get issue details
        issue_url = f"{self.base_url}/rest/api/2/issue/{issue_key}"
        issue_result = await self._request("GET", issue_url, headers=self._get_auth_headers())
        
        fields = issue_result.get("fields", {})
        
        # Get test details from Xray API
        await self._throttle()
            
        test_url = f"{self.base_url}/rest/raven/1.0/api/test/{issue_key}"
        try:
            test_result = await self._request("GET", test_url, headers=self._get_auth_headers())
        except XrayNotFoundError:
            test_result = {}
        
        test_type = test_result.get("type", "Manual").lower()
        is_gherkin = test_type in ["cucumber", "gherkin"]
        
        response = {
            "issue_id": issue_result.get("id"),
            "key": issue_result.get("key"),
            "summary": fields.get("summary"),
            "description": fields.get("description"),
            "labels": fields.get("labels", []),
            "priority": fields.get("priority", {}).get("name") if fields.get("priority") else None,
            "test_type": "gherkin" if is_gherkin else "manual",
            "preconditions": test_result.get("precondition"),
        }
        
        if is_gherkin:
            response["gherkin_scenario"] = test_result.get("definition", "")
        else:
            # Get manual steps
            await self._throttle()
                
            steps_url = f"{self.base_url}/rest/raven/1.0/api/test/{issue_key}/step"
            try:
                steps_result = await self._request("GET", steps_url, headers=self._get_auth_headers())
                steps = steps_result if isinstance(steps_result, list) else []
            except XrayNotFoundError:
                steps = []
            
            response["manual_steps"] = [
                {
                    "index": i,
                    "action": step.get("step", ""),
                    "data": step.get("data", ""),
                    "expected": step.get("result", "")
                }
                for i, step in enumerate(steps)
            ]
        
        return response
    
    async def create_test_execution(
        self,
        project_key: str,
        test_results: List[Dict[str, Any]],
        summary: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a test execution with results"""
        await self._ensure_session()
        await self._ensure_authenticated()
        
        # Build the execution payload for Xray Server REST API
        execution_payload = {
            "info": {
                "project": project_key,
                "summary": summary or f"Test Execution - {datetime.now().isoformat()}",
                "description": description or "Automated test execution from Browser Test Platform",
            },
            "tests": []
        }
        
        for result in test_results:
            test_entry = {
                "testKey": result.get("test_key"),
                "status": self._map_status(result.get("status", "PENDING")),
                "comment": result.get("comment", ""),
            }
            
            # Add step results if available
            if result.get("steps"):
                test_entry["steps"] = [
                    {
                        "status": self._map_status(step.get("status", "PENDING")),
                        "actualResult": step.get("actual_result", ""),
                        "comment": step.get("comment", ""),
                    }
                    for step in result["steps"]
                ]
            
            execution_payload["tests"].append(test_entry)
        
        # POST to create execution
        await self._throttle()
        url = f"{self.base_url}/rest/raven/1.0/import/execution"
        response = await self._request("POST", url, headers=self._get_auth_headers(), json=execution_payload)
        
        return {
            "execution_key": response.get("testExecIssue", {}).get("key"),
            "execution_id": response.get("testExecIssue", {}).get("id"),
        }
    
    @staticmethod
    def _map_status(status: str) -> str:
        """Map internal status to Xray status"""
        status_map = {
            "PENDING": "TODO",
            "PASSED": "PASS",
            "FAILED": "FAIL",
            "SKIPPED": "SKIPPED",
            "BLOCKED": "BLOCKED",
        }
        return status_map.get(status.upper(), "TODO")


def get_xray_client(config: XrayConfig) -> BaseXrayClient:
    """Factory function to get the appropriate Xray client"""
    if config.instance_type == XrayInstanceType.CLOUD:
        return XrayCloudClient(config)
    else:
        return XrayServerClient(config)
