use std::collections::HashMap;

use crate::method::Method;
use crate::request::Request;
use crate::response::Response;
use crate::state::StateContainer;

/// A parsed path segment in a route pattern
#[derive(Debug, Clone, PartialEq)]
enum Segment {
    /// A literal path segment (e.g., "hello")
    Literal(String),
    /// A dynamic path parameter (e.g., `<name>`)
    Param(String),
}

/// A parsed route path pattern
#[derive(Debug, Clone)]
pub(crate) struct PathPattern {
    segments: Vec<Segment>,
}

impl PathPattern {
    /// Parse a path pattern like "/hello/<name>/<id>" into segments
    fn parse(pattern: &str) -> Self {
        let segments = pattern
            .split('/')
            .filter(|s| !s.is_empty())
            .map(|seg| {
                if seg.starts_with('<') && seg.ends_with('>') {
                    let name = &seg[1..seg.len() - 1];
                    Segment::Param(name.to_string())
                } else {
                    Segment::Literal(seg.to_string())
                }
            })
            .collect();

        PathPattern { segments }
    }

    /// Try to match an incoming path against this pattern.
    /// Returns Some(HashMap) with extracted params if matched, None otherwise.
    fn matches(&self, path: &str) -> Option<HashMap<String, String>> {
        let incoming: Vec<&str> = path.split('/').filter(|s| !s.is_empty()).collect();

        if incoming.len() != self.segments.len() {
            return None;
        }

        let mut params = HashMap::new();

        for (seg, inc) in self.segments.iter().zip(incoming.iter()) {
            match seg {
                Segment::Literal(lit) => {
                    if lit != inc {
                        return None;
                    }
                }
                Segment::Param(name) => {
                    params.insert(name.clone(), inc.to_string());
                }
            }
        }

        Some(params)
    }
}

/// A single route definition
pub struct Route {
    pub method: Method,
    pub path: String,
    pub(crate) pattern: PathPattern,
    /// Handler: receives request and state, returns a Response
    pub handler: Box<dyn Fn(&mut Request, &StateContainer) -> crate::Result<Response> + Send + Sync>,
}

impl Route {
    pub fn new(
        method: Method,
        path: impl Into<String>,
        handler: Box<dyn Fn(&mut Request, &StateContainer) -> crate::Result<Response> + Send + Sync>,
    ) -> Self {
        let path_str = path.into();
        let pattern = PathPattern::parse(&path_str);
        Route {
            method,
            path: path_str,
            pattern,
            handler,
        }
    }
}

impl std::fmt::Debug for Route {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Route")
            .field("method", &self.method)
            .field("path", &self.path)
            .finish()
    }
}

/// Collection of routes organized by path prefix
pub struct Router {
    routes: Vec<Route>,
}

impl Router {
    pub fn new() -> Self {
        Router { routes: vec![] }
    }

    /// Add a route to the router
    pub fn add(&mut self, route: Route) {
        self.routes.push(route);
    }

    /// Merge another router's routes into this one
    pub fn merge(&mut self, other: Router) {
        self.routes.extend(other.routes);
    }

    /// Try to dispatch a request to a matching handler
    pub fn dispatch(&self, req: &mut Request, state: &StateContainer) -> crate::Result<Response> {
        let method = req.method();
        let path = req.path();

        for route in &self.routes {
            if route.method != method {
                continue;
            }

            if let Some(params) = route.pattern.matches(path) {
                for (k, v) in params {
                    req.set_path_param(k, v);
                }
                return (route.handler)(req, state);
            }
        }

        Err(crate::Error::Status(crate::status::Status::NOT_FOUND))
    }
}

/// Macro to create a vector of routes from handler functions tagged with route attributes
///
/// Each handler function produces a hidden `_ylmz_route_<name>` function that returns a `Route`.
/// This macro calls those functions and collects the routes.
#[macro_export]
macro_rules! routes {
    ($($route:ident),* $(,)?) => {{
        let mut router = $crate::route::Router::new();
        $(
            router.add($crate::paste::paste! { [<_ylmz_route_ $route>]() });
        )*
        router
    }};
}
