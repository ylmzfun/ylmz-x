"""Parameter descriptors — explicit Path, Query, Body, Header, Cookie markers."""

from __future__ import annotations

from typing import Any


class Param:
    """Base class for parameter descriptors."""

    def __init__(
        self,
        default: Any = ...,
        *,
        alias: str = None,
        description: str = "",
        required: bool = None,
    ):
        self.default = default
        self.alias = alias
        self.description = description
        self.required = required


class Path(Param):
    """Declare a path parameter with metadata.

    Usage::

        @app.get("/items/{item_id}")
        async def get_item(item_id: int = Path(description="The item ID")):
            ...
    """

    def __init__(self, default: Any = ..., **kwargs):
        super().__init__(default, **kwargs)
        if self.required is None and self.default is ...:
            self.required = True


class Query(Param):
    """Declare a query parameter with metadata.

    Usage::

        @app.get("/items")
        async def search(
            q: str = Query(default="", description="Search term", min_length=1),
            page: int = Query(default=1, ge=1),
        ):
            ...
    """

    def __init__(
        self,
        default: Any = ...,
        *,
        alias: str = None,
        description: str = "",
        required: bool = None,
        min_length: int = None,
        max_length: int = None,
        ge: float = None,
        le: float = None,
        gt: float = None,
        lt: float = None,
        pattern: str = None,
    ):
        super().__init__(default, alias=alias, description=description, required=required)
        self.min_length = min_length
        self.max_length = max_length
        self.ge = ge
        self.le = le
        self.gt = gt
        self.lt = lt
        self.pattern = pattern


class Body(Param):
    """Declare that a parameter comes from the request body.

    Usage::

        @app.post("/items")
        async def create_item(item: Item = Body()):
            ...

        # With embedded key:
        @app.post("/items")
        async def create_item(data: Item = Body(embed=True)):
            ...
    """

    def __init__(
        self,
        default: Any = ...,
        *,
        embed: bool = False,
        description: str = "",
    ):
        super().__init__(default, description=description)
        self.embed = embed
        if self.required is None and self.default is ...:
            self.required = True


class Header(Param):
    """Declare a parameter from request headers.

    Usage::

        @app.get("/items")
        async def list_items(user_agent: str = Header(alias="User-Agent")):
            ...
    """

    def __init__(self, default: Any = ..., **kwargs):
        super().__init__(default, **kwargs)


class Cookie(Param):
    """Declare a parameter from cookies.

    Usage::

        @app.get("/items")
        async def list_items(session_id: str = Cookie()):
            ...
    """

    def __init__(self, default: Any = ..., **kwargs):
        super().__init__(default, **kwargs)
