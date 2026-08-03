"""Tests for new advanced features: DI, types, params, OpenAPI, etc."""

import pytest
from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum
from typing import Optional, Union, List, Dict
from uuid import UUID, uuid4

from ylmz.types import BaseModel, Field, validator
from ylmz.depends import Depends
from ylmz.params import Path, Query, Body, Header, Cookie
from ylmz.status import status
from ylmz.background import BackgroundTasks
from ylmz.app import Ylmz


# ── Enum, Optional, Union Tests ─────────────────────────────


class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class AdvancedModel(BaseModel):
    name: str
    color: Color
    tags: Optional[list[str]] = None
    count: int = Field(ge=0, le=100)
    description: str = Field(default="", max_length=200)


class DateTimeModel(BaseModel):
    created_at: datetime
    event_date: Optional[date] = None
    uid: Optional[UUID] = None
    price: Optional[Decimal] = None


class TestAdvancedTypes:
    def test_enum_field(self):
        m = AdvancedModel(name="test", color="red", count=50)
        assert m.color == Color.RED

    def test_enum_invalid(self):
        with pytest.raises(TypeError):
            AdvancedModel(name="test", color="yellow")

    def test_optional_list(self):
        m = AdvancedModel(name="test", color="blue", tags=["a", "b"], count=50)
        assert m.tags == ["a", "b"]

        m2 = AdvancedModel(name="test2", color="green", count=50)
        assert m2.tags is None

    def test_field_constraints_ge(self):
        with pytest.raises(TypeError, match=">="):
            AdvancedModel(name="x", color="red", count=-1)

    def test_field_constraints_le(self):
        with pytest.raises(TypeError, match="<="):
            AdvancedModel(name="x", color="red", count=101)

    def test_max_length(self):
        with pytest.raises(TypeError):
            AdvancedModel(name="x", color="red", description="a" * 201)

    def test_datetime_iso(self):
        m = DateTimeModel(created_at="2024-01-15T10:30:00")
        assert isinstance(m.created_at, datetime)
        assert m.created_at.year == 2024

    def test_date_field(self):
        m = DateTimeModel(created_at="2024-01-15T10:30:00", event_date="2024-06-01")
        assert isinstance(m.event_date, date)

    def test_uuid_field(self):
        uid = uuid4()
        m = DateTimeModel(created_at=datetime.now(), uid=str(uid))
        assert isinstance(m.uid, UUID)
        assert m.uid == uid

    def test_decimal_field(self):
        m = DateTimeModel(created_at=datetime.now(), price="19.99")
        assert isinstance(m.price, Decimal)
        assert m.price == Decimal("19.99")

    def test_model_dump_json(self):
        m = DateTimeModel(
            created_at=datetime(2024, 1, 15, 10, 30),
            uid=UUID("12345678-1234-5678-1234-567812345678"),
        )
        json_str = m.model_dump_json()
        assert "2024-01-15T10:30:00" in json_str
        assert "12345678-1234-5678-1234-567812345678" in json_str

    def test_model_validate(self):
        m = DateTimeModel.model_validate(
            {"created_at": "2024-01-01T00:00:00"}
        )
        assert isinstance(m, DateTimeModel)


# ── Validator Tests ─────────────────────────────────────────


class ValidatedModel(BaseModel):
    name: str
    age: int

    @validator("name")
    def check_name(cls, v):
        if len(v) < 2:
            raise ValueError("Name too short")
        return v.strip()

    @validator("age")
    def check_age(cls, v):
        if v < 0:
            raise ValueError("Age must be positive")
        return v


class TestValidators:
    def test_validator_pass(self):
        m = ValidatedModel(name=" Alice ", age=30)
        assert m.name == "Alice"
        assert m.age == 30

    def test_validator_fail(self):
        with pytest.raises(TypeError, match="Name too short"):
            ValidatedModel(name="A", age=30)

    def test_validator_negative_age(self):
        with pytest.raises(TypeError, match="Age must be positive"):
            ValidatedModel(name="Bob", age=-5)


# ── Field Alias Tests ────────────────────────────────────────


