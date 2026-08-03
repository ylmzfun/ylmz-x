use std::collections::HashMap;

use crate::Method;

/// Incoming HTTP request
pub struct Request {
    pub(crate) inner: http::Request<hyper::body::Incoming>,
    pub(crate) path_params: HashMap<String, String>,
    pub(crate) query_params: HashMap<String, String>,
    pub(crate) body_bytes: Option<Vec<u8>>,
}

impl Request {
    pub fn new(inner: http::Request<hyper::body::Incoming>) -> Self {
        let query_params = inner
            .uri()
            .query()
            .map(|q| {
                serde_urlencoded::from_str::<Vec<(String, String)>>(q)
                    .unwrap_or_default()
                    .into_iter()
                    .collect::<HashMap<_, _>>()
            })
            .unwrap_or_default();

        Request {
            inner,
            path_params: HashMap::new(),
            query_params,
            body_bytes: None,
        }
    }

    pub fn method(&self) -> Method {
        self.inner.method().as_str().parse().unwrap_or(Method::GET)
    }

    pub fn uri(&self) -> &http::Uri {
        self.inner.uri()
    }

    pub fn path(&self) -> &str {
        self.inner.uri().path()
    }

    pub fn headers(&self) -> &http::HeaderMap {
        self.inner.headers()
    }

    /// Get a path parameter by name (e.g., `<name>` in `/hello/<name>`)
    pub fn path_param(&self, name: &str) -> Option<&str> {
        self.path_params.get(name).map(|s| s.as_str())
    }

    pub fn set_path_param(&mut self, name: String, value: String) {
        self.path_params.insert(name, value);
    }

    /// Get a query parameter by name
    pub fn query_param(&self, name: &str) -> Option<&str> {
        self.query_params.get(name).map(|s| s.as_str())
    }

    /// Read and cache the request body (call once, early in request lifecycle)
    pub async fn cache_body(&mut self) -> Result<(), crate::Error> {
        if self.body_bytes.is_some() {
            return Ok(());
        }

        use http_body_util::BodyExt;

        let mut data = Vec::new();
        loop {
            let frame_result = self.inner.body_mut().frame().await;
            let frame_data = match frame_result {
                Some(Ok(fd)) => fd,
                Some(Err(e)) => {
                    return Err(crate::Error::Internal(format!("body read error: {}", e)));
                }
                None => break,
            };

            match frame_data.into_data() {
                Ok(buf) => data.extend_from_slice(&buf),
                Err(_trailers) => break,
            }
        }

        self.body_bytes = Some(data);
        Ok(())
    }

    /// Get cached body bytes (must call `cache_body()` first in an async context)
    pub fn body_bytes(&self) -> Result<&[u8], crate::Error> {
        self.body_bytes
            .as_deref()
            .ok_or_else(|| crate::Error::Internal("body not yet read".into()))
    }

    /// Get body as UTF-8 string
    pub fn body_string(&self) -> Result<String, crate::Error> {
        let bytes = self.body_bytes()?;
        String::from_utf8(bytes.to_vec())
            .map_err(|e| crate::Error::Internal(format!("invalid UTF-8: {}", e)))
    }

    /// Get the content type of the request
    pub fn content_type(&self) -> Option<&str> {
        self.inner
            .headers()
            .get(http::header::CONTENT_TYPE)
            .and_then(|v| v.to_str().ok())
    }
}

impl std::fmt::Debug for Request {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Request")
            .field("method", &self.method())
            .field("path", &self.path())
            .field("path_params", &self.path_params)
            .field("query_params", &self.query_params)
            .finish()
    }
}
