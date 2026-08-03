pub fn Context::new(req : Request, w : ResponseWriter, h : Array[(Context) -> Context]) -> Context {
  { request: req, writer: w, params: Params([]), handlers: h,
    index: -1, keys: {}, aborted: false, errors: [] }
}

fn _idx(c : Context, v : Int) -> Context {
  { request: c.request, writer: c.writer, params: c.params,
    handlers: c.handlers, index: v, keys: c.keys,
    aborted: c.aborted, errors: c.errors }
}
fn _abort(c : Context) -> Context {
  { request: c.request, writer: c.writer, params: c.params,
    handlers: c.handlers, index: c.index, keys: c.keys,
    aborted: true, errors: c.errors }
}
fn _wr(c : Context, w : ResponseWriter) -> Context {
  { request: c.request, writer: w, params: c.params,
    handlers: c.handlers, index: c.index, keys: c.keys,
    aborted: c.aborted, errors: c.errors }
}

// ─── Chain execution ─────────────────────────────────────────────────────

pub fn Context::next(self : Context) -> Context {
  let mut cur = _idx(self, self.index + 1)
  let len = cur.handlers.length()
  while cur.index < len && !(cur.aborted) {
    cur = cur.handlers[cur.index](cur)
    cur = _idx(cur, cur.index + 1)
  }
  cur
}

// ─── Accessors ───────────────────────────────────────────────────────────

pub fn Context::http_method(self : Context) -> String { self.request.http_method }
pub fn Context::path(self : Context) -> String { self.request.path }
pub fn Context::is_aborted(self : Context) -> Bool { self.aborted }
pub fn Context::param(self : Context, key : String) -> String? { self.params.get(key) }
pub fn Context::get_header(self : Context, key : String) -> String? { self.request.headers.get(key) }
pub fn Context::client_ip(self : Context) -> String {
  match self.request.headers.get("X-Forwarded-For") {
    Some(ip) => ip
    None => match self.request.headers.get("X-Real-Ip") {
      Some(ip) => ip; None => "127.0.0.1"
    }
  }
}
pub fn Context::default_query(self : Context, key : String, def : String) -> String {
  let q = self.request.query
  if q == "" { return def }
  let pairs = q.split("&").to_array()
  for i = 0; i < pairs.length(); i = i + 1 {
    let kv = pairs[i].split("=").to_array()
    if kv.length() == 2 && kv[0] == key { return kv[1].to_owned() }
  }
  def
}
pub fn Context::set_params(self : Context, p : Params) -> Context {
  { request: self.request, writer: self.writer, params: p,
    handlers: self.handlers, index: self.index, keys: self.keys,
    aborted: self.aborted, errors: self.errors }
}
pub fn Context::set_kv(self : Context, key : String, value : String) -> Context {
  self.keys.set(key, value); self
}
pub fn Context::get_val(self : Context, key : String) -> String? { self.keys.get(key) }
pub fn Context::body_string(self : Context) -> String { self.request.body }
pub fn Context::bind_json(self : Context) -> String? {
  if self.request.body == "" { None } else { Some(self.request.body) }
}

// ─── Response rendering ──────────────────────────────────────────────────

pub fn Context::string(self : Context, code : Int, body : String) -> Context {
  let h = self.writer.headers; h.set("Content-Type", "text/plain; charset=utf-8")
  _abort(_wr(self, { status: code, headers: h, body: body, written: true }))
}
pub fn Context::json(self : Context, code : Int, body : String) -> Context {
  let h = self.writer.headers; h.set("Content-Type", "application/json; charset=utf-8")
  _abort(_wr(self, { status: code, headers: h, body: body, written: true }))
}
pub fn Context::html(self : Context, code : Int, body : String) -> Context {
  let h = self.writer.headers; h.set("Content-Type", "text/html; charset=utf-8")
  _abort(_wr(self, { status: code, headers: h, body: body, written: true }))
}
pub fn Context::ok(self : Context, body : String) -> Context { self.string(StatusOK, body) }
pub fn Context::created(self : Context, body : String) -> Context { self.string(StatusCreated, body) }
pub fn Context::no_content(self : Context) -> Context { _abort(self) }
pub fn Context::bad_request(self : Context, body : String) -> Context { self.string(StatusBadRequest, body) }
pub fn Context::unauthorized(self : Context, body : String) -> Context {
  let h = self.writer.headers
  h.set("WWW-Authenticate", "Basic realm=\"Restricted\"")
  h.set("Content-Type", "application/json; charset=utf-8")
  _abort(_wr(self, { status: StatusUnauthorized, headers: h, body: body, written: true }))
}
pub fn Context::forbidden(self : Context, body : String) -> Context { self.string(StatusForbidden, body) }
pub fn Context::not_found(self : Context, body : String) -> Context { self.string(StatusNotFound, body) }
pub fn Context::internal_error(self : Context, body : String) -> Context { self.string(StatusInternalServerError, body) }
pub fn Context::add_error(self : Context, err : String) -> Context { self.errors.push(err); self }
pub fn Context::has_errors(self : Context) -> Bool { self.errors.length() > 0 }
