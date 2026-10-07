"""Small read-only client for the X API v2 (user lookup and user timeline)."""

import time

import requests

API_BASE = "https://api.x.com/2"
DEFAULT_WAIT = 60       # seconds to wait after HTTP 429 if X gives no reset time
MAX_WAIT = 900          # never wait longer than 15 minutes because of one 429


class XApiError(Exception):
    pass


class RateLimited(XApiError):
    def __init__(self, message: str, retry_after: float):
        super().__init__(message)
        self.retry_after = retry_after


def retry_after_seconds(headers, now: float) -> float:
    """Seconds until the rate limit window resets (x-rate-limit-reset is a Unix time)."""
    reset = headers.get("x-rate-limit-reset", "")
    if str(reset).isdigit():
        return min(max(int(reset) - now, 0) + 1, MAX_WAIT)
    return DEFAULT_WAIT


class XClient:
    def __init__(self, bearer_token: str, timeout: float = 10, session=None, now=time.time):
        self.headers = {"Authorization": f"Bearer {bearer_token}"}
        self.timeout = timeout
        self.session = session or requests
        self.now = now

    def _get(self, path: str, params: dict | None = None) -> dict:
        response = self.session.get(f"{API_BASE}{path}", headers=self.headers, params=params, timeout=self.timeout)
        if response.status_code == 429:
            wait = retry_after_seconds(response.headers, self.now())
            raise RateLimited(f"X API rate limit hit on {path}", wait)
        if response.status_code in (401, 403):
            raise XApiError(f"X API refused the request (HTTP {response.status_code}). Check X_BEARER_TOKEN and your API access level.")
        response.raise_for_status()
        return response.json()

    def get_user_id(self, username: str) -> str:
        data = self._get(f"/users/by/username/{username}")
        if "data" not in data:
            raise XApiError(f"X user not found: @{username}")
        return data["data"]["id"]

    def get_recent_tweets(self, user_id: str, max_results: int = 5, since_id: str | None = None,
                          exclude: list | None = None) -> list:
        params = {"max_results": max(5, min(max_results, 100)), "tweet.fields": "created_at"}
        if since_id:
            params["since_id"] = since_id
        if exclude:
            params["exclude"] = ",".join(exclude)
        return self._get(f"/users/{user_id}/tweets", params).get("data", [])
