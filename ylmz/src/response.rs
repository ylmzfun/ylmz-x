use crate::status::Status;

/// Response that can be returned from a handler
pub struct Response {
    status: Status,
    headers: http::HeaderMap,
    body: Vec<u8>,
}

impl Response {
    pub fn new(status: Status, body: Vec<u8>) -> Self {
        Response {
            status,
            headers: http::HeaderMap::new(),
            body,
        }
    }

    /// Create a response with a status and a string body
    pub fn with_status(status: Status, body: impl Into<String>) -> Self {
        let mut resp = Response::new(status, body.into().into_bytes());
        resp.set_header(http::header::CONTENT_TYPE, "text/plain; charset=utf-8");
        resp
    }

    /// Create a 200 OK response with a string body
    pub fn ok(body: impl Into<String>) -> Self {
        Self::with_status(Status::OK, body)
    }

    /// Create a 404 Not Found response
    pub fn not_found() -> Self {
        Self::with_status(Status::NOT_FOUND, "404 Not Found")
    }

    /// Set a header on the response
    pub fn set_header(
        &mut self,
        key: impl http::header::IntoHeaderName,
        value: impl AsRef<str>,
    ) {
        if let Ok(v) = http::HeaderValue::from_str(value.as_ref()) {
            self.headers.insert(key, v);
        }
    }

    /// Set content type
    pub fn content_type(mut self, ct: &str) -> Self {
        self.set_header(http::header::CONTENT_TYPE, ct);
        self
    }

    pub fn status(&self) -> Status {
        self.status
    }

    pub fn set_status(&mut self, status: Status) {
        self.status = status;
    }

    /// Convert to a hyper response using Full<Bytes> body
    pub(crate) fn into_hyper(self) -> http::Response<http_body_util::Full<hyper::body::Bytes>> {
        let mut builder = http::Response::builder().status(self.status.code());
        for (k, v) in self.headers.iter() {
            builder = builder.header(k, v);
        }
        builder
            .header(http::header::CONTENT_LENGTH, self.body.len().to_string())
            .body(http_body_util::Full::new(hyper::body::Bytes::from(self.body)))
            .unwrap()
    }
}

/// Trait for types that can be converted into a Response
pub trait Responder: Send {
    fn respond_to(self) -> Response;
}

impl Responder for &str {
    fn respond_to(self) -> Response {
        Response::ok(self)
    }
}

impl Responder for String {
    fn respond_to(self) -> Response {
        Response::ok(self)
    }
}

impl Responder for Response {
    fn respond_to(self) -> Response {
        self
    }
}

impl Responder for (Status, String) {
    fn respond_to(self) -> Response {
        Response::with_status(self.0, self.1)
    }
}

impl Responder for (Status, &str) {
    fn respond_to(self) -> Response {
        Response::with_status(self.0, self.1)
    }
}

impl Responder for Status {
    fn respond_to(self) -> Response {
        Response::with_status(self, format!("{}", self.code()))
    }
}

impl<T: serde::Serialize + Send> Responder for crate::extractor::Json<T> {
    fn respond_to(self) -> Response {
        match serde_json::to_vec(&self.0) {
            Ok(bytes) => Response::new(Status::OK, bytes).content_type("application/json"),
            Err(e) => Response::with_status(
                Status::INTERNAL_SERVER_ERROR,
                format!("JSON serialization error: {}", e),
            ),
        }
    }
}

impl Responder for () {
    fn respond_to(self) -> Response {
        Response::new(Status::NO_CONTENT, vec![])
    }
}

impl<T: Responder> Responder for Option<T> {
    fn respond_to(self) -> Response {
        match self {
            Some(val) => val.respond_to(),
            None => Response::not_found(),
        }
    }
}

impl<T: Responder, E: std::fmt::Display + Send> Responder for Result<T, E> {
    fn respond_to(self) -> Response {
        match self {
            Ok(val) => val.respond_to(),
            Err(e) => Response::with_status(Status::INTERNAL_SERVER_ERROR, format!("{}", e)),
        }
    }
}

/// Outcome of a handler or extractor — either success or a status to short-circuit
pub type Outcome<T> = Result<T, Status>;
