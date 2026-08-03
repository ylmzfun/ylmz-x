"""Routing system — trie-based path matching with pre-compiled signatures."""

from __future__ import annotations

import re
import inspect
from typing import Any, Callable, get_type_hints

from ylmz.request import Request
from ylmz.response import JSONResponse
from ylmz.exceptions import HTTPException
from ylmz.types import BaseModel
from ylmz.depends import Depends, _DependencyCache, _resolve_dependency
from ylmz.background import BackgroundTasks
from ylmz.params import Param, Path, Query, Body, Header, Cookie

# Sentinel for "parameter not resolved yet"
_UNSET = object()


class Route:
    """A single route binding a path pattern, method, and handler."""

    def __init__(self, path: str, endpoint: Callable, methods: set[str]):
        self.endpoint = endpoint
        self.methods = methods
        self._segments = self._split_path(path)
        self._signature: list[_ParamSpec] | None = None
        # Keep regex matching for backward compat and direct Route usage
        self._pattern, self._param_names = self._compile_path(path)

    @staticmethod
    def _split_path(path_template: str) -> list[tuple[str, str | None]]:
        segments = []
        for segment in path_template.strip("/").split("/"):
            if not segment:
                continue
            if segment.startswith("{") and segment.endswith("}"):
                raw = segment[1:-1]
                name = raw.split(":")[0]
                segments.append(("{[^/]+}", name))
            else:
                segments.append((segment, None))
        return segments

    @staticmethod
    def _compile_path(path_template: str) -> tuple:
        """Compile a path template into a regex pattern (for direct Route.match)."""
        param_names = []
        pattern = "^"
        for segment in path_template.strip("/").split("/"):
            pattern += "/"
            if segment.startswith("{") and segment.endswith("}"):
                raw = segment[1:-1]
                name = raw.split(":")[0]
                param_names.append(name)
                pattern += r"([^/]+)"
            else:
                pattern += re.escape(segment)
        if not pattern[1:]:
            pattern += "/"
        pattern += "/?$"
        return re.compile(pattern), param_names

    def match(self, method: str, path: str) -> dict | None:
        """Direct route matching using regex. Used for direct Route usage."""
        if method not in self.methods:
            return None
        normalized = path.rstrip("/") or "/"
        m = self._pattern.match(normalized)
        if m is None:
            return None
        return dict(zip(self._param_names, m.groups()))

    def __repr__(self):
        return f"<Route methods={self.methods} endpoint={self.endpoint.__name__}>"


# ── Pre-compiled parameter specification ─────────────────────

class _ParamSpec:
    """Pre-compiled single-parameter binding info — computed once at registration."""
    __slots__ = (
        "name", "kind", "annotation", "default_val", "default_is_set",
        "descriptor", "depends_dep", "depends_cache",
    )

    def __init__(self):
        self.name = ""
        self.kind = ""  # "request" | "background" | "depends" | "path" | "query" | "body" | "header" | "cookie" | "default"
        self.annotation = None
        self.default_val = _UNSET
        self.default_is_set = False
        self.descriptor = None  # Param instance or None
        self.depends_dep = None  # Callable for Depends
        self.depends_cache = True


# ── Trie-based Router ────────────────────────────────────────

class _TrieNode:
    """A node in the route trie."""

    __slots__ = ("static", "dynamic_name", "dynamic_node", "methods")

    def __init__(self):
        self.static: dict[str, _TrieNode] = {}
        self.dynamic_name: str | None = None
        self.dynamic_node: _TrieNode | None = None
        self.methods: dict[str, Route] = {}


