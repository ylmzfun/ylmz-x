"""Tests for the ylmz framework core."""

import pytest
from ylmz.types import BaseModel, Field, validate
from ylmz.response import JSONResponse, PlainTextResponse, HTMLResponse, StreamingResponse
from ylmz.exceptions import HTTPException


# ── Type System Tests ───────────────────────────────────────


class User(BaseModel):
    name: str
    age: int


class Post(BaseModel):
    title: str
    tags: list[str] = []
    metadata: dict = {}


class NestedModel(BaseModel):
    user: User
    content: str


class ModelWithDefaults(BaseModel):
    name: str
    count: int = 0
    active: bool = True


class ModelWithFactory(BaseModel):
    name: str
    items: list[str] = Field(default_factory=list)


class TestBaseModel:
    def test_simple_model(self):
        u = User(name="Alice", age=30)
        assert u.name == "Alice"
        assert u.age == 30

    def test_model_dump(self):
        u = User(name="Bob", age=25)
        assert u.model_dump() == {"name": "Bob", "age": 25}

    def test_required_field_raises(self):
        with pytest.raises(TypeError, match="required"):
            User(name="Alice")

    def test_type_coercion_int_from_str(self):
        u = User(name="Alice", age="30")
        assert u.age == 30
        assert isinstance(u.age, int)

    def test_type_coercion_float_from_str(self):
        class Product(BaseModel):
            price: float

        p = Product(price="9.99")
        assert p.price == 9.99
        assert isinstance(p.price, float)

    def test_invalid_type_raises(self):
        with pytest.raises(TypeError):
            User(name="Alice", age="not-a-number")

    def test_list_field(self):
        p = Post(title="Hello", tags=["a", "b"])
        assert p.tags == ["a", "b"]

    def test_default_list(self):
        p = Post(title="Hello")
        assert p.tags == []
        assert p.metadata == {}

    def test_nested_model(self):
        nm = NestedModel(user={"name": "Eve", "age": 28}, content="test")
        assert isinstance(nm.user, User)
        assert nm.user.name == "Eve"
        assert nm.user.age == 28

    def test_nested_model_passed_as_object(self):
        u = User(name="Eve", age=28)
        nm = NestedModel(user=u, content="test")
        assert nm.user is u

    def test_validate_shortcut(self):
        u = validate(User, {"name": "Zoe", "age": 22})
        assert isinstance(u, User)
        assert u.name == "Zoe"

    def test_defaults(self):
        m = ModelWithDefaults(name="test")
        assert m.count == 0
        assert m.active is True

    def test_field_factory(self):
        m1 = ModelWithFactory(name="a")
        m2 = ModelWithFactory(name="b")
        m1.items.append("x")
        assert m1.items == ["x"]
        assert m2.items == []

    def test_bool_type(self):
        class Config(BaseModel):
            enabled: bool

        c1 = Config(enabled=True)
        assert c1.enabled is True
        c2 = Config(enabled=False)
        assert c2.enabled is False

    def test_bool_rejects_non_bool(self):
        class Config(BaseModel):
            enabled: bool

        with pytest.raises(TypeError):
            Config(enabled=1)

    def test_list_item_coercion(self):
        class Scores(BaseModel):
            points: list[int]

        s = Scores(points=["1", "2", "3"])
        assert s.points == [1, 2, 3]

    def test_dict_coercion(self):
        class Translation(BaseModel):
            labels: dict[str, str]

        t = Translation(labels={"en": "Hello", "fr": 123})
        assert t.labels == {"en": "Hello", "fr": "123"}


# ── Response Tests ──────────────────────────────────────────


class TestResponse:
    def test_json_response(self):
        r = JSONResponse({"key": "value"})
        assert r.status_code == 200
        assert r.body == b'{"key": "value"}'

    def test_json_response_status(self):
        r = JSONResponse({"error": "gone"}, status_code=404)
        assert r.status_code == 404

    def test_plain_text_response(self):
        r = PlainTextResponse("hello world")
        assert r.status_code == 200
        assert r.body == b"hello world"

    def test_html_response(self):
        r = HTMLResponse("<h1>Title</h1>")
        assert r.status_code == 200
        assert b"<h1>Title</h1>" in r.body
        assert "text/html" in r.headers["content-type"]

    def test_response_headers(self):
        r = JSONResponse({"ok": True}, headers={"x-custom": "val"})
        assert r.headers["x-custom"] == "val"

    def test_streaming_response_created(self):
        async def gen():
            yield b"chunk1"
            yield b"chunk2"

        sr = StreamingResponse(gen())
        assert sr.status_code == 200


# ── Exception Tests ─────────────────────────────────────────


class TestHTTPException:
    def test_basic(self):
        exc = HTTPException(404, "Not Found")
        assert exc.status_code == 404
        assert exc.detail == "Not Found"

    def test_with_headers(self):
        exc = HTTPException(400, "Bad", headers={"x-error": "yes"})
        assert exc.headers["x-error"] == "yes"
