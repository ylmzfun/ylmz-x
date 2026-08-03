fn main {
  let app = @lib.Engine::new()
  app.add_middleware(@lib.logger())
  app.add_middleware(@lib.recovery())

  app.get("/ping", fn(ctx) { ctx.json(200, "{\"message\":\"pong\"}") })
  app.get("/hello", fn(ctx) { ctx.string(200, "Hello, MoonBit!") })
  app.get("/hello/:name", fn(ctx) {
    match ctx.param("name") {
      Some(n) => ctx.string(200, "Hello, " + n + "!")
      None => ctx.bad_request("{\"error\":\"missing name\"}")
    }
  })
  app.post("/echo", fn(ctx) { ctx.string(200, ctx.body_string()) })
  app.get("/query", fn(ctx) {
    let n = ctx.default_query("name", "World")
    ctx.string(200, "Query says: " + n)
  })

  let api = app.group("/api/v1", [fn(ctx) { ctx.set_kv("api_version", "v1").next() }])
  api.get("/users", fn(ctx) {
    ctx.json(200, "[{\"id\":1,\"name\":\"Alice\"},{\"id\":2,\"name\":\"Bob\"}]")
  })
  api.get("/users/:id", fn(ctx) {
    match ctx.param("id") {
      Some(id) => ctx.json(200, "{\"id\":\{id},\"name\":\"User-\{id}\"}")
      None => ctx.not_found("{\"error\":\"user not found\"}")
    }
  })
  api.post("/users", fn(ctx) {
    ctx.json(201, "{\"message\":\"created\",\"data\":" + ctx.body_string() + "}")
  })

  let admin = app.group("/admin", [fn(ctx) {
    match ctx.get_header("X-Admin-Token") {
      Some("secret-admin-token") => ctx.next()
      Some(_) => ctx.forbidden("{\"error\":\"invalid admin token\"}")
      None => ctx.unauthorized("{\"error\":\"admin token required\"}")
    }
  }])
  admin.get("/dashboard", fn(ctx) {
    ctx.json(200, "{\"status\":\"ok\",\"users\":42,\"uptime\":\"72h\"}")
  })

  app.get("/static/*filepath", fn(ctx) {
    match ctx.param("filepath") {
      Some(fp) => ctx.string(200, "Serving: " + fp)
      None => ctx.not_found("{\"error\":\"file not found\"}")
    }
  })

  println("")
  println("╔══════════════════════════════════════╗")
  println("║   ylmz_gin — Gin-like Web Framework ║")
  println("║   for MoonBit                       ║")
  println("╚══════════════════════════════════════╝")
  app.run(":8080")

  println("")
  println("─── Test Requests ───────────────────────")
  let hdrs : Map[String, String] = Map([])

  let r1 = app.serve_http("GET", "/ping", "", hdrs, "")
  println("GET /ping → \{r1.status} \{r1.body}")

  let r2 = app.serve_http("GET", "/hello/ylmz", "", hdrs, "")
  println("GET /hello/ylmz → \{r2.status} \{r2.body}")

  let r3 = app.serve_http("GET", "/api/v1/users", "", hdrs, "")
  println("GET /api/v1/users → \{r3.status} \{r3.body}")

  let r4 = app.serve_http("POST", "/echo", "", hdrs, "Hello!")
  println("POST /echo → \{r4.status} \{r4.body}")

  let r5 = app.serve_http("GET", "/api/v1/users/42", "", hdrs, "")
  println("GET /api/v1/users/42 → \{r5.status} \{r5.body}")

  let r6 = app.serve_http("GET", "/static/css/style.css", "", hdrs, "")
  println("GET /static/css/style.css → \{r6.status} \{r6.body}")

  let r7 = app.serve_http("GET", "/nonexistent", "", hdrs, "")
  println("GET /nonexistent → \{r7.status} \{r7.body}")

  println("")
  println("✅ All tests completed!")
}
