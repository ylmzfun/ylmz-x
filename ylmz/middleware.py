"""Middleware support for the ylmz framework."""

from __future__ import annotations

from ylmz.request import Request
from ylmz.response import Response


class BaseMiddleware:
    """Base class for ASGI middleware."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        await self.app(scope, receive, send)


def build_middleware_stack(app, middlewares: list[type]) -> callable:
    """Wrap the app with a chain of middleware."""
    for middleware_cls in reversed(middlewares):
        app = middleware_cls(app)
    return app


def cors_middleware_factory(
    allow_origins: list[str] = None,
    allow_methods: list[str] = None,
    allow_headers: list[str] = None,
) -> type:
    """Factory that creates a CORS middleware class."""

    class CORSMiddleware(BaseMiddleware):
        async def __call__(self, scope, receive, send):
            if scope["type"] != "http":
                await self.app(scope, receive, send)
                return

            origin = None
            for k, v in scope.get("headers", []):
                if k == b"origin":
                    origin = v.decode()
                    break

            method = scope.get("method", "")

            # Preflight
            if method == "OPTIONS" and origin:
                await send({
                    "type": "http.response.start",
                    "status": 204,
                    "headers": [
                        (b"access-control-allow-origin", origin.encode()),
                        (b"access-control-allow-methods", ", ".join(allow_methods or ["*"]).encode()),
                        (b"access-control-allow-headers", ", ".join(allow_headers or ["*"]).encode()),
                        (b"access-control-max-age", b"86400"),
                    ],
                })
                await send({"type": "http.response.body", "body": b""})
                return

            async def cors_send(message):
                if message["type"] == "http.response.start":
                    headers = message.get("headers", [])
                    if origin and (
                        not allow_origins
                        or "*" in allow_origins
                        or origin in allow_origins
                    ):
                        headers.append(
                            (b"access-control-allow-origin", origin.encode())
                        )
                    message["headers"] = headers
                await send(message)

            await self.app(scope, receive, cors_send)

    return CORSMiddleware
