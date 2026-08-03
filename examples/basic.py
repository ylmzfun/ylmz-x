"""
Example: Full-featured ylmz application showcasing advanced features.

Run with: uvicorn examples.basic:app --reload
"""

import asyncio
from datetime import datetime
from enum import Enum
from typing import Optional

from ylmz import (
    Ylmz, BaseModel, Field, validator, Depends,
    JSONResponse, PlainTextResponse, StreamingResponse,
    HTTPException, Router, Path, Query, Body, Header,
    BackgroundTasks, status, setup_docs,
)

app = Ylmz(title="ylmz 2.0 API", debug=True)

# ── Setup OpenAPI docs ──────────────────────────────────────

setup_docs(app)  # Adds /docs, /redoc, /openapi.json

# ── Lifespan events ─────────────────────────────────────────


@app.on_event("startup")
async def startup():
    app.state["started_at"] = datetime.now().isoformat()


@app.on_event("shutdown")
async def shutdown():
    print("Shutting down...")

# ── Models ──────────────────────────────────────────────────


class Category(str, Enum):
    ELECTRONICS = "electronics"
    BOOKS = "books"
    CLOTHING = "clothing"


class Item(BaseModel):
    name: str = Field(description="Item name", min_length=1, max_length=100)
    price: float = Field(ge=0, description="Price in USD")
    category: Category
    in_stock: bool = True
    tags: Optional[list[str]] = None

    @validator("name")
    def normalize_name(cls, v):
        return v.strip()


class ItemResponse(BaseModel):
    id: int
    item: Item
    created_at: datetime


# ── Dependencies ────────────────────────────────────────────

_items_store: dict[int, Item] = {}
_next_id = 1


async def get_item_store():
    """Dependency that provides access to the item store."""
    return _items_store


def get_next_id():
    """Sync dependency for ID generation (will be cached)."""
    global _next_id
    nid = _next_id
    _next_id += 1
    return nid


# ── Routes ──────────────────────────────────────────────────


@app.get("/")
async def root(background_tasks: BackgroundTasks):
    """Welcome endpoint with background task demo."""
    async def log_visit():
        pass  # Simulated logging

    background_tasks.add_task(log_visit)
    return {
        "app": app.title,
        "version": "0.2.0",
        "started_at": app.state.get("started_at"),
    }


@app.get("/items/{item_id:int}")
async def get_item(
    item_id: int = Path(description="The item ID"),
    store=Depends(get_item_store),
):
    """Get a single item by ID."""
    if item_id not in store:
        raise HTTPException(status.NOT_FOUND, f"Item {item_id} not found")
    item = store[item_id]
    return {"id": item_id, **item.model_dump()}


@app.get("/items")
async def list_items(
    category: Optional[str] = Query(default=None, description="Filter by category"),
    store=Depends(get_item_store),
):
    """List items, optionally filtered by category."""
    result = []
    for k, v in store.items():
        if category and v.category.value != category:
            continue
        result.append({"id": k, **v.model_dump()})
    return result


@app.post("/items", status_code=status.CREATED)
async def create_item(
    item: Item = Body(description="Item to create"),
    store=Depends(get_item_store),
    item_id=Depends(get_next_id),
):
    """Create a new item."""
    store[item_id] = item
    return ItemResponse(id=item_id, item=item, created_at=datetime.now()).model_dump()


@app.put("/items/{item_id:int}")
async def update_item(
    item_id: int,
    item: Item,
    store=Depends(get_item_store),
):
    """Update an existing item."""
    if item_id not in store:
        raise HTTPException(status.NOT_FOUND, "Item not found")
    store[item_id] = item
    return {"id": item_id, **item.model_dump()}


@app.delete("/items/{item_id:int}", status_code=status.NO_CONTENT)
async def delete_item(
    item_id: int,
    store=Depends(get_item_store),
):
    """Delete an item."""
    if item_id not in store:
        raise HTTPException(status.NOT_FOUND, "Item not found")
    del store[item_id]
    return PlainTextResponse("", status_code=204)


# ── Headers / Cookies ───────────────────────────────────────


@app.get("/whoami")
async def whoami(
    user_agent: str = Header(default="unknown"),
    x_request_id: str = Header(default="", alias="x-request-id"),
):
    """Echo request headers."""
    return {"user_agent": user_agent, "request_id": x_request_id}


# ── Streaming ───────────────────────────────────────────────


@app.get("/stream")
async def stream_numbers():
    """Stream numbers as SSE."""
    async def numbers():
        for i in range(5):
            yield f"data: {i}\n\n"
            await asyncio.sleep(0.3)

    return StreamingResponse(numbers(), media_type="text/event-stream")


# ── Custom Exception Handler ────────────────────────────────

class ValidationFailed(Exception):
    pass


@app.exception_handler(ValidationFailed)
async def validation_handler(request, exc):
    return JSONResponse(
        {"error": "validation_failed", "detail": str(exc)},
        status_code=status.BAD_REQUEST,
    )


@app.get("/validate")
async def trigger_validation():
    """Trigger a custom exception handler."""
    raise ValidationFailed("Something went wrong")


# ── Sub Router ──────────────────────────────────────────────

admin = Router(prefix="/admin")


@admin.get("/health")
async def health_check():
    return {"status": "healthy", "items_count": len(_items_store)}


@admin.get("/config")
async def admin_config():
    return {"debug": app.debug, "title": app.title}


app.include_router(admin)


# ── WebSocket ───────────────────────────────────────────────


@app.websocket("/ws")
async def websocket_endpoint(ws):
    """Simple echo WebSocket."""
    await ws.accept()
    try:
        while True:
            message = await ws.receive()
            if message["type"] == "websocket.disconnect":
                break
            if "text" in message:
                await ws.send_text(f"Echo: {message['text']}")
    except Exception:
        pass