class Router:
    """A group of routes that can be nested. Uses a trie for O(segments) matching."""

    def __init__(self, prefix: str = ""):
        self.prefix = prefix.rstrip("/")
        self._root = _TrieNode()
        self.routes: list[Route] = []  # Public for OpenAPI iteration

    def add_route(self, path: str, endpoint: Callable, methods: set[str]) -> None:
        """Register a new route."""
        full_path = self.prefix + path
        route = Route(full_path, endpoint, methods)
        self.routes.append(route)
        self._insert(route)

    def _insert(self, route: Route) -> None:
        """Insert a route into the trie."""
        node = self._root
        for seg_pattern, param_name in route._segments:
            if param_name is not None:
                # Dynamic segment
                if node.dynamic_node is None:
                    node.dynamic_name = param_name
                    node.dynamic_node = _TrieNode()
                node = node.dynamic_node
            else:
                # Static segment
                if seg_pattern not in node.static:
                    node.static[seg_pattern] = _TrieNode()
                node = node.static[seg_pattern]
        # Register methods
        for method in route.methods:
            node.methods[method] = route

    def route(self, path: str, methods: set[str]) -> Callable:
        """Decorator to register a route."""
        def decorator(endpoint: Callable) -> Callable:
            self.add_route(path, endpoint, methods)
            return endpoint
        return decorator

    def get(self, path: str) -> Callable:
        return self.route(path, {"GET"})

    def post(self, path: str) -> Callable:
        return self.route(path, {"POST"})

    def put(self, path: str) -> Callable:
        return self.route(path, {"PUT"})

    def delete(self, path: str) -> Callable:
        return self.route(path, {"DELETE"})

    def patch(self, path: str) -> Callable:
        return self.route(path, {"PATCH"})

    def websocket(self, path: str) -> Callable:
        return self.route(path, {"WEBSOCKET"})

    def include_router(self, router: "Router") -> None:
        """Mount another router. Routes are merged into this router's trie."""
        for route in router.routes:
            self.routes.append(route)
            self._insert(route)

    def match(self, method: str, path: str) -> tuple[Callable | None, dict]:
        """Find a matching route using trie traversal. O(segments)."""
        normalized = path.rstrip("/") or "/"
        segments = normalized.strip("/").split("/")
        if segments == [""]:
            segments = []

        params = {}
        node = self._root

        for seg in segments:
            # Try static match first (fast path)
            if seg in node.static:
                node = node.static[seg]
            elif node.dynamic_node is not None:
                params[node.dynamic_name] = seg
                node = node.dynamic_node
            else:
                return None, {}

        # Check method
        route = node.methods.get(method)
        if route is None:
            return None, {}
        return route.endpoint, params


# ── Signature pre-compilation ────────────────────────────────

def _compile_signature(endpoint: Callable) -> list[_ParamSpec]:
    """Pre-compile an endpoint's signature into a list of _ParamSpec.

    This is called once per endpoint (cached on Route._signature), not per request.
    """
    try:
        sig = inspect.signature(endpoint)
    except (ValueError, TypeError):
        return []
    try:
        type_hints = get_type_hints(endpoint)
    except Exception:
        type_hints = {}

    specs = []
    for name, param in sig.parameters.items():
        annotation = type_hints.get(name, param.annotation)
        if annotation is inspect.Parameter.empty:
            annotation = None
        default = param.default

        spec = _ParamSpec()
        spec.name = name
        spec.annotation = annotation
        spec.default_is_set = default is not inspect.Parameter.empty

        if spec.default_is_set:
            if isinstance(default, Param):
                spec.default_val = default.default if default.default is not inspect.Parameter.empty else _UNSET
            else:
                spec.default_val = default

        # Classify parameter
        if annotation is Request or name == "request":
            spec.kind = "request"
        elif annotation is BackgroundTasks or name == "background_tasks":
            spec.kind = "background"
        elif isinstance(default, Depends):
            spec.kind = "depends"
            spec.depends_dep = default.dependency
            spec.depends_cache = default.use_cache
        elif isinstance(default, Path):
            spec.kind = "path"
            spec.descriptor = default
        elif isinstance(default, Query):
            spec.kind = "query"
            spec.descriptor = default
        elif isinstance(default, Body):
            spec.kind = "body"
            spec.descriptor = default
        elif isinstance(default, Header):
            spec.kind = "header"
            spec.descriptor = default
        elif isinstance(default, Cookie):
            spec.kind = "cookie"
            spec.descriptor = default
        elif (
            annotation
            and isinstance(annotation, type)
            and issubclass(annotation, BaseModel)
        ):
            spec.kind = "body_model"
        elif spec.default_is_set and not isinstance(default, Param):
            spec.kind = "default"
        else:
            spec.kind = "auto"  # Resolved at request time

        specs.append(spec)

    return specs


