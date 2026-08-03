# ylmz

> A lightweight, zero-dependency ASGI web framework kernel — FastAPI-like API, minimal footprint.

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

**ylmz** is a pure-Python ASGI web framework that delivers the developer experience of FastAPI — type-safe request/response handling, automatic OpenAPI docs, dependency injection, and rich data validation — all without mandatory third-party dependencies.

---

## ✨ Features

| Category | Highlights |
|---|---|
| **Routing** | `@app.get/post/put/delete/patch/websocket` — path params `{id}` with type coercion `{id:int}` |
| **Type System** | `BaseModel` with `Field(ge/le/gt/lt/min_length/max_length/pattern/alias)`, `@validator`, `model_dump[_json]`, `model_validate` |
| **Rich Types** | `str` `int` `float` `bool` `Decimal` `datetime` `date` `time` `UUID` `Enum` `Optional[T]` `Union[A,B]` `list[T]` `dict[K,V]` nested models |
| **Dependency Injection** | `Depends()` with automatic sub-dependency resolution and per-request caching |
| **Parameter Descriptors** | `Path()` `Query()` `Body()` `Header()` `Cookie()` — explicit source + constraints |
| **Background Tasks** | `BackgroundTasks.add_task()` — fire-and-forget after response |
| **Lifespan** | `@app.on_event("startup"/"shutdown")` + `app.state` |
| **Middleware** | Class-based middleware chain + built-in `cors_middleware_factory()` |
| **Exception Handling** | `HTTPException`, custom `@app.exception_handler()` |
| **OpenAPI Docs** | `setup_docs(app)` → auto-generated `/docs` (Swagger) + `/redoc` |
| **WebSocket** | Native `WebSocket` with `send_text/send_json/send_bytes/receive/close` |
| **File Upload** | `UploadFile` with `read()` / `save()` |
| **Status Codes** | `status.OK`, `status.CREATED`, `status.NOT_FOUND` … — named constants |
| **Zero Deps** | Core framework has zero mandatory dependencies — just `uvicorn` to run |

---

## 🚀 Quick Start

### Installation

```bash
pip install -e .            # framework only
pip install -e ".[dev]"     # + uvicorn, pytest, httpx
```

### Hello World

```python
from ylmz import Ylmz

app = Ylmz()

@app.get("/")
async def root():
    return {"hello": "world"}
```

```bash
PYTHONPATH=. uvicorn hello:app --reload
```

Open `http://localhost:8000/docs` for interactive Swagger UI.

---

## 📖 Usage Guide

### Routing

```python
@app.get("/items/{item_id:int}")
async def get_item(item_id: int):
    return {"item_id": item_id}

@app.get("/search")
async def search(q: str = "", page: int = 1):
    return {"q": q, "page": page}
```

### Data Models

```python
from enum import Enum
from datetime import datetime
from ylmz import BaseModel, Field, validator

class Category(str, Enum):
    ELECTRONICS = "electronics"
    BOOKS = "books"

class Item(BaseModel):
    name: str = Field(min_length=1, max_length=100, description="Item name")
    price: float = Field(ge=0)
    category: Category
    tags: list[str] | None = None
    created_at: datetime | None = None

    @validator("name")
    def normalize(cls, v):
        return v.strip()

# Automatic validation
item = Item(name="  Widget  ", price=9.99, category="electronics")
assert item.name == "Widget"
print(item.model_dump_json())  # → JSON string
```

### POST with Body

```python
@app.post("/items", status_code=201)
async def create_item(item: Item):
    # item is already validated
    return {"created": item.model_dump()}
```

### Dependency Injection

```python
from ylmz import Depends

async def get_db():
    return {"connected": True}

@app.get("/data")
async def read_data(db=Depends(get_db)):
    return {"db": db}

# Sub-dependencies work automatically:
async def get_repo(db=Depends(get_db)):
    return f"repo({db['connected']})"

@app.get("/repo")
async def read_repo(repo=Depends(get_repo)):
    return {"repo": repo}
```

