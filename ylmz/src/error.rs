use crate::status::Status;

/// Framework error type
#[derive(Debug)]
pub enum Error {
    /// Internal server error
    Internal(String),
    /// Request extraction error (e.g., missing parameter, invalid type)
    Extraction(String),
    /// HTTP status used as a short-circuit in routing
    Status(Status),
}

impl std::fmt::Display for Error {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Error::Internal(msg) => write!(f, "internal error: {}", msg),
            Error::Extraction(msg) => write!(f, "extraction error: {}", msg),
            Error::Status(s) => write!(f, "HTTP {}", s.code()),
        }
    }
}

impl std::error::Error for Error {}

impl From<Status> for Error {
    fn from(s: Status) -> Self {
        Error::Status(s)
    }
}

/// Shorthand for Result<T, Error>
pub type Result<T> = std::result::Result<T, Error>;
