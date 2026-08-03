//! # ylmz — A lightweight, Rocket-inspired web framework for Rust
//!
//! ```ignore
//! use ylmz::prelude::*;
//!
//! #[get("/")]
//! fn index() -> &'static str {
//!     "Hello, world!"
//! }
//!
//! #[get("/hello/<name>")]
//! fn hello(name: String) -> String {
//!     format!("Hello, {}!", name)
//! }
//!
//! fn main() -> ylmz::Result<()> {
//!     App::new()
//!         .mount("/", routes![index, hello])
//!         .launch()
//! }
//! ```

pub mod app;
pub mod catcher;
pub mod config;
pub mod error;
pub mod extractor;
pub mod fairing;
pub mod method;
pub mod request;
pub mod response;
pub mod route;
pub mod state;
pub mod status;

// Re-export paste for macro use
pub use paste;

// Core types
pub use app::App;
pub use catcher::{Catcher, Catchers};
pub use config::Config;
pub use error::{Error, Result};
pub use extractor::{FromRequest, Json, Query};
pub use fairing::{Fairing, Logger};
pub use method::Method;
pub use request::Request;
pub use response::{Responder, Response};
pub use route::{Route, Router};
pub use state::{State, StateContainer};
pub use status::Status;

// Re-export proc macros
pub use ylmz_macros::{catch, delete, get, patch, post, put};

/// Prelude — import this for the most commonly used types
pub mod prelude {
    pub use crate::app::App;
    pub use crate::error::Result;
    pub use crate::extractor::{Json, Query};
    pub use crate::fairing::{Fairing, Logger};
    pub use crate::response::Responder;
    pub use crate::state::State;
    pub use crate::status::Status;
    pub use crate::{catchers, routes};
    pub use ylmz_macros::{catch, delete, get, patch, post, put};
}