### Parameter Descriptors

```python
from ylmz import Path, Query, Body, Header, Cookie

@app.get("/items/{item_id}")
async def get_item(
    item_id: int = Path(description="The item ID"),
    verbose: bool = Query(default=False),
):
    ...

@app.post("/items")
async def create(item: Item = Body(description="Item data")):
    ...

@app.get("/whoami")
async def whoami(user_agent: str = Header()):
    return {"ua": user_agent}
```

### Background Tasks

```python
from ylmz import BackgroundTasks

@app.post("/send-email")
async def send(background_tasks: BackgroundTasks):
    background_tasks.add_task(send_email_async, to="user@example.com")
    return {"queued": True}
```

### Lifespan Events

```python
@app.on_event("startup")
async def startup():
    app.state.db = await init_db()

@app.on_event("shutdown")
async def shutdown():
    await app.state.db.close()
```

### Custom Exception Handlers

```python
class RateLimitExceeded(Exception):
    pass

@app.exception_handler(RateLimitExceeded)
async def handle_rate_limit(request, exc):
    return JSONResponse(
        {"error": "rate_limited", "retry_after": 60},
        status_code=429,
    )
```

### WebSocket

```python
from ylmz import WebSocket

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    while True:
        msg = await ws.receive()
        if msg["type"] == "websocket.disconnect":
            break
        await ws.send_text(f"Echo: {msg['text']}")
```

### Sub Routers

```python
from ylmz import Router

admin = Router(prefix="/admin")

@admin.get("/health")
async def health():
    return {"status": "ok"}

app.include_router(admin)  # → /admin/health
```

### File Upload

```python
from ylmz import UploadFile

@app.post("/upload")
async def upload(file: UploadFile):
    content = await file.read()
    await file.save(f"./uploads/{file.filename}")
    return {"filename": file.filename, "size": file.size}
```

### OpenAPI Docs

```python
from ylmz import setup_docs

app = Ylmz(title="My API")
setup_docs(app)
# Now available: /docs (Swagger) /redoc /openapi.json
```

### Middleware & CORS

```python
from ylmz.middleware import cors_middleware_factory

app.add_middleware(
    cors_middleware_factory(
        allow_origins=["http://localhost:3000"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
)
```

### Status Codes

```python
from ylmz import status
raise HTTPException(status.NOT_FOUND, "Item not found")
```

---

## 📁 Project Structure

```
ylmz-python/
├── ylmz/                    # framework source (zero mandatory deps)
│   ├── app.py               # Ylmz ASGI application
│   ├── routing.py           # route matching + parameter resolution
│   ├── types.py             # BaseModel type system
│   ├── depends.py           # dependency injection
│   ├── params.py            # Path/Query/Body/Header/Cookie
│   ├── response.py          # JSON/HTML/Plain/Streaming responses
│   ├── request.py           # Request object
│   ├── middleware.py         # middleware + CORS
│   ├── background.py         # BackgroundTasks
│   ├── websocket.py         # WebSocket support
│   ├── uploads.py           # UploadFile
│   ├── exceptions.py        # HTTPException
│   ├── status.py            # named status codes
│   └── openapi.py           # OpenAPI 3.0 + Swagger/ReDoc
├── examples/
│   └── basic.py             # full-featured demo app
└── tests/                   # 88 tests across 3 files
```

---

## 🧪 Running Tests

```bash
PYTHONPATH=. python3 -m pytest tests/ -v
```

---

## 🆚 vs FastAPI

ylmz is designed as a **from-scratch alternative** to FastAPI with zero mandatory dependencies:

| | ylmz | FastAPI |
|---|---|---|
| Core dependencies | **0** | Pydantic + Starlette |
| Framework source | ~2000 lines | ~50,000+ lines |
| Type validation | Built-in `BaseModel` | Pydantic |
| OpenAPI docs | Built-in CDN-based | Built-in |
| Startup time | **instant** | slower (heavy imports) |
| Python version | 3.9+ | 3.8+ |

---

## 📄 License

MIT