class AliasedModel(BaseModel):
    user_name: str = Field(alias="userName")
    first_name: str = Field(alias="firstName")


class TestFieldAlias:
    def test_alias_input(self):
        m = AliasedModel(userName="john", firstName="John")
        assert m.user_name == "john"
        assert m.first_name == "John"

    def test_original_name_still_works(self):
        m = AliasedModel(user_name="jane", first_name="Jane")
        assert m.user_name == "jane"

    def test_alias_preferred(self):
        m = AliasedModel(user_name="jane", userName="john", firstName="John")
        # user_name takes precedence since it's the field name
        assert m.user_name == "jane"


# ── Status Codes Tests ───────────────────────────────────────


class TestStatusCodes:
    def test_common_codes(self):
        assert status.OK == 200
        assert status.CREATED == 201
        assert status.NO_CONTENT == 204
        assert status.BAD_REQUEST == 400
        assert status.NOT_FOUND == 404
        assert status.UNPROCESSABLE_ENTITY == 422
        assert status.INTERNAL_SERVER_ERROR == 500


# ── Depends Tests ────────────────────────────────────────────


class TestDepends:
    def test_depends_creation(self):
        async def get_db():
            return {"db": "connected"}

        d = Depends(get_db)
        assert d.dependency is get_db
        assert d.use_cache is True

    def test_depends_no_cache(self):
        def get_counter():
            return {"count": 1}

        d = Depends(get_counter, use_cache=False)
        assert d.use_cache is False


# ── Param Descriptor Tests ───────────────────────────────────


class TestParams:
    def test_path_param(self):
        p = Path(description="The item ID")
        assert p.description == "The item ID"
        assert p.required is True

    def test_query_param(self):
        q = Query(default="", description="Search term", min_length=1, ge=0)
        assert q.default == ""
        assert q.min_length == 1
        assert q.ge == 0

    def test_body_param(self):
        b = Body(description="Item data")
        assert b.description == "Item data"

    def test_header_param(self):
        h = Header(alias="X-API-Key")
        assert h.alias == "X-API-Key"

    def test_cookie_param(self):
        c = Cookie(default="session123")
        assert c.default == "session123"


# ── BackgroundTasks Tests ────────────────────────────────────


class TestBackgroundTasks:
    @pytest.mark.asyncio
    async def test_add_and_run(self):
        results = []

        async def task(msg: str):
            results.append(msg)

        bt = BackgroundTasks()
        bt.add_task(task, "hello")
        await bt.run()
        assert results == ["hello"]

    @pytest.mark.asyncio
    async def test_multiple_tasks(self):
        results = []

        async def task(i):
            results.append(i)

        bt = BackgroundTasks()
        for i in range(3):
            bt.add_task(task, i)
        await bt.run()
        assert sorted(results) == [0, 1, 2]


# ── Application Level Integration Tests ──────────────────────


class TestDIIntegration:
    @pytest.fixture
    def app(self):
        app = Ylmz(debug=True)

        async def get_config():
            return {"env": "test", "debug": True}

        @app.get("/config")
        async def read_config(config=Depends(get_config)):
            return config

        # Sub-dependency
        async def get_db(config=Depends(get_config)):
            return f"db://{config['env']}"

        @app.get("/db")
        async def read_db(db=Depends(get_db)):
            return {"dsn": db}

        # Depends with BackgroundTasks
        @app.post("/notify")
        async def notify(background_tasks: BackgroundTasks, message: str = Query(default="")):
            async def send(msg):
                pass  # Simulated

            background_tasks.add_task(send, message)
            return {"queued": message}

        return app

    @pytest.fixture
    async def client(self, app):
        import httpx
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    @pytest.mark.asyncio
    async def test_simple_depends(self, client):
        resp = await client.get("/config")
        assert resp.status_code == 200
        assert resp.json() == {"env": "test", "debug": True}

    @pytest.mark.asyncio
    async def test_sub_dependency(self, client):
        resp = await client.get("/db")
        assert resp.status_code == 200
        assert resp.json() == {"dsn": "db://test"}

    @pytest.mark.asyncio
    async def test_background_tasks_injection(self, client):
        resp = await client.post("/notify?message=hello")
        assert resp.status_code == 200
        assert resp.json()["queued"] == "hello"


