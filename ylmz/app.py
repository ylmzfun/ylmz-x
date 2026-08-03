"""Core Ylmz application — the ASGI entry point."""

from __future__ import annotations

import inspect as _inspect
from typing import Callable

from ylmz.request import Request
from ylmz.response import Response, JSONResponse
from ylmz.exceptions import HTTPException
from ylmz.routing import Router, _build_kwargs, Route
from ylmz.middleware import build_middleware_stack
from ylmz.background import BackgroundTasks
from ylmz.depends import _DependencyCache


class Ylmz:
    """The main application class."""

    def __init__(self, title: str = "ylmz", debug: bool = False):
        self.title = title
        self.debug = debug
        self.router = Router()
        self._middlewares: list[type] = []
        self._startup_handlers: list[Callable] = []
        self._shutdown_handlers: list[Callable] = []
        self._exception_handlers: dict[type, Callable] = {}
        self.state: dict = {}

    def add_middleware(self, middleware_cls: type) -> None:
        self._middlewares.append(middleware_cls)

    # -- Lifespan --

    def on_startup(self, func: Callable) -> Callable:
        self._startup_handlers.append(func)
        return func

    def on_shutdown(self, func: Callable) -> Callable:
        self._shutdown_handlers.append(func)
        return func

    def on_event(self, event_type: str):
        def decorator(func: Callable) -> Callable:
            if event_type == "startup":
                self._startup_handlers.append(func)
            elif event_type == "shutdown":
                self._shutdown_handlers.append(func)
            else:
                raise ValueError(f"Unknown event type: {event_type}")
            return func
        return decorator

    # -- Exception handlers --

    def add_exception_handler(self, exc_class: type, handler: Callable) -> None:
        self._exception_handlers[exc_class] = handler

    def exception_handler(self, exc_class: type) -> Callable:
        def decorator(handler: Callable) -> Callable:
            self.add_exception_handler(exc_class, handler)
            return handler
        return decorator

    # -- Route registration (wires route ref for signature caching) --

    def _wrap_route(self, decorator_factory):
        """Wrap a router decorator to attach route reference to endpoint."""
        def wrapper(path: str):
            decorator = decorator_factory(path)
            def _decorator(endpoint: Callable) -> Callable:
                # Register the route and capture the Route object
                for route in self.router._routes:
                    if route.endpoint is endpoint:
                        endpoint.__ylmz_route__ = route
                        break
                return decorator(endpoint)
            return _decorator
        return wrapper

    def route(self, path: str, methods: set[str]):
        return self.router.route(path, methods)

    def get(self, path: str):
        decorator = self.router.get(path)
        def _wrap(endpoint):
            result = decorator(endpoint)
            for route in self.router.routes:
                if route.endpoint is endpoint:
                    endpoint.__ylmz_route__ = route
                    break
            return result
        return _wrap

    def post(self, path: str):
        decorator = self.router.post(path)
        def _wrap(endpoint):
            result = decorator(endpoint)
            for route in self.router.routes:
                if route.endpoint is endpoint:
                    endpoint.__ylmz_route__ = route
                    break
            return result
        return _wrap

    def put(self, path: str):
        decorator = self.router.put(path)
        def _wrap(endpoint):
            result = decorator(endpoint)
            for route in self.router.routes:
                if route.endpoint is endpoint:
                    endpoint.__ylmz_route__ = route
                    break
            return result
        return _wrap

    def delete(self, path: str):
        decorator = self.router.delete(path)
        def _wrap(endpoint):
            result = decorator(endpoint)
            for route in self.router.routes:
                if route.endpoint is endpoint:
                    endpoint.__ylmz_route__ = route
                    break
            return result
        return _wrap

    def patch(self, path: str):
        decorator = self.router.patch(path)
        def _wrap(endpoint):
            result = decorator(endpoint)
            for route in self.router.routes:
                if route.endpoint is endpoint:
                    endpoint.__ylmz_route__ = route
                    break
            return result
        return _wrap

    def websocket(self, path: str):
        decorator = self.router.websocket(path)
        def _wrap(endpoint):
            result = decorator(endpoint)
            for route in self.router.routes:
                if route.endpoint is endpoint:
                    endpoint.__ylmz_route__ = route
                    break
            return result
        return _wrap

    def include_router(self, router: Router) -> None:
        self.router.include_router(router)

    # -- Backward compat --

    def _build_response(self, raw) -> Response:
        """Convert a handler return value into a Response."""
        return _to_response(raw)

    # -- ASGI interface --

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "lifespan":
            await self._handle_lifespan(scope, receive, send)
            return

        if scope["type"] == "websocket":
            await self._handle_websocket(scope, receive, send)
            return

        if scope["type"] != "http":
            return

        request = Request(scope, receive)
        background = BackgroundTasks()
        dep_cache = _DependencyCache()

        try:
            endpoint, path_params = self.router.match(request.method, request.path)
            if endpoint is None:
                if request.method == "HEAD":
                    endpoint, path_params = self.router.match("GET", request.path)
                if endpoint is None:
                    raise HTTPException(404, "Not Found")

            request.path_params = path_params

            kwargs, errors = await _build_kwargs(
                endpoint, request, path_params, dep_cache, background
            )
            if errors:
                raise HTTPException(422, detail={"errors": errors})

            raw = endpoint(**kwargs)
            if raw is not None and hasattr(raw, "__await__"):
                raw = await raw

            response = _to_response(raw)
            await response(send)

            await background.run()

        except HTTPException as exc:
            await self._handle_exception(exc, send)
        except Exception as exc:
            handled = await self._try_handle_custom_exception(exc, send, request)
            if not handled:
                if self.debug:
                    raise
                await self._handle_exception(
                    HTTPException(500, detail=str(exc) if self.debug else "Internal Server Error"),
                    send,
                )

    # -- Lifespan --

    async def _handle_lifespan(self, scope, receive, send) -> None:
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                for handler in self._startup_handlers:
                    if _inspect.iscoroutinefunction(handler):
                        await handler()
                    else:
                        handler()
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                for handler in self._shutdown_handlers:
                    if _inspect.iscoroutinefunction(handler):
                        await handler()
                    else:
                        handler()
                await send({"type": "lifespan.shutdown.complete"})
                return

    # -- WebSocket --

    async def _handle_websocket(self, scope, receive, send) -> None:
        endpoint, path_params = self.router.match("WEBSOCKET", scope["path"])
        if endpoint is None:
            await send({"type": "websocket.close", "code": 404})
            return
        from ylmz.websocket import WebSocket
        ws = WebSocket(scope, receive, send)
        ws.path_params = path_params
        await endpoint(ws)

    # -- Exception handling --

    async def _handle_exception(self, exc: HTTPException, send) -> None:
        body = {"detail": exc.detail}
        response = JSONResponse(body, status_code=exc.status_code, headers=exc.headers)
        await response(send)

    async def _try_handle_custom_exception(
        self, exc: Exception, send, request: Request
    ) -> bool:
        for exc_class in self._exception_handlers:
            if isinstance(exc, exc_class):
                handler = self._exception_handlers[exc_class]
                result = handler(request, exc)
                if hasattr(result, "__await__"):
                    result = await result
                resp = _to_response(result)
                await resp(send)
                return True
        return False


# ── Module-level fast response builder (avoids method lookup) ──

def _to_response(raw) -> Response:
    """Convert a handler return value into a Response — fast path."""
    if isinstance(raw, Response):
        return raw
    if isinstance(raw, dict):
        return JSONResponse(raw)
    if isinstance(raw, (list, tuple)):
        return JSONResponse(raw)
    return JSONResponse(raw)
