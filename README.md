# ylmz 🚀

A lightweight, Rocket-inspired web framework for Rust — designed to be **concise yet comprehensive**.

## Features

- **Declarative routing** — `#[get("/hello/<name>")]` with path parameters
- **Type-safe extractors** — `Json<T>`, `Query<T>`, `State<T>`, path params
- **JSON support** — request/response via `serde_json`
- **Managed state** — thread-safe application state via `App::manage()`
- **Middleware (Fairings)** — hook into request/response lifecycle
- **Error catchers** — `#[catch(404)]` for custom error pages
- **Flexible responses** — return `&str`, `String`, `Json<T>`, `(Status, &str)`, `Option<T>`, `Result<T, E>`, etc.

## Quick Start

```rust
use ylmz::prelude::*;
use serde::Deserialize;

#[get("/")]
fn index() -> &'static str {
    "Hello, world!"
}

#[get("/hello/<name>")]
fn hello(name: String) -> String {
    format!("Hello, {}!", name)
}

#[derive(Deserialize)]
struct SearchParams {
    q: String,
    page: Option<u32>,
}

#[get("/search")]
fn search(query: Query<SearchParams>) -> String {
    let p = query.into_inner();
    format!("Searching '{}' page {}", p.q, p.page.unwrap_or(1))
}

#[catch(404)]
fn not_found() -> (Status, String) {
    (Status::NOT_FOUND, "Page not found".into())
}

fn main() -> ylmz::Result<()> {
    App::new()
        .attach(Logger)
        .register("/", catchers![not_found])
        .mount("/", routes![index, hello, search])
        .launch()
}
```

## Route Macros

| Macro | HTTP Method | Example |
|-------|-------------|---------|
| `#[get("/path")]` | GET | `#[get("/user/<id>")]` |
| `#[post("/path", data = "<body>")]` | POST | `#[post("/users", data = "<user>")]` |
| `#[put("/path/<id>", data = "<body>")]` | PUT | Full update |
| `#[delete("/path/<id>")]` | DELETE | Resource deletion |
| `#[patch("/path/<id>", data = "<body>")]` | PATCH | Partial update |
| `#[catch(404)]` | — | Error handler |

### Path Parameters

Path segments wrapped in `<>` are extracted and passed to the handler **positionally**:

```rust
#[get("/user/<name>/posts/<id>")]
fn user_posts(name: String, id: u32) -> String { ... }
```

### Request Body (JSON)

Use `data = "<param>"` to bind the request body to a `Json<T>` parameter:

```rust
#[post("/users", data = "<user>")]
fn create_user(user: Json<User>) -> Json<User> { ... }
```

### Query Parameters

Use `Query<T>` where `T: Deserialize`:

```rust
#[get("/search")]
fn search(query: Query<SearchParams>) -> String { ... }
```

### Managed State

```rust
#[derive(Default)]
struct Counter { count: AtomicU64 }

App::new()
    .manage(Counter::default())
    .mount("/", routes![counter])
    .launch()

#[get("/counter")]
fn counter(state: State<Counter>) -> String { ... }
```

## Responder Types

The following types implement `Responder` out of the box:

| Type | Behavior |
|------|----------|
| `&str` / `String` | 200 OK, text/plain |
| `(Status, &str)` / `(Status, String)` | Custom status + body |
| `Json<T: Serialize>` | 200 OK, application/json |
| `Option<T: Responder>` | `Some(T)` or 404 |
| `Result<T: Responder, E: Display>` | `Ok(T)` or 500 |
| `Status` | Status code with default reason |
| `()` | 204 No Content |

## Fairings (Middleware)

Implement `Fairing` to hook into the request/response lifecycle:

```rust
pub trait Fairing: Send + Sync {
    fn on_request(&self, req: &Request) -> Option<Response> { None }
    fn on_response(&self, req: &Request, res: &mut Response) {}
}
```

Built-in: `Logger` — logs every request with method, path, and status code.

## Error Catchers

```rust
#[catch(404)]
fn not_found() -> (Status, String) {
    (Status::NOT_FOUND, r#"{"error":"Not Found"}"#.into())
}

App::new()
    .register("/", catchers![not_found])
    .launch()
```

## Configuration

```rust
App::new()
    .configure(Config::new().address("0.0.0.0").port(3000))
    .launch()
```

## Project Structure

```
ylmz-rust/
├── Cargo.toml            # workspace
├── ylmz/                 # core framework crate
│   └── src/
│       ├── app.rs        # App builder + HTTP server (hyper + tokio)
│       ├── route.rs      # Router + path matching
│       ├── request.rs    # Request (lazy body caching)
│       ├── response.rs   # Response + Responder trait
│       ├── extractor.rs  # FromRequest, Json, Query, State
│       ├── catcher.rs    # Error catchers
│       ├── fairing.rs    # Middleware hooks
│       ├── state.rs      # StateContainer + State<T>
│       ├── config.rs     # Configuration
│       └── ...
├── ylmz-macros/          # proc-macro crate
│   └── src/lib.rs        # #[get] #[post] #[put] #[delete] #[patch] #[catch]
└── examples/hello/       # demo application
    └── src/main.rs
```

## License

MIT
