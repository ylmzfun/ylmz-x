"""Request class wrapping the ASGI scope and messages — optimized."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs


class Request:
    """Represents an incoming HTTP request — headers pre-parsed at init time."""

    __slots__ = (
        "_scope", "_receive", "_body", "_json", "_form",
        "_query_params", "path_params", "method", "path", "headers", "cookies",
    )

    def __init__(self, scope: dict, receive: callable):
        self._scope = scope
        self._receive = receive
        self._body: bytes | None = None
        self._json: Any = ...
        self._form: dict | None = None
        self._query_params: dict | None = None
        self.path_params: dict = {}

        # Pre-parse method and path
        self.method: str = scope.get("method", "")
        self.path: str = scope.get("path", "")

        # Pre-parse headers (avoid per-access decode)
        self.headers: dict[str, str] = {}
        for key, value in scope.get("headers", []):
            self.headers[key.decode("latin-1").lower()] = value.decode("latin-1")

        # Pre-parse cookies
        self.cookies: dict[str, str] = {}
        cookie_header = self.headers.get("cookie", "")
        if cookie_header:
            for item in cookie_header.split(";"):
                item = item.strip()
                if "=" in item:
                    k, v = item.split("=", 1)
                    self.cookies[k.strip()] = v.strip()

    @property
    def query_params(self) -> dict:
        if self._query_params is None:
            qs = self._scope.get("query_string", b"").decode("latin-1")
            parsed = parse_qs(qs, keep_blank_values=True)
            self._query_params = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
        return self._query_params

    def get(self, key: str, default=None) -> Any:
        if key in self.path_params:
            return self.path_params[key]
        if key in self.query_params:
            return self.query_params[key]
        return default

    async def body(self) -> bytes:
        if self._body is not None:
            return self._body
        body = b""
        more_body = True
        while more_body:
            message = await self._receive()
            body += message.get("body", b"")
            more_body = message.get("more_body", False)
        self._body = body
        return self._body

    async def json(self) -> Any:
        if self._json is ...:
            body = await self.body()
            if not body:
                self._json = None
            else:
                self._json = json.loads(body)
        return self._json

    async def form(self) -> dict:
        if self._form is not None:
            return self._form
        body = await self.body()
        parsed = parse_qs(body.decode("latin-1"), keep_blank_values=True)
        self._form = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
        return self._form
