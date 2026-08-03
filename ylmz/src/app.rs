use std::net::SocketAddr;
use std::sync::Arc;

use hyper::body::Incoming;
use hyper::server::conn::http1;
use hyper::service::service_fn;
use hyper_util::rt::TokioIo;
use tokio::net::TcpListener;

use crate::catcher::Catchers;
use crate::config::Config;
use crate::error::Result;
use crate::fairing::Fairing;
use crate::request::Request;
use crate::response::Response;
use crate::route::Router;
use crate::state::StateContainer;
use crate::status::Status;

/// The main application builder — entry point for the framework
pub struct App {
    config: Config,
    state: StateContainer,
    router: Router,
    catchers: Catchers,
    fairings: Vec<Box<dyn Fairing>>,
}

impl App {
    /// Create a new App with default configuration
    pub fn new() -> Self {
        App {
            config: Config::default(),
            state: StateContainer::new(),
            router: Router::new(),
            catchers: Catchers::new(),
            fairings: vec![],
        }
    }

    /// Configure the server
    pub fn configure(mut self, config: Config) -> Self {
        self.config = config;
        self
    }

    /// Add application-wide managed state
    pub fn manage<T: Send + Sync + 'static>(mut self, value: T) -> Self {
        self.state.insert(value);
        self
    }

    /// Mount routes under a path prefix
    pub fn mount(mut self, _prefix: &str, router: Router) -> Self {
        self.router.merge(router);
        self
    }

    /// Register error catchers
    pub fn register(mut self, _prefix: &str, catchers: Catchers) -> Self {
        self.catchers = catchers;
        self
    }

    /// Attach a fairing (middleware)
    pub fn attach<F: Fairing + 'static>(mut self, fairing: F) -> Self {
        self.fairings.push(Box::new(fairing));
        self
    }

    /// Launch the server (blocking)
    pub fn launch(self) -> Result<()> {
        let rt = tokio::runtime::Runtime::new()
            .map_err(|e| crate::Error::Internal(format!("tokio runtime: {}", e)))?;

        rt.block_on(self.launch_async())
    }

    async fn launch_async(self) -> Result<()> {
        let addr: SocketAddr = self
            .config
            .bind_addr()
            .parse()
            .map_err(|e| crate::Error::Internal(format!("invalid bind address: {}", e)))?;

        let listener = TcpListener::bind(addr).await.map_err(|e| {
            crate::Error::Internal(format!("bind failed: {}", e))
        })?;

        println!("🚀 ylmz server running at http://{}", addr);

        let app = Arc::new(self);

        loop {
            let (stream, _) = listener.accept().await.map_err(|e| {
                crate::Error::Internal(format!("accept failed: {}", e))
            })?;

            let app = app.clone();

            tokio::spawn(async move {
                let io = TokioIo::new(stream);

                let svc = service_fn(move |req: http::Request<Incoming>| {
                    let app = app.clone();
                    async move {
                        let response = handle_request(&app, req).await;
                        let hyper_resp = match response {
                            Ok(resp) => resp.into_hyper(),
                            Err(e) => match e {
                                crate::Error::Status(s) => app.catchers.handle(s).into_hyper(),
                                _ => Response::with_status(
                                    Status::INTERNAL_SERVER_ERROR,
                                    format!("{}", e),
                                )
                                .into_hyper(),
                            },
                        };
                        Ok::<_, std::convert::Infallible>(hyper_resp)
                    }
                });

                if let Err(e) = http1::Builder::new()
                    .serve_connection(io, svc)
                    .await
                {
                    eprintln!("connection error: {}", e);
                }
            });
        }
    }
}

async fn handle_request(app: &App, req: http::Request<Incoming>) -> Result<Response> {
    let mut request = Request::new(req);

    // Eagerly read body bytes so sync extractors can access them
    request.cache_body().await?;

    // Run request fairings
    for fairing in &app.fairings {
        if let Some(response) = fairing.on_request(&request) {
            let mut resp = response;
            for f in &app.fairings {
                f.on_response(&request, &mut resp);
            }
            return Ok(resp);
        }
    }

    // Dispatch to route handler
    let result = app.router.dispatch(&mut request, &app.state);

    match result {
        Ok(mut response) => {
            for fairing in &app.fairings {
                fairing.on_response(&request, &mut response);
            }
            Ok(response)
        }
        Err(crate::Error::Status(s)) => {
            let response = app.catchers.handle(s);
            Ok(response)
        }
        Err(e) => {
            let mut response =
                Response::with_status(Status::INTERNAL_SERVER_ERROR, format!("{}", e));
            for fairing in &app.fairings {
                fairing.on_response(&request, &mut response);
            }
            Ok(response)
        }
    }
}
