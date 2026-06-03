#!/usr/bin/env python3
"""Small helper to retry flaky network-bound CLI steps (Trivy DB, etc.)."""
from __future__ import annotations

import time
from typing import Callable, Optional, TypeVar

T = TypeVar("T")


def run_with_retry(
    fn: Callable[[int], T],
    *,
    max_attempts: int = 3,
    delay_seconds: float = 5.0,
    should_retry: Optional[Callable[[T, int], bool]] = None,
) -> T:
    """
    Call ``fn(attempt)`` until success or attempts exhausted.

    ``should_retry(result, attempt)`` defaults to retry when *result* has
    ``returncode != 0`` (subprocess.CompletedProcess).
    """
    if max_attempts < 1:
        max_attempts = 1

    def _default_retry(result: T, _attempt: int) -> bool:
        code = getattr(result, "returncode", None)
        return code is not None and code != 0

    retry_pred = should_retry or _default_retry
    last: T = fn(1)
    for attempt in range(2, max_attempts + 1):
        if not retry_pred(last, attempt - 1):
            return last
        time.sleep(delay_seconds)
        last = fn(attempt)
    return last
