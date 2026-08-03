struct Route {
  http_method : String
  pattern : String
  handlers : Array[(Context) -> Context]
}

pub struct Router { routes : Array[Route] }
pub fn Router::new() -> Router { { routes: [] } }

pub fn Router::add_route(self : Router, http_method : String, pattern : String, handlers : Array[(Context) -> Context]) -> Unit {
  self.routes.push({ http_method: http_method, pattern: pattern, handlers: handlers })
}

pub fn Router::find(self : Router, http_method : String, path : String) -> (Array[(Context) -> Context]?, Params) {
  let norm = if path != "/" && path.has_suffix("/") { path[0:path.length() - 1].to_owned() } else { path }
  for i = 0; i < self.routes.length(); i = i + 1 {
    let rt = self.routes[i]
    if rt.http_method != http_method { continue }
    let params = Params([])
    if _match(rt.pattern, norm, params) { return (Some(rt.handlers), params) }
  }
  (None, Params([]))
}

pub fn Router::has_method(self : Router, http_method : String) -> Bool {
  for i = 0; i < self.routes.length(); i = i + 1 { if self.routes[i].http_method == http_method { return true } }
  false
}

fn _match(pattern : String, path : String, params : Params) -> Bool {
  if pattern == "/" && path == "/" { return true }
  let s1 = if pattern[0] == '/' { pattern[1:].to_owned() } else { pattern }
  let s2 = if path[0] == '/' { path[1:].to_owned() } else { path }
  let ps = s1.split("/").collect()
  let pp = s2.split("/").collect()
  let pl = ps.length(); let ppl = pp.length()
  if pl == 0 && ppl == 0 { return true }
  if pl == 1 && ps[0] == "" && ppl == 1 && pp[0] == "" { return true }
  let mut pi = 0; let mut ppi = 0
  while pi < pl {
    if ppi >= ppl { return false }
    let part = ps[pi]
    if part.length() > 0 && part[0] == ':' {
      params.0.push({ key: part[1:].to_owned(), value: pp[ppi].to_owned() })
      pi = pi + 1; ppi = ppi + 1; continue
    }
    if part.length() > 0 && part[0] == '*' {
      let mut s = pp[ppi].to_owned(); let mut j = ppi + 1
      while j < ppl { s = s + "/" + pp[j].to_owned(); j = j + 1 }
      params.0.push({ key: part[1:].to_owned(), value: s }); return true
    }
    if part != pp[ppi] { return false }
    pi = pi + 1; ppi = ppi + 1
  }
  ppi == ppl
}
pub struct Engine { router : Router; middleware : Array[(Context) -> Context] }
pub fn Engine::new() -> Engine { { router: Router::new(), middleware: [] } }

pub fn Engine::get(self : Engine, path : String, h : HandlerFunc) -> Unit { self.handle("GET", path, h) }
pub fn Engine::post(self : Engine, path : String, h : HandlerFunc) -> Unit { self.handle("POST", path, h) }
pub fn Engine::put(self : Engine, path : String, h : HandlerFunc) -> Unit { self.handle("PUT", path, h) }
pub fn Engine::delete(self : Engine, path : String, h : HandlerFunc) -> Unit { self.handle("DELETE", path, h) }
pub fn Engine::patch(self : Engine, path : String, h : HandlerFunc) -> Unit { self.handle("PATCH", path, h) }

pub fn Engine::handle(self : Engine, m : String, path : String, h : HandlerFunc) -> Unit {
  let chain : Array[(Context) -> Context] = []
  for x in self.middleware { chain.push(x) }
  chain.push(h)
  self.router.add_route(m, path, chain)
}

pub fn Engine::add_middleware(self : Engine, mw : HandlerFunc) -> Unit { self.middleware.push(mw) }
