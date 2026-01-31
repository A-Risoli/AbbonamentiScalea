"""Rate limiter for bot queries using sliding window algorithm."""

import time
from collections import defaultdict, deque
from typing import Deque, Dict


class RateLimiter:
    """Rate limiter using sliding window with per-user tracking."""

    def __init__(self, max_requests: int = 20, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed per window (default: 20)
            window_seconds: Time window in seconds (default: 60)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.user_requests: Dict[int, Deque[float]] = defaultdict(deque)

    def is_allowed(self, user_id: int) -> bool:
        """
        Check if user is allowed to make a request.

        Args:
            user_id: Telegram user ID

        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        now = time.time()
        user_queue = self.user_requests[user_id]

        # Remove timestamps outside the current window
        while user_queue and user_queue[0] < now - self.window_seconds:
            user_queue.popleft()

        # Check if limit exceeded
        if len(user_queue) >= self.max_requests:
            return False

        # Add current request timestamp
        user_queue.append(now)
        return True

    def get_wait_time(self, user_id: int) -> int:
        """
        Get seconds to wait before next request is allowed.

        Args:
            user_id: Telegram user ID

        Returns:
            Seconds to wait (0 if request is currently allowed)
        """
        now = time.time()
        user_queue = self.user_requests[user_id]

        # Remove expired timestamps
        while user_queue and user_queue[0] < now - self.window_seconds:
            user_queue.popleft()

        if len(user_queue) < self.max_requests:
            return 0

        # Time until oldest request expires
        oldest_request = user_queue[0]
        wait_time = int((oldest_request + self.window_seconds) - now) + 1
        return max(0, wait_time)
