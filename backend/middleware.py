"""
DermaSense Security & Rate Limiting Middleware.
Provides in-memory sliding window rate limiting per IP address.
"""

import time
import threading
from typing import Dict, List
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.config import RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SECS


class RateLimiter:
    def __init__(self, max_requests: int = RATE_LIMIT_REQUESTS, window_seconds: int = RATE_LIMIT_WINDOW_SECS):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.ip_records: Dict[str, List[float]] = {}
        self.lock = threading.Lock()

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        window_start = now - self.window_seconds

        with self.lock:
            if client_ip not in self.ip_records:
                self.ip_records[client_ip] = [now]
                return True

            # Filter timestamps outside the sliding window
            timestamps = [ts for ts in self.ip_records[client_ip] if ts > window_start]
            if len(timestamps) >= self.max_requests:
                self.ip_records[client_ip] = timestamps
                return False

            timestamps.append(now)
            self.ip_records[client_ip] = timestamps
            return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, rate_limiter: RateLimiter = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimiter()

    async def dispatch(self, request: Request, call_next):
        # Allow health checks without rate limiting
        if request.url.path in ("/api/health", "/docs", "/openapi.json"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "127.0.0.1"
        if not self.rate_limiter.is_allowed(client_ip):
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Rate limit exceeded: maximum {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW_SECS} seconds."
                },
                headers={"Retry-After": str(RATE_LIMIT_WINDOW_SECS)}
            )

        return await call_next(request)

