"""Response classes for the ylmz framework — optimized."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator


class Response:
    """Base HTTP response."""

    __slots__ = ("status_code", "headers", "body")
    media_type = "text/plain"
    charset = "utf-8"

    def __init__(
        self,
        content: Any = "",
        status_code: int = 200,
        headers: dict = None,
        media_type: str = None,
    ):
        self.status_code = status_code
        ct = f"{media_type or self.media_type}; charset={self.charset}"
        if headers:
            self.headers = {k.lower(): v for k, v in headers.items()}
            self.headers["content-type"] = ct
        else:
            self.headers = {"content-type": ct}
        self.body = self.render(content)

    def render(self, content: Any) -> bytes:
        if isinstance(content, bytes):
            return content
        return str(content).encode(self.charset)

    async def __call__(self, send) -> None:
        await send({
            "type": "http.response.start",
            "status": self.status_code,
            "headers": [(k.encode(), v.encode()) for k, v in self.headers.items()],
        })
        await send({"type": "http.response.body", "body": self.body})


class JSONResponse(Response):
    """JSON response with fast serialization."""

    __slots__ = ()
    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        return _json_dumps(content, ensure_ascii=False, default=_json_default).encode(self.charset)


class PlainTextResponse(Response):
    __slots__ = ()
    media_type = "text/plain"


class HTMLResponse(Response):
    __slots__ = ()
    media_type = "text/html"


class StreamingResponse(Response):
    """Streaming response for large payloads."""

    __slots__ = ("_iterator",)

    def __init__(
        self,
        content: AsyncIterator[bytes | str],
        status_code: int = 200,
        headers: dict = None,
        media_type: str = "text/plain",
    ):
        self.status_code = status_code
        ct = f"{media_type}; charset=utf-8"
        if headers:
            self.headers = {k.lower(): v for k, v in headers.items()}
            self.headers["content-type"] = ct
        else:
            self.headers = {"content-type": ct}
        self._iterator = content

    async def __call__(self, send) -> None:
        await send({
            "type": "http.response.start",
            "status": self.status_code,
            "headers": [(k.encode(), v.encode()) for k, v in self.headers.items()],
        })
        async for chunk in self._iterator:
            if isinstance(chunk, str):
                chunk = chunk.encode("utf-8")
            await send({"type": "http.response.body", "body": chunk, "more_body": True})
        await send({"type": "http.response.body", "body": b"", "more_body": False})


# ── Module-level JSON serializer (avoids repeated kwargs) ──

_json_dumps = json.dumps
_json_default = str
