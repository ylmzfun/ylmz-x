use crate::request::Request;
use crate::response::Response;

/// Lifecycle hooks for the framework.
/// Similar to Rocket's Fairings, allows hooking into request/response processing.
pub trait Fairing: Send + Sync {
    /// Called when a request is received, before routing.
    /// Return `None` to continue normally, or `Some(Response)` to short-circuit.
    fn on_request(&self, _req: &Request) -> Option<Response> {
        None
    }

    /// Called after a response is generated, before sending.
    /// Can modify the response (e.g., add headers).
    fn on_response(&self, _req: &Request, res: &mut Response) {
        let _ = _req;
        let _ = res;
    }
}

/// A logger fairing that logs each request
pub struct Logger;

impl Fairing for Logger {
    fn on_request(&self, req: &Request) -> Option<Response> {
        println!("→ {} {}", req.method().as_str(), req.path());
        None
    }

    fn on_response(&self, req: &Request, res: &mut Response) {
        println!(
            "← {} {} — {}",
            req.method().as_str(),
            req.path(),
            res.status().code()
        );
    }
}
