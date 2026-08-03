"""WebSocket support for the ylmz framework."""

from __future__ import annotations

from typing import Any


class WebSocket:
    """Represents a WebSocket connection."""

    def __init__(self, scope: dict, receive: callable, send: callable):
        self._scope = scope
        self._receive = receive
        self._send = send
        self.path_params: dict = {}
        self._accepted = False

    @property
    def headers(self) -> dict:
        """Request headers."""
        result = {}
        for k, v in self._scope.get("headers", []):
            result[k.decode("latin-1").lower()] = v.decode("latin-1")
        return result

    @property
    def path(self) -> str:
        return self._scope.get("path", "")

    @property
    def client(self) -> tuple:
        """Client address as (host, port)."""
        return self._scope.get("client", ("", 0))

    async def accept(self) -> None:
        """Accept the WebSocket connection."""
        await self._send({"type": "websocket.accept"})
        self._accepted = True

    async def receive(self) -> dict:
        """Receive a WebSocket message.

        Returns a dict with keys: 'type' ('websocket.receive' or 'websocket.disconnect'),
        'text' or 'bytes' for text/binary messages, and 'code' on disconnect.
        """
        message = await self._receive()
        return message

    async def send_text(self, data: str) -> None:
        """Send a text message."""
        await self._send({"type": "websocket.send", "text": data})

    async def send_bytes(self, data: bytes) -> None:
        """Send a binary message."""
        await self._send({"type": "websocket.send", "bytes": data})

    async def send_json(self, data: Any) -> None:
        """Send a JSON-serialized message."""
        import json

        await self.send_text(json.dumps(data, ensure_ascii=False, default=str))

    async def close(self, code: int = 1000) -> None:
        """Close the WebSocket connection."""
        await self._send({"type": "websocket.close", "code": code})


class WebSocketDisconnect(Exception):
    """Raised when the WebSocket client disconnects."""
    def __init__(self, code: int = 1000):
        self.code = code
        super().__init__(f"WebSocket disconnected with code {code}")
