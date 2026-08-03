pub fn logger() -> HandlerFunc {
  fn(ctx : Context) -> Context {
    let lg_m = ctx.http_method(); let lg_p = ctx.path()
    let lg_ctx = ctx.next()
    println("[ylmz_gin] \{lg_m} \{lg_p}")
    lg_ctx
  }
}

pub fn recovery() -> HandlerFunc {
  fn(ctx : Context) -> Context { ctx.next() }
}

pub fn cors() -> HandlerFunc {
  fn(ctx : Context) -> Context {
    let co_h = ctx.writer.headers
    co_h.set("Access-Control-Allow-Origin", "*")
    co_h.set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, PATCH, OPTIONS")
    co_h.set("Access-Control-Allow-Headers", "Content-Type, Authorization")
    let co_w = { status: ctx.writer.status, headers: co_h, body: ctx.writer.body, written: ctx.writer.written }
    let co_ctx = { request: ctx.request, writer: co_w, params: ctx.params,
                    handlers: ctx.handlers, index: ctx.index, keys: ctx.keys,
                    aborted: ctx.aborted, errors: ctx.errors }
    if co_ctx.http_method() == "OPTIONS" { return co_ctx.no_content() }
    co_ctx.next()
  }
}

pub fn basic_auth(_u : String, _p : String) -> HandlerFunc {
  fn(ctx : Context) -> Context {
    match ctx.get_header("Authorization") {
      Some(ba_auth) => if ba_auth.length() >= 6 && ba_auth[0:6] == "Basic " { ctx.next() }
                       else { ctx.unauthorized("{\"error\":\"unauthorized\"}") }
      None => ctx.unauthorized("{\"error\":\"unauthorized\"}")
    }
  }
}

pub fn no_cache() -> HandlerFunc {
  fn(ctx : Context) -> Context {
    let nc_h = ctx.writer.headers
    nc_h.set("Cache-Control", "no-cache, no-store, must-revalidate")
    nc_h.set("Pragma", "no-cache")
    let nc_w = { status: ctx.writer.status, headers: nc_h, body: ctx.writer.body, written: ctx.writer.written }
    let nc_ctx = { request: ctx.request, writer: nc_w, params: ctx.params,
                    handlers: ctx.handlers, index: ctx.index, keys: ctx.keys,
                    aborted: ctx.aborted, errors: ctx.errors }
    nc_ctx.next()
  }
}

pub fn request_id() -> HandlerFunc {
  fn(ctx : Context) -> Context {
    match ctx.get_header("X-Request-ID") {
      Some(rid_val) => {
        let ri_h = ctx.writer.headers; ri_h.set("X-Request-ID", rid_val)
        let ri_w = { status: ctx.writer.status, headers: ri_h, body: ctx.writer.body, written: ctx.writer.written }
        let ri_ctx = { request: ctx.request, writer: ri_w, params: ctx.params,
                        handlers: ctx.handlers, index: ctx.index, keys: ctx.keys,
                        aborted: ctx.aborted, errors: ctx.errors }
        ri_ctx.set_kv("request_id", rid_val).next()
      }
      None => {
        let ri2_h = ctx.writer.headers; ri2_h.set("X-Request-ID", "req-unknown")
        let ri2_w = { status: ctx.writer.status, headers: ri2_h, body: ctx.writer.body, written: ctx.writer.written }
        let ri2_ctx = { request: ctx.request, writer: ri2_w, params: ctx.params,
                         handlers: ctx.handlers, index: ctx.index, keys: ctx.keys,
                         aborted: ctx.aborted, errors: ctx.errors }
        ri2_ctx.set_kv("request_id", "req-unknown").next()
      }
    }
  }
}
