"""Dependency injection system — FastAPI-like Depends() with caching and sub-dependencies."""

from __future__ import annotations

import inspect
import functools
from typing import Any, Callable


class Depends:
    """Declare a dependency for a route handler parameter.

    Usage::

        async def get_db():
            return Database()

        @app.get("/items")
        async def list_items(db = Depends(get_db)):
            return await db.query(...)
    """

    def __init__(self, dependency: Callable, *, use_cache: bool = True):
        self.dependency = dependency
        self.use_cache = use_cache

    def __repr__(self):
        return f"Depends({self.dependency.__name__})"


class _DependencyCache:
    """Per-request cache for resolved dependencies."""

    def __init__(self):
        self._cache: dict[Callable, Any] = {}

    def get(self, dep: Callable) -> Any:
        return self._cache.get(dep, _sentinel)

    def set(self, dep: Callable, value: Any) -> None:
        self._cache[dep] = value


_sentinel = object()


async def _resolve_dependency(
    dependency: Callable,
    cache: _DependencyCache,
    *,
    use_cache: bool,
) -> Any:
    """Resolve a single dependency, with caching."""
    if use_cache:
        cached = cache.get(dependency)
        if cached is not _sentinel:
            return cached

    # Resolve sub-dependencies recursively
    kwargs = await _resolve_signature(dependency, cache)

    if inspect.iscoroutinefunction(dependency):
        result = await dependency(**kwargs)
    else:
        result = dependency(**kwargs)

    if use_cache:
        cache.set(dependency, result)
    return result


async def _resolve_signature(
    func: Callable,
    cache: _DependencyCache,
) -> dict:
    """Inspect a function's signature and resolve all Depends() parameters."""
    sig = inspect.signature(func)
    kwargs = {}

    for name, param in sig.parameters.items():
        default = param.default
        if isinstance(default, Depends):
            kwargs[name] = await _resolve_dependency(
                default.dependency,
                cache,
                use_cache=default.use_cache,
            )
        elif default is not inspect.Parameter.empty and not isinstance(default, Depends):
            kwargs[name] = default

    return kwargs