# ── Request-time kwarg builder (fast path with pre-compiled specs) ──

async def _build_kwargs(
    endpoint: Callable,
    request: Request,
    path_params: dict,
    dep_cache: _DependencyCache,
    background: BackgroundTasks,
) -> tuple[dict, list[str]]:
    """Build kwargs for an endpoint using pre-compiled signature specs."""
    # Get or compile the signature spec
    route_obj = getattr(endpoint, "__ylmz_route__", None)
    if route_obj is not None:
        specs = route_obj._signature
        if specs is None:
            specs = _compile_signature(endpoint)
            route_obj._signature = specs
    else:
        specs = _compile_signature(endpoint)

    kwargs = {}
    errors = []
    body_consumed = False
    body_cache = _UNSET

    for spec in specs:
        name = spec.name
        kind = spec.kind

        if kind == "request":
            kwargs[name] = request
            continue

        if kind == "background":
            kwargs[name] = background
            continue

        if kind == "depends":
            kwargs[name] = await _resolve_dependency(
                spec.depends_dep, dep_cache, use_cache=spec.depends_cache
            )
            continue

        # Descriptor-based parameters
        if kind == "path":
            d = spec.descriptor
            src = d.alias or name
            value = path_params.get(src)
            if value is not None and spec.annotation:
                try:
                    value = _coerce_path_param(spec.annotation, value, name)
                except (ValueError, TypeError) as e:
                    errors.append(str(e))
                    continue
            kwargs[name] = value if value is not None else (
                spec.default_val if spec.default_is_set else None
            )
            continue

        if kind == "query":
            d = spec.descriptor
            src = d.alias or name
            value = request.query_params.get(src)
            if value is not None and spec.annotation:
                try:
                    value = _coerce_param_value(spec.annotation, value, name, d)
                except (ValueError, TypeError) as e:
                    errors.append(str(e))
                    continue
            if value is not None:
                kwargs[name] = value
            elif spec.default_is_set:
                kwargs[name] = spec.default_val
            elif d.required:
                errors.append(f"Missing required parameter: '{name}'")
            continue

        if kind in ("body", "body_model"):
            if body_cache is _UNSET:
                try:
                    body_cache = await request.json() or {}
                except Exception:
                    body_cache = {}
            body_raw = body_cache

            if kind == "body" and spec.descriptor is not None:
                d = spec.descriptor
                if d.embed and d.alias and d.alias in body_raw:
                    body_raw = body_raw[d.alias]
                elif d.embed and name in body_raw:
                    body_raw = body_raw[name]

            if spec.annotation and isinstance(spec.annotation, type) and issubclass(spec.annotation, BaseModel):
                try:
                    kwargs[name] = spec.annotation(**body_raw)
                except TypeError as e:
                    errors.append(str(e))
            else:
                kwargs[name] = body_raw
            continue

        if kind == "header":
            d = spec.descriptor
            src = (d.alias or name).lower()
            value = request.headers.get(src)
            if value is None and "_" in src:
                value = request.headers.get(src.replace("_", "-"))
            if value is not None:
                kwargs[name] = value
            elif spec.default_is_set:
                kwargs[name] = spec.default_val
            elif d.required:
                errors.append(f"Missing required header: '{name}'")
            continue

        if kind == "cookie":
            d = spec.descriptor
            src = d.alias or name
            value = request.cookies.get(src)
            if value is not None:
                kwargs[name] = value
            elif spec.default_is_set:
                kwargs[name] = spec.default_val
            elif d.required:
                errors.append(f"Missing required cookie: '{name}'")
            continue

        if kind == "default":
            # Try path/query before falling back to default
            if name in path_params:
                value = path_params[name]
                if spec.annotation:
                    try:
                        value = _coerce_path_param(spec.annotation, value, name)
                    except (ValueError, TypeError) as e:
                        errors.append(str(e))
                        continue
                kwargs[name] = value
            elif name in request.query_params:
                value = request.query_params[name]
                if spec.annotation:
                    try:
                        value = _coerce_path_param(spec.annotation, value, name)
                    except (ValueError, TypeError) as e:
                        errors.append(str(e))
                        continue
                kwargs[name] = value
            else:
                kwargs[name] = spec.default_val
            continue

        # --- kind == "auto": implicit resolution ---

        # Path param
        if name in path_params:
            value = path_params[name]
            if spec.annotation:
                try:
                    value = _coerce_path_param(spec.annotation, value, name)
                except (ValueError, TypeError) as e:
                    errors.append(str(e))
                    continue
            kwargs[name] = value
            continue

        # Query param
        if name in request.query_params:
            value = request.query_params[name]
            if spec.annotation:
                try:
                    value = _coerce_path_param(spec.annotation, value, name)
                except (ValueError, TypeError) as e:
                    errors.append(str(e))
                    continue
            kwargs[name] = value
            continue

        # Default
        if spec.default_is_set:
            kwargs[name] = spec.default_val
            continue

        errors.append(f"Missing required parameter: '{name}'")

    return kwargs, errors


