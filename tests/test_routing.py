"""Tests for the routing and application layer."""

import pytest
from ylmz.routing import Router, Route
from ylmz.app import Ylmz
from ylmz.response import JSONResponse
from ylmz.exceptions import HTTPException


# ── Route Tests ─────────────────────────────────────────────


class TestRoute:
    def test_static_path_match(self):
        r = Route("/users", lambda: None, {"GET"})
        assert r.match("GET", "/users") == {}
        assert r.match("POST", "/users") is None
        assert r.match("GET", "/other") is None

    def test_path_param(self):
        r = Route("/users/{user_id}", lambda: None, {"GET"})
        params = r.match("GET", "/users/42")
        assert params == {"user_id": "42"}

    def test_multiple_params(self):
        r = Route("/orgs/{org}/repos/{repo}", lambda: None, {"GET"})
        params = r.match("GET", "/orgs/acme/repos/backend")
        assert params == {"org": "acme", "repo": "backend"}

    def test_root_path(self):
        r = Route("/", lambda: None, {"GET"})
        assert r.match("GET", "/") == {}
        assert r.match("GET", "") == {}

    def test_trailing_slash(self):
        r = Route("/users", lambda: None, {"GET"})
        assert r.match("GET", "/users/") == {}


# ── Router Tests ────────────────────────────────────────────


class TestRouter:
    def test_basic_routing(self):
        router = Router()

        @router.get("/hello")
        async def hello():
            return "world"

        endpoint, params = router.match("GET", "/hello")
        assert endpoint is hello
        assert params == {}

    def test_method_not_allowed(self):
        router = Router()

        @router.get("/items")
        async def get_items():
            pass

        endpoint, _ = router.match("POST", "/items")
        assert endpoint is None

    def test_prefix(self):
        router = Router(prefix="/api")

        @router.get("/data")
        async def data():
            pass

        endpoint, params = router.match("GET", "/api/data")
        assert endpoint is data

    def test_sub_router_inclusion(self):
        main = Router()

        @main.get("/root")
        async def root_handler():
            pass

        sub = Router(prefix="/v1")

        @sub.get("/items")
        async def items():
            pass

        main.include_router(sub)

        ep1, _ = main.match("GET", "/root")
        assert ep1 is root_handler

        ep2, _ = main.match("GET", "/v1/items")
        assert ep2 is items


# ── Application Tests ───────────────────────────────────────


class TestApplication:
    def test_app_creation(self):
        app = Ylmz()
        assert app.title == "ylmz"
        assert app.debug is False

    def test_route_registration(self):
        app = Ylmz()

        @app.get("/ping")
        async def ping():
            return "pong"

        ep, _ = app.router.match("GET", "/ping")
        assert ep is ping

    def test_response_building_dict(self):
        app = Ylmz()
        resp = app._build_response({"key": "val"})
        assert isinstance(resp, JSONResponse)
        assert resp.status_code == 200

    def test_response_building_list(self):
        app = Ylmz()
        resp = app._build_response([1, 2, 3])
        assert isinstance(resp, JSONResponse)

    def test_response_building_passthrough(self):
        app = Ylmz()
        from ylmz.response import PlainTextResponse

        original = PlainTextResponse("raw")
        result = app._build_response(original)
        assert result is original

    def test_sub_router_include(self):
        app = Ylmz()
        sub = Router(prefix="/api")

        @sub.get("/status")
        async def status():
            return {"ok": True}

        app.include_router(sub)
        ep, params = app.router.match("GET", "/api/status")
        assert ep is status
        assert params == {}


# ── Integration Tests (using ASGI test client) ──────────────


class TestASGIIntegration:
    @pytest.fixture
    def app(self):
        app = Ylmz(debug=True)

        @app.get("/")
        async def root():
            return {"hello": "world"}

        @app.get("/echo/{msg}")
        async def echo(msg: str):
            return {"msg": msg}

        @app.get("/add/{a:int}/{b:int}")
        async def add(a: int, b: int):
            return {"result": a + b}

        @app.get("/search")
        async def search(q: str = ""):
            return {"query": q}

        @app.post("/items")
        async def create_item(request):
            body = await request.json()
            return {"created": body}

        @app.get("/error")
        async def error():
            raise HTTPException(418, "I'm a teapot")

        return app

    @pytest.fixture
    async def client(self, app):
        import httpx
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    @pytest.mark.asyncio
    async def test_root(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert resp.json() == {"hello": "world"}

    @pytest.mark.asyncio
    async def test_path_param(self, client):
        resp = await client.get("/echo/hello")
        assert resp.status_code == 200
        assert resp.json() == {"msg": "hello"}

    @pytest.mark.asyncio
    async def test_path_param_int_coercion(self, client):
        resp = await client.get("/add/3/7")
        assert resp.status_code == 200
        assert resp.json() == {"result": 10}

    @pytest.mark.asyncio
    async def test_query_param(self, client):
        resp = await client.get("/search?q=hello")
        assert resp.status_code == 200
        assert resp.json() == {"query": "hello"}

    @pytest.mark.asyncio
    async def test_query_param_default(self, client):
        resp = await client.get("/search")
        assert resp.status_code == 200
        assert resp.json() == {"query": ""}

    @pytest.mark.asyncio
    async def test_post_json_body(self, client):
        resp = await client.post("/items", json={"name": "thing"})
        assert resp.status_code == 200
        assert resp.json() == {"created": {"name": "thing"}}

    @pytest.mark.asyncio
    async def test_404_not_found(self, client):
        resp = await client.get("/nonexistent")
        assert resp.status_code == 404
        assert "Not Found" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_http_exception(self, client):
        resp = await client.get("/error")
        assert resp.status_code == 418
        assert resp.json()["detail"] == "I'm a teapot"

    @pytest.mark.asyncio
    async def test_422_validation_error(self, client):
        resp = await client.get("/add/abc/def")
        assert resp.status_code == 422