# ── Param Descriptor Integration Tests ───────────────────────


class TestParamDescriptorsIntegration:
    @pytest.fixture
    def app(self):
        app = Ylmz(debug=True)

        @app.get("/search")
        async def search(
            q: str = Query(default="", description="Search term", min_length=1),
            page: int = Query(default=1, ge=1),
        ):
            return {"q": q, "page": page}

        @app.get("/items/{item_id}")
        async def get_item(
            item_id: int = Path(description="Item ID"),
        ):
            return {"item_id": item_id}

        @app.get("/headers")
        async def get_headers(
            user_agent: str = Header(default="unknown"),
            x_token: str = Header(default="", alias="x-token"),
        ):
            return {"user_agent": user_agent, "x_token": x_token}

        return app

    @pytest.fixture
    async def client(self, app):
        import httpx
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    @pytest.mark.asyncio
    async def test_query_with_defaults(self, client):
        resp = await client.get("/search")
        assert resp.status_code == 200
        data = resp.json()
        assert data["q"] == ""
        assert data["page"] == 1

    @pytest.mark.asyncio
    async def test_query_with_values(self, client):
        resp = await client.get("/search?q=hello&page=3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["q"] == "hello"
        assert data["page"] == 3

    @pytest.mark.asyncio
    async def test_path_with_descriptor(self, client):
        resp = await client.get("/items/42")
        assert resp.status_code == 200
        assert resp.json()["item_id"] == 42

    @pytest.mark.asyncio
    async def test_header_param(self, client):
        resp = await client.get(
            "/headers",
            headers={"user-agent": "pytest", "x-token": "secret123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_agent"] == "pytest"
        assert data["x_token"] == "secret123"


# ── Custom Exception Handler Tests ───────────────────────────


class TestExceptionHandlers:
    @pytest.fixture
    def app(self):
        app = Ylmz(debug=True)

        class CustomError(Exception):
            pass

        @app.exception_handler(CustomError)
        async def handle_custom(request, exc):
            from ylmz.response import JSONResponse
            return JSONResponse(
                {"error": "custom", "detail": str(exc)},
                status_code=status.BAD_REQUEST,
            )

        @app.get("/fail")
        async def fail():
            raise CustomError("something went wrong")

        return app

    @pytest.fixture
    async def client(self, app):
        import httpx
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    @pytest.mark.asyncio
    async def test_custom_exception_handler(self, client):
        resp = await client.get("/fail")
        assert resp.status_code == 400
        data = resp.json()
        assert data["error"] == "custom"
        assert data["detail"] == "something went wrong"


# ── OpenAPI Tests ────────────────────────────────────────────


class TestOpenAPI:
    def test_generate_schema(self):
        app = Ylmz(title="Test API")

        @app.get("/items")
        async def list_items(q: str = Query(default="")):
            """List all items."""
            return []

        @app.post("/items")
        async def create_item(data: dict):
            return data

        from ylmz.openapi import generate_openapi
        schema = generate_openapi(app, title="Test API")

        assert schema["openapi"] == "3.0.2"
        assert schema["info"]["title"] == "Test API"
        assert "/items" in schema["paths"]
        assert "get" in schema["paths"]["/items"]
        assert "post" in schema["paths"]["/items"]

    def test_model_to_schema(self):
        class Product(BaseModel):
            name: str = Field(description="Product name")
            price: float = Field(ge=0)
            in_stock: bool = True

        from ylmz.openapi import _model_to_schema
        schema = _model_to_schema(Product)

        assert schema["type"] == "object"
        assert "name" in schema["properties"]
        assert "price" in schema["properties"]
        assert schema["properties"]["price"]["minimum"] == 0

    def test_setup_docs(self):
        app = Ylmz(title="DocTest")
        from ylmz.openapi import setup_docs
        setup_docs(app)

        ep, _ = app.router.match("GET", "/docs")
        assert ep is not None
        ep2, _ = app.router.match("GET", "/redoc")
        assert ep2 is not None
        ep3, _ = app.router.match("GET", "/openapi.json")
        assert ep3 is not None
