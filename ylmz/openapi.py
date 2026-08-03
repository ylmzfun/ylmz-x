"""OpenAPI / Swagger documentation auto-generation."""

from __future__ import annotations

import json
from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum
from uuid import UUID

from ylmz.types import BaseModel, Field
from ylmz.routing import Router, Route
from ylmz.params import Path, Query, Body, Header, Cookie
from ylmz.depends import Depends


# JSON Schema type mapping
_TYPE_MAP = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
    datetime: {"type": "string", "format": "date-time"},
    date: {"type": "string", "format": "date"},
    time: {"type": "string", "format": "time"},
    UUID: {"type": "string", "format": "uuid"},
    Decimal: "number",
}


def _python_type_to_schema(py_type: type) -> dict:
    """Convert a Python type to a JSON Schema fragment."""
    from typing import get_origin, get_args

    origin = get_origin(py_type)
    args = get_args(py_type)

    if origin is not None:
        if origin is list:
            item_schema = _python_type_to_schema(args[0]) if args else {}
            return {"type": "array", "items": item_schema}
        if origin is dict:
            return {"type": "object"}

    # Check for UnionType (X | Y syntax)
    try:
        from types import UnionType

        if isinstance(py_type, type) and origin is UnionType:
            schemas = [_python_type_to_schema(a) for a in args if a is not type(None)]
            nullable = type(None) in args
            if len(schemas) == 1:
                result = dict(schemas[0])
                if nullable:
                    result["nullable"] = True
                return result
            return {"anyOf": schemas}
    except ImportError:
        pass

    if isinstance(py_type, type) and issubclass(py_type, Enum):
        return {"type": "string", "enum": [str(m.value) for m in py_type]}

    if isinstance(py_type, type) and issubclass(py_type, BaseModel):
        return _model_to_schema(py_type)

    if py_type in _TYPE_MAP:
        mapping = _TYPE_MAP[py_type]
        if isinstance(mapping, str):
            return {"type": mapping}
        return dict(mapping)

    return {"type": "string"}


def _model_to_schema(model_cls: type[BaseModel]) -> dict:
    """Generate JSON Schema for a BaseModel subclass."""
    properties = {}
    required = []

    for field_name, (py_type, field_def, alias) in model_cls.__fields__.items():
        schema = _python_type_to_schema(py_type)
        if isinstance(field_def, Field):
            if field_def.description:
                schema["description"] = field_def.description
            if field_def.ge is not None:
                schema["minimum"] = field_def.ge
            if field_def.le is not None:
                schema["maximum"] = field_def.le
            if field_def.gt is not None:
                schema["exclusiveMinimum"] = field_def.gt
            if field_def.lt is not None:
                schema["exclusiveMaximum"] = field_def.lt
            if field_def.min_length is not None:
                schema["minLength"] = field_def.min_length
            if field_def.max_length is not None:
                schema["maxLength"] = field_def.max_length
            if field_def.pattern is not None:
                schema["pattern"] = field_def.pattern
            if field_def.default is not ...:
                schema["default"] = field_def.default
        properties[alias if alias != field_name else field_name] = schema
        if field_name in model_cls.__required__:
            required.append(field_name)

    result = {"type": "object", "properties": properties}
    if required:
        result["required"] = required
    return result


def generate_openapi(
    app,
    *,
    title: str = "ylmz API",
    version: str = "0.1.0",
    description: str = "",
) -> dict:
    """Generate an OpenAPI 3.0 schema from the application routes."""
    paths = {}
    schemas = {}

    for route in app.router.routes:
        for method in route.methods:
            if method == "WEBSOCKET":
                continue

            http_method = method.lower()
            path_key = _route_to_openapi_path(route._pattern.pattern)

            if path_key not in paths:
                paths[path_key] = {}

            operation = _build_operation(route, method, schemas)
            paths[path_key][http_method] = operation

    return {
        "openapi": "3.0.2",
        "info": {
            "title": title,
            "version": version,
            "description": description or f"Auto-generated API docs for {title}",
        },
        "paths": paths,
        "components": {
            "schemas": schemas or {},
        },
    }


