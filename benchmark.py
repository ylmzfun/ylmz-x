"""Quick performance benchmark for ylmz vs raw ASGI."""

import time
import asyncio
from ylmz import Ylmz, BaseModel


app = Ylmz()


class Item(BaseModel):
    name: str
    price: float
    in_stock: bool = True


@app.get("/")
async def root():
    return {"hello": "world"}


@app.get("/items/{item_id:int}")
async def get_item(item_id: int):
    return {"id": item_id}


@app.get("/search")
async def search(q: str = ""):
    return {"q": q}


@app.post("/items")
async def create_item(item: Item):
    return {"created": item.model_dump()}


# Setup 100 routes to test trie scaling
for i in range(100):
    @app.get(f"/api/v{i}")
    async def handler():
        return {"v": "ok"}


async def run_benchmark():
    import httpx

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Warmup
        for _ in range(50):
            await client.get("/")

        # Benchmark: simple route
        n = 2000
        start = time.perf_counter()
        for _ in range(n):
            await client.get("/")
        elapsed = time.perf_counter() - start
        print(f"GET /                    : {n/elapsed:.0f} req/s ({elapsed*1000/n:.2f} ms/req)")

        # Benchmark: path param
        start = time.perf_counter()
        for _ in range(n):
            await client.get("/items/42")
        elapsed = time.perf_counter() - start
        print(f"GET /items/42            : {n/elapsed:.0f} req/s ({elapsed*1000/n:.2f} ms/req)")

        # Benchmark: query param
        start = time.perf_counter()
        for _ in range(n):
            await client.get("/search?q=hello")
        elapsed = time.perf_counter() - start
        print(f"GET /search?q=hello       : {n/elapsed:.0f} req/s ({elapsed*1000/n:.2f} ms/req)")

        # Benchmark: POST with body
        start = time.perf_counter()
        for _ in range(n // 2):
            await client.post("/items", json={"name": "test", "price": 9.99})
        elapsed = time.perf_counter() - start
        print(f"POST /items (with model)  : {(n//2)/elapsed:.0f} req/s ({elapsed*1000/(n//2):.2f} ms/req)")

        # Benchmark: deep route (trie perf test)
        start = time.perf_counter()
        for _ in range(n):
            await client.get("/api/v50")
        elapsed = time.perf_counter() - start
        print(f"GET /api/v50 (100 routes) : {n/elapsed:.0f} req/s ({elapsed*1000/n:.2f} ms/req)")


asyncio.run(run_benchmark())
