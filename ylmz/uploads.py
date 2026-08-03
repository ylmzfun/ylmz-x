"""File upload support."""

from __future__ import annotations

import os
import tempfile
from typing import BinaryIO


class UploadFile:
    """Represents an uploaded file.

    Usage::

        @app.post("/upload")
        async def upload(file: UploadFile):
            content = await file.read()
            await file.save("/path/to/destination")
            return {"filename": file.filename, "size": file.size}
    """

    def __init__(self, filename: str, content: bytes = None, content_type: str = ""):
        self.filename = filename
        self.content_type = content_type
        self._content = content
        self._file: BinaryIO | None = None
        self._size: int | None = None

    @property
    def size(self) -> int:
        """File size in bytes."""
        if self._size is not None:
            return self._size
        if self._content is not None:
            self._size = len(self._content)
        return self._size or 0

    @classmethod
    async def from_multipart(cls, headers: dict, body: bytes) -> "UploadFile":
        """Parse an UploadFile from multipart form headers and body."""
        content_disposition = headers.get("content-disposition", "")
        filename = "unknown"
        if "filename=" in content_disposition:
            # Extract filename from content-disposition header
            for part in content_disposition.split(";"):
                part = part.strip()
                if part.startswith("filename="):
                    filename = part.split("=", 1)[1].strip('"').strip("'")

        content_type = headers.get("content-type", "application/octet-stream")
        return cls(filename=filename, content=body, content_type=content_type)

    async def read(self) -> bytes:
        """Read the full file content."""
        if self._content is not None:
            return self._content
        if self._file is not None:
            self._file.seek(0)
            return self._file.read()
        return b""

    async def save(self, destination: str) -> None:
        """Save the uploaded file to disk."""
        content = await self.read()
        os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)
        with open(destination, "wb") as f:
            f.write(content)

    async def close(self) -> None:
        """Close any open file handles."""
        if self._file is not None:
            self._file.close()
            self._file = None
