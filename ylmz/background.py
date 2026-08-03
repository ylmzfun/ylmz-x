"""Background tasks — run async tasks after the response is sent."""

from __future__ import annotations

import asyncio
from typing import Callable, Awaitable


class BackgroundTasks:
    """Collect background tasks to be executed after the response is sent.

    Usage::

        @app.post("/send-email")
        async def send_email(background_tasks: BackgroundTasks):
            background_tasks.add_task(send_email_async, to="user@example.com")
            return {"message": "Email queued"}
    """

    def __init__(self):
        self._tasks: list[tuple[Callable, tuple, dict]] = []

    def add_task(self, func: Callable[..., Awaitable], *args, **kwargs) -> None:
        """Add a background task to be executed after the response."""
        self._tasks.append((func, args, kwargs))

    async def run(self) -> None:
        """Run all collected tasks concurrently."""
        if not self._tasks:
            return
        coros = [
            _run_task(func, args, kwargs)
            for func, args, kwargs in self._tasks
        ]
        await asyncio.gather(*coros, return_exceptions=True)


async def _run_task(func: Callable, args: tuple, kwargs: dict) -> None:
    """Run a single task, catching exceptions."""
    try:
        if asyncio.iscoroutinefunction(func):
            await func(*args, **kwargs)
        else:
            # Run sync functions in a thread to avoid blocking
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: func(*args, **kwargs))
    except Exception:
        pass  # Background tasks should not crash the app