def _route_to_openapi_path(pattern: str) -> str:
    """Convert a compiled regex pattern to an OpenAPI path template."""
    import re

    # Extract the path segments from the regex pattern
    result = ""
    segments = pattern.strip("^").strip("$").strip("/?").split("/")
    for seg in segments:
        if seg and seg != "?":
            if seg == r"([^/]+)":
                # Placeholder — we need the original param name
                result += "/{param}"
            else:
                result += "/" + re.sub(r"\\(.)", r"\1", seg)
    return result if result else "/"


def _build_operation(route: Route, method: str, schemas: dict) -> dict:
    """Build an OpenAPI operation object for a route."""
    import inspect

    endpoint = route.endpoint
    doc = inspect.getdoc(endpoint) or ""
    sig = inspect.signature(endpoint)

    operation: dict = {
        "summary": endpoint.__name__.replace("_", " ").title(),
        "description": doc,
        "responses": {
            "200": {"description": "Successful response"},
        },
    }

    parameters = []
    request_body = None

    for name, param in sig.parameters.items():
        annotation = param.annotation if param.annotation is not inspect.Parameter.empty else None
        default = param.default

        if annotation in (None, inspect.Parameter.empty):
            continue

        if isinstance(default, Path) or (
            not isinstance(default, (Query, Body, Header, Cookie, Depends, Field))
            and name in (route._param_names if hasattr(route, "_param_names") else [])
        ):
            # Path parameter
            schema = _python_type_to_schema(annotation) if annotation is not inspect.Parameter.empty else {"type": "string"}
            parameters.append({
                "name": name,
                "in": "path",
                "required": True,
                "schema": schema,
                "description": getattr(default, "description", ""),
            })
        elif isinstance(default, Query):
            schema = _python_type_to_schema(annotation) if annotation is not inspect.Parameter.empty else {"type": "string"}
            parameters.append({
                "name": default.alias or name,
                "in": "query",
                "required": default.required if default.required is not None else False,
                "schema": schema,
                "description": default.description,
            })
        elif isinstance(default, Header):
            schema = _python_type_to_schema(annotation) if annotation is not inspect.Parameter.empty else {"type": "string"}
            parameters.append({
                "name": default.alias or name,
                "in": "header",
                "required": default.required if default.required is not None else False,
                "schema": schema,
                "description": default.description,
            })
        elif isinstance(default, Cookie):
            schema = _python_type_to_schema(annotation) if annotation is not inspect.Parameter.empty else {"type": "string"}
            parameters.append({
                "name": default.alias or name,
                "in": "cookie",
                "required": default.required if default.required is not None else False,
                "schema": schema,
            })
        elif isinstance(default, Body) or (
            isinstance(annotation, type)
            and issubclass(annotation, BaseModel)
        ):
            # Request body
            if isinstance(annotation, type) and issubclass(annotation, BaseModel):
                schema_name = annotation.__name__
                schemas[schema_name] = _model_to_schema(annotation)
                request_body = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{schema_name}"}
                        }
                    },
                }

    if parameters:
        operation["parameters"] = parameters
    if request_body:
        operation["requestBody"] = request_body

    return operation


# Swagger UI HTML template (CDN-based, zero dependencies)
SWAGGER_UI_HTML = """<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
    <title>{title} - Swagger UI</title>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        SwaggerUIBundle({{
            url: "{openapi_url}",
            dom_id: "#swagger-ui",
            deepLinking: true,
            presets: [SwaggerUIBundle.presets.apis],
        }});
    </script>
</body>
</html>"""

REDOC_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>{title} - ReDoc</title>
    <meta charset="utf-8"/>
    <style> body {{ margin: 0; padding: 0; }} </style>
</head>
<body>
    <redoc spec-url="{openapi_url}"></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"></script>
</body>
</html>"""


def setup_docs(app, openapi_url: str = "/openapi.json") -> None:
    """Set up /docs, /redoc, and /openapi.json routes on the app."""

    @app.get(openapi_url)
    async def openapi_schema():
        return generate_openapi(app, title=app.title)

    @app.get("/docs")
    async def swagger_ui():
        from ylmz.response import HTMLResponse

        return HTMLResponse(
            SWAGGER_UI_HTML.format(title=app.title, openapi_url=openapi_url)
        )

    @app.get("/redoc")
    async def redoc():
        from ylmz.response import HTMLResponse

        return HTMLResponse(
            REDOC_HTML.format(title=app.title, openapi_url=openapi_url)
        )
