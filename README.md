# ylmz_gin

A Gin-like web framework for [MoonBit](https://www.moonbitlang.com/).

## Features

- **Routing** — `GET`, `POST`, `PUT`, `DELETE`, `PATCH` with `:param` and `*wildcard` support
- **Route Groups** — shared path prefix and middleware stack
- **Middleware** — global & group-level chains, `ctx.next()` to pass control
- **Context** — functional style, each handler returns a new Context
- **Rendering** — `json`, `string`, `html` response helpers
- **Built-in middleware** — Logger, Recovery, CORS, BasicAuth, NoCache, RequestID

## Quick Start

```moonbit
// cmd/main/main.mbt
fn main {
  let app = @lib.Engine::new()
  app.add_middleware(@lib.logger())

  app.get("/ping", fn(ctx) { ctx.json(200, "{\"message\":\"pong\"}") })

  app.get("/hello/:name", fn(ctx) {
    match ctx.param("name") {
      Some(n) => ctx.string(200, "Hello, " + n + "!")
      None => ctx.bad_request("{\"error\":\"missing name\"}")
    }
  })

  // Route group with auth
  let api = app.group("/api/v1", [
    fn(ctx) {
      match ctx.get_header("Authorization") {
        Some("Bearer secret") => ctx.next()
        _ => ctx.unauthorized("{\"error\":\"unauthorized\"}")
      }
    },
  ])
  api.get("/users", fn(ctx) { ctx.json(200, "[{\"id\":1,\"name\":\"Alice\"}]") })

  app.run(":8080")
}
```

```bash
moon run cmd/main
```

## Project Structure

```
.
├── moon.mod.json          # Project manifest
├── moon.pkg               # Root package marker
├── types.mbt              # Constants, core types
├── context.mbt            # Context methods
├── router.mbt             # Route matching engine
├── engine.mbt             # Engine + RouterGroup
├── middleware.mbt         # Built-in middleware
└── cmd/main/
    ├── moon.pkg           # Entry point config
    └── main.mbt           # Your application
```

## API Overview

### Engine

| Method | Description |
|--------|-------------|
| `Engine::new()` | Create a new engine |
| `app.get(path, handler)` | Register GET route |
| `app.post(path, handler)` | Register POST route |
| `app.put(path, handler)` | Register PUT route |
| `app.delete(path, handler)` | Register DELETE route |
| `app.patch(path, handler)` | Register PATCH route |
| `app.group(prefix, [middleware])` | Create a RouterGroup |
| `app.add_middleware(handler)` | Add global middleware |
| `app.run(addr)` | Start the server |
| `app.serve_http(method, path, query, headers, body)` | Handle single HTTP request |

### Context

| Method | Description |
|--------|-------------|
| `ctx.next()` | Continue to the next handler |
| `ctx.json(code, body)` | Send JSON response |
| `ctx.string(code, body)` | Send text response |
| `ctx.html(code, body)` | Send HTML response |
| `ctx.param(key)` | Get path parameter (`:id`) |
| `ctx.default_query(key, default)` | Get query parameter |
| `ctx.get_header(key)` | Get request header |
| `ctx.set_kv(key, value)` | Store value in context |
| `ctx.get_val(key)` | Retrieve stored value |
| `ctx.body_string()` | Get request body |
| `ctx.ok(body)` | 200 shortcut |
| `ctx.bad_request(body)` | 400 shortcut |
| `ctx.unauthorized(body)` | 401 shortcut |
| `ctx.forbidden(body)` | 403 shortcut |
| `ctx.not_found(body)` | 404 shortcut |

### Built-in Middleware

```moonbit
app.add_middleware(@lib.logger())       // request logging
app.add_middleware(@lib.recovery())     // panic recovery
app.add_middleware(@lib.cors())         // CORS headers
app.add_middleware(@lib.no_cache())     // cache-control headers
app.add_middleware(@lib.request_id())   // X-Request-ID header
```

## Route Patterns

| Pattern | Matches | Example |
|---------|---------|---------|
| `/ping` | Exact | `/ping` |
| `/user/:name` | Named param | `/user/alice` → `param("name") == "alice"` |
| `/static/*filepath` | Catch-all | `/static/css/app.css` → `param("filepath") == "css/app.css"` |

## License

MIT
