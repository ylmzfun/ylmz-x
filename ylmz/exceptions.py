"""HTTP exceptions for the ylmz framework."""

from __future__ import annotations


class HTTPException(Exception):
    """An HTTP exception that can be raised in route handlers."""

    def __init__(self, status_code: int, detail: str = "", headers: dict = None):
        self.status_code = status_code
        self.detail = detail
        self.headers = headers or {}

    def __repr__(self):
        return f"HTTPException(status_code={self.status_code}, detail={self.detail!r})"
