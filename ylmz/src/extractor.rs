use std::str::FromStr;

use crate::error::{Error, Result};
use crate::request::Request;
use crate::state::StateContainer;

/// Trait for types that can be extracted from a request
///
/// Implementations are provided for:
/// - `String` (path segment by position)
/// - `T: FromStr` (path segment by position)
/// - `&State<T>` (managed application state)
/// - `Json<T: Deserialize>` (JSON request body)
/// - `Query<T: Deserialize>` (query parameters)
pub trait FromRequest: Sized {
    fn from_request(req: &mut Request, state: &StateContainer) -> Result<Self>;
}

// ===== JSON extractor =====

/// Extracts JSON from the request body
///
/// ```ignore
/// #[post("/users", data = "<user>")]
/// fn create_user(user: Json<User>) -> String { ... }
/// ```
#[derive(Debug)]
pub struct Json<T>(pub T);

impl<T> Json<T> {
    pub fn into_inner(self) -> T {
        self.0
    }
}

impl<T: serde::de::DeserializeOwned> FromRequest for Json<T> {
    fn from_request(req: &mut Request, _state: &StateContainer) -> Result<Self> {
        let bytes = req.body_bytes()?;
        serde_json::from_slice::<T>(bytes)
            .map(Json)
            .map_err(|e| Error::Extraction(format!("JSON parse error: {}", e)))
    }
}

// ===== Query extractor =====

/// Extracts query parameters from the request URL
///
/// ```ignore
/// #[get("/search")]
/// fn search(query: Query<SearchParams>) -> String { ... }
/// ```
#[derive(Debug)]
pub struct Query<T>(pub T);

impl<T> Query<T> {
    pub fn into_inner(self) -> T {
        self.0
    }
}

impl<T: serde::de::DeserializeOwned> FromRequest for Query<T> {
    fn from_request(req: &mut Request, _state: &StateContainer) -> Result<Self> {
        let query_str = req.uri().query().unwrap_or("");
        serde_urlencoded::from_str::<T>(query_str)
            .map(Query)
            .map_err(|e| Error::Extraction(format!("query parse error: {}", e)))
    }
}

// ===== State extractor =====

use crate::state::State;

impl<T: Send + Sync + 'static> FromRequest for State<T> {
    fn from_request(_req: &mut Request, state: &StateContainer) -> Result<Self> {
        state
            .get::<T>()
            .map(|arc| State::new(arc))
            .ok_or_else(|| {
                Error::Extraction(format!(
                    "State<{}> not found in managed state",
                    std::any::type_name::<T>()
                ))
            })
    }
}

// ===== Path segment extractor (used internally) =====

/// Extract a path parameter by name as a string
pub fn extract_path_string(req: &Request, name: &str) -> Result<String> {
    req.path_param(name)
        .map(|s| s.to_string())
        .ok_or_else(|| Error::Extraction(format!("missing path parameter: {}", name)))
}

/// Extract a path parameter by name and parse it
pub fn extract_path_param<T: FromStr>(req: &Request, name: &str) -> Result<T>
where
    T::Err: std::fmt::Display,
{
    let s = extract_path_string(req, name)?;
    T::from_str(&s).map_err(|e| Error::Extraction(format!("invalid path parameter '{}': {}", name, e)))
}

// ===== Option<T> extractor =====

impl<T: FromRequest> FromRequest for Option<T> {
    fn from_request(req: &mut Request, state: &StateContainer) -> Result<Self> {
        match T::from_request(req, state) {
            Ok(v) => Ok(Some(v)),
            Err(_) => Ok(None),
        }
    }
}
