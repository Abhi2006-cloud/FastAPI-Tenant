import logging
import time
from typing import Any, Dict, Optional
import httpx
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class MeilisearchException(Exception):
    """Base exception for Meilisearch errors."""
    pass

class MeilisearchUnavailableException(MeilisearchException):
    """Raised when Meilisearch is offline or circuit breaker is open."""
    pass

class MeilisearchApiError(MeilisearchException):
    """Raised when Meilisearch returns a error status code."""
    def __init__(self, message: str, status_code: int, details: Optional[Any] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details

class CircuitBreaker:
    """Lightweight in-memory Circuit Breaker to prevent excessive failed calls."""
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.failure_count = 0
        self.last_state_change = time.time()

    def record_success(self):
        if self.state != "CLOSED":
            logger.info("Circuit Breaker CLOSED")
            self.state = "CLOSED"
        self.failure_count = 0

    def record_failure(self):
        self.failure_count += 1
        if self.state == "CLOSED" and self.failure_count >= self.failure_threshold:
            logger.warning("Circuit Breaker OPENED - too many consecutive failures")
            self.state = "OPEN"
            self.last_state_change = time.time()
        elif self.state == "HALF_OPEN":
            logger.warning("Circuit Breaker OPENED - failed during HALF_OPEN trial request")
            self.state = "OPEN"
            self.last_state_change = time.time()

    def allow_request(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if time.time() - self.last_state_change > self.recovery_timeout:
                logger.info("Circuit Breaker entering HALF_OPEN state for trial request")
                self.state = "HALF_OPEN"
                self.last_state_change = time.time()
                return True
            return False
        if self.state == "HALF_OPEN":
            return True
        return True

class SearchClient:
    """HTTP client communicating with Meilisearch Cloud API."""
    def __init__(self):
        self.circuit_breaker = CircuitBreaker()
        self.enabled = False
        self._async_client: Optional[httpx.AsyncClient] = None

    def is_configured(self) -> bool:
        settings = get_settings()
        if not settings.is_search_enabled:
            return False
        url = settings.meilisearch_url
        key = settings.meilisearch_api_key
        if not url or not key:
            return False
        if url.startswith("<") or key.startswith("<"):
            return False
        return True

    def get_client(self) -> httpx.AsyncClient:
        if self._async_client is None:
            settings = get_settings()
            url = settings.meilisearch_url or ""
            key = settings.meilisearch_api_key or ""
            self._async_client = httpx.AsyncClient(
                base_url=url,
                headers={"Authorization": f"Bearer {key}"} if key else {},
                timeout=2.0
            )
        return self._async_client

    async def initialize(self) -> bool:
        """Startup check to test connection and enable/disable search."""
        if not self.is_configured():
            logger.warning("Meilisearch not configured or contains placeholders. Search module disabled.")
            self.enabled = False
            return False
        
        try:
            logger.info("Connecting to Meilisearch at: %s", get_settings().meilisearch_url)
            # Try to hit health endpoint directly
            client = self.get_client()
            response = await client.get("/health")
            if response.status_code == 200:
                logger.info("Meilisearch connection established successfully.")
                self.enabled = True
                self.circuit_breaker.record_success()
                return True
            else:
                logger.warning("Meilisearch health returned status %s. Search disabled.", response.status_code)
                self.enabled = False
                return False
        except Exception as e:
            logger.warning("Failed to connect to Meilisearch during startup: %s. Search disabled.", str(e))
            self.enabled = False
            return False

    async def health_status(self) -> str:
        """Returns 'connected', 'disabled', or 'unavailable' for health check metrics."""
        settings = get_settings()
        if not settings.is_search_enabled:
            return "disabled"
        if not self.enabled or not self.is_configured():
            return "unavailable"
        
        if not self.circuit_breaker.allow_request():
            return "unavailable"

        try:
            client = self.get_client()
            response = await client.get("/health")
            if response.status_code == 200:
                self.circuit_breaker.record_success()
                return "connected"
            else:
                self.circuit_breaker.record_failure()
                return "unavailable"
        except Exception:
            self.circuit_breaker.record_failure()
            return "unavailable"

    async def request(self, method: str, path: str, **kwargs) -> Any:
        """Wrap all requests with the Circuit Breaker and check initialization state."""
        if not self.is_configured():
            raise MeilisearchUnavailableException("Search service is disabled or not configured.")

        if not self.enabled:
            await self.initialize()
            if not self.enabled:
                raise MeilisearchUnavailableException("Search service is disabled or unavailable.")

        if not self.circuit_breaker.allow_request():

            raise MeilisearchUnavailableException("Search service is temporarily unavailable (circuit breaker open).")

        try:
            client = self.get_client()
            response = await client.request(method, path, **kwargs)
            
            # Treat 5xx or specific server issues as breaker failures
            if response.status_code >= 500:
                self.circuit_breaker.record_failure()
                raise MeilisearchApiError(
                    f"Meilisearch server error: {response.text}", 
                    response.status_code
                )
                
            if response.status_code >= 400:
                # 4xx are client errors, do not open circuit breaker for 4xx, just raise exception
                try:
                    error_data = response.json()
                    message = error_data.get("message", response.text)
                except Exception:
                    message = response.text
                raise MeilisearchApiError(message, response.status_code, details=response.text)

            self.circuit_breaker.record_success()
            try:
                return response.json()
            except ValueError:
                return response.text

        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout) as e:
            logger.error("Connection error to Meilisearch: %s", str(e))
            self.circuit_breaker.record_failure()
            raise MeilisearchUnavailableException(f"Connection failed: {str(e)}") from e
        except MeilisearchException:
            raise
        except Exception as e:
            logger.error("Unexpected error contacting Meilisearch: %s", str(e))
            self.circuit_breaker.record_failure()
            raise MeilisearchUnavailableException(f"Unexpected request error: {str(e)}") from e

    async def close(self):
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None

# Global search client instance
search_client = SearchClient()
