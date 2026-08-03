
pub struct RouterGroup { base_path : String; router : Router; handlers : Array[(Context) -> Context] }

pub fn Engine::group(self : Engine, rel : String, grp : Array[(Context) -> Context]) -> RouterGroup {
  let merged : Array[(Context) -> Context] = []
  for x in self.middleware { merged.push(x) }
  for x in grp { merged.push(x) }
  { base_path: _join("", rel), router: self.router, handlers: merged }
}

pub fn RouterGroup::get(self : RouterGroup, path : String, h : HandlerFunc) -> Unit {
  let full = _join(self.base_path, path)
  let chain : Array[(Context) -> Context] = []
  for x in self.handlers { chain.push(x) }
  chain.push(h)
  self.router.add_route("GET", full, chain)
}
pub fn RouterGroup::post(self : RouterGroup, path : String, h : HandlerFunc) -> Unit {
  let full = _join(self.base_path, path)
  let chain : Array[(Context) -> Context] = []
  for x in self.handlers { chain.push(x) }
  chain.push(h)
  self.router.add_route("POST", full, chain)
}
pub fn RouterGroup::put(self : RouterGroup, path : String, h : HandlerFunc) -> Unit {
  let full = _join(self.base_path, path)
  let chain : Array[(Context) -> Context] = []
  for x in self.handlers { chain.push(x) }
  chain.push(h)
  self.router.add_route("PUT", full, chain)
}
pub fn RouterGroup::delete(self : RouterGroup, path : String, h : HandlerFunc) -> Unit {
  let full = _join(self.base_path, path)
  let chain : Array[(Context) -> Context] = []
  for x in self.handlers { chain.push(x) }
  chain.push(h)
  self.router.add_route("DELETE", full, chain)
}

pub fn Engine::run(_self : Engine, addr : String) -> Unit {
  println("🚀 ylmz_gin server on \{addr}")
}

pub fn Engine::serve_http(
  self : Engine, m : String, path : String,
  query : String, headers : Map[String, String], body : String
) -> ResponseWriter {
  let w = ResponseWriter::new()
  let req = { http_method: m, path: path, query: query, headers: headers, body: body }
  let (handlers, params) = self.router.find(m, path)
  match handlers {
    Some(chain) => {
      let ctx = Context::new(req, w, chain).set_params(params).next()
      ctx.writer
    }
    None => {
      if self.router.has_method(m) {
        let h = w.headers; h.set("Content-Type", "application/json; charset=utf-8")
        { status: StatusNotFound, headers: h, body: "{\"error\":\"not found\"}", written: true }
      } else {
        let h = w.headers; h.set("Content-Type", "application/json; charset=utf-8")
        { status: StatusMethodNotAllowed, headers: h, body: "{\"error\":\"method not allowed\"}", written: true }
      }
    }
  }
}

fn _join(base : String, rel : String) -> String {
  if base == "" || base == "/" { return rel }
  if rel == "/" { return base }
  if rel == "" { return base }
  base + rel
}