# ── Coercion helpers ─────────────────────────────────────────

_COERCE_BOOL = lambda v: str(v).lower() in ("true", "1", "yes", "on")
_COERCE_INT = int
_COERCE_FLOAT = float
_COERCE_STR = str

_COERCE_MAP = {
    bool: _COERCE_BOOL,
    int: _COERCE_INT,
    float: _COERCE_FLOAT,
    str: _COERCE_STR,
}


def _coerce_path_param(annotation: type, value: str, name: str) -> Any:
    """Coerce a string path/query parameter to the annotated type."""
    coercer = _COERCE_MAP.get(annotation)
    if coercer is not None:
        return coercer(value)
    return value


def _coerce_param_value(annotation: type, value: Any, name: str, param_def: Query) -> Any:
    """Coerce a query parameter value with constraint validation."""
    if annotation is bool:
        result = str(value).lower() in ("true", "1", "yes", "on")
    elif annotation in (int, float):
        result = annotation(value)
    elif annotation is str:
        result = str(value)
        if param_def.min_length and len(result) < param_def.min_length:
            raise ValueError(f"'{name}' length ({len(result)}) < min ({param_def.min_length})")
        if param_def.max_length and len(result) > param_def.max_length:
            raise ValueError(f"'{name}' length ({len(result)}) > max ({param_def.max_length})")
        if param_def.pattern and not re.match(param_def.pattern, result):
            raise ValueError(f"'{name}' doesn't match pattern")
    else:
        result = annotation(value) if annotation else value

    # Numeric constraints
    if param_def.ge is not None and result < param_def.ge:
        raise ValueError(f"'{name}' ({result}) must be >= {param_def.ge}")
    if param_def.le is not None and result > param_def.le:
        raise ValueError(f"'{name}' ({result}) must be <= {param_def.le}")
    if param_def.gt is not None and result <= param_def.gt:
        raise ValueError(f"'{name}' ({result}) must be > {param_def.gt}")
    if param_def.lt is not None and result >= param_def.lt:
        raise ValueError(f"'{name}' ({result}) must be < {param_def.lt}")

    return result
