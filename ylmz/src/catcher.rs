use crate::response::Response;
use crate::status::Status;

/// Error catcher — handles HTTP error responses for specific status codes
pub struct Catcher {
    pub code: u16,
    pub handler: Box<dyn Fn(&Status) -> Response + Send + Sync>,
}

impl Catcher {
    pub fn new(
        code: u16,
        handler: Box<dyn Fn(&Status) -> Response + Send + Sync>,
    ) -> Self {
        Catcher { code, handler }
    }

    pub fn handle(&self, status: &Status) -> Response {
        (self.handler)(status)
    }
}

/// Collection of error catchers
#[derive(Default)]
pub struct Catchers {
    catchers: Vec<Catcher>,
    default_handler: Option<Box<dyn Fn(&Status) -> Response + Send + Sync>>,
}

impl Catchers {
    pub fn new() -> Self {
        Catchers {
            catchers: vec![],
            default_handler: Some(Box::new(|s| {
                Response::with_status(*s, format!("{} {}", s.code(), status_reason(s.code())))
            })),
        }
    }

    pub fn add(&mut self, catcher: Catcher) {
        self.catchers.push(catcher);
    }

    /// Set a custom default handler for unregistered status codes
    pub fn set_default(
        &mut self,
        handler: Box<dyn Fn(&Status) -> Response + Send + Sync>,
    ) {
        self.default_handler = Some(handler);
    }

    /// Handle a status code — finds a matching catcher or uses the default
    pub fn handle(&self, status: Status) -> Response {
        for catcher in &self.catchers {
            if catcher.code == status.code() {
                return catcher.handle(&status);
            }
        }
        if let Some(ref handler) = self.default_handler {
            handler(&status)
        } else {
            Response::with_status(status, format!("{} {}", status.code(), status_reason(status.code())))
        }
    }
}

fn status_reason(code: u16) -> &'static str {
    match code {
        200 => "OK",
        201 => "Created",
        204 => "No Content",
        301 => "Moved Permanently",
        302 => "Found",
        304 => "Not Modified",
        400 => "Bad Request",
        401 => "Unauthorized",
        403 => "Forbidden",
        404 => "Not Found",
        405 => "Method Not Allowed",
        409 => "Conflict",
        422 => "Unprocessable Entity",
        500 => "Internal Server Error",
        501 => "Not Implemented",
        502 => "Bad Gateway",
        503 => "Service Unavailable",
        _ => "Unknown",
    }
}

/// Macro to create catchers from catcher functions tagged with `#[catch]`
#[macro_export]
macro_rules! catchers {
    ($($catcher:ident),* $(,)?) => {{
        let mut cats = $crate::catcher::Catchers::new();
        $(
            cats.add($crate::paste::paste! { [<_ylmz_catcher_ $catcher>]() });
        )*
        cats
    }};
}
