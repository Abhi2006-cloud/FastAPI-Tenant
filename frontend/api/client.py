"""Base HTTP client for API communication."""

import requests
from typing import Any

from frontend.utils.constants import API_BASE_URL
from frontend.utils.session import get_access_token, get_organization_id


class APIError(Exception):
    """Custom exception for API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class APIClient:
    """Base API client with authentication and organization context."""

    def __init__(self):
        self.base_url = API_BASE_URL.rstrip("/")

    def _get_headers(self, require_auth: bool = True) -> dict[str, str]:
        """Build request headers with auth and organization context."""
        headers = {"Content-Type": "application/json"}
        
        if require_auth:
            token = get_access_token()
            if not token:
                raise APIError("Authentication required. Please login.")
            headers["Authorization"] = f"Bearer {token}"
        
        # Add organization ID if set
        org_id = get_organization_id()
        if org_id:
            headers["X-Organization-Id"] = org_id
        
        return headers

    def _handle_response(self, response: requests.Response) -> Any:
        """Handle API response and errors."""
        if response.status_code == 401:
            raise APIError("Unauthorized. Please login again.", 401)
        elif response.status_code == 403:
            raise APIError("Forbidden. You don't have permission.", 403)
        elif response.status_code == 404:
            raise APIError("Resource not found.", 404)
        elif response.status_code == 409:
            raise APIError("Resource already exists or conflict.", 409)
        elif response.status_code >= 400:
            error_msg = response.text
            try:
                error_data = response.json()
                error_msg = error_data.get("detail", error_msg)
            except ValueError:
                pass
            raise APIError(f"API Error: {error_msg}", response.status_code)
        
        # Return JSON if possible, otherwise text
        try:
            return response.json()
        except ValueError:
            return response.text

    def get(self, endpoint: str, params: dict | None = None, require_auth: bool = True) -> Any:
        """Make a GET request."""
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, headers=self._get_headers(require_auth), params=params)
        return self._handle_response(response)

    def post(self, endpoint: str, data: dict | None = None, files: dict | None = None, 
             require_auth: bool = True) -> Any:
        """Make a POST request."""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers(require_auth)
        
        # Remove Content-Type for file uploads (requests sets it automatically)
        if files:
            headers.pop("Content-Type", None)
        
        response = requests.post(url, headers=headers, json=data, files=files)
        return self._handle_response(response)

    def put(self, endpoint: str, data: dict | None = None, require_auth: bool = True) -> Any:
        """Make a PUT request."""
        url = f"{self.base_url}{endpoint}"
        response = requests.put(url, headers=self._get_headers(require_auth), json=data)
        return self._handle_response(response)

    def delete(self, endpoint: str, require_auth: bool = True) -> Any:
        """Make a DELETE request."""
        url = f"{self.base_url}{endpoint}"
        response = requests.delete(url, headers=self._get_headers(require_auth))
        return self._handle_response(response)


# Global API client instance
api_client = APIClient()
