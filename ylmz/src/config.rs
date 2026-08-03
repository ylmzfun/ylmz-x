/// Server configuration
#[derive(Debug, Clone)]
pub struct Config {
    /// Address to bind to (default: "127.0.0.1")
    pub address: String,
    /// Port to listen on (default: 8000)
    pub port: u16,
    /// Maximum request body size in bytes
    pub max_body_size: usize,
    /// Enable debug logging
    pub debug: bool,
}

impl Default for Config {
    fn default() -> Self {
        Config {
            address: "127.0.0.1".into(),
            port: 8000,
            max_body_size: 1024 * 1024, // 1 MB
            debug: false,
        }
    }
}

impl Config {
    pub fn new() -> Self {
        Config::default()
    }

    pub fn address(mut self, addr: impl Into<String>) -> Self {
        self.address = addr.into();
        self
    }

    pub fn port(mut self, port: u16) -> Self {
        self.port = port;
        self
    }

    pub fn bind_addr(&self) -> String {
        format!("{}:{}", self.address, self.port)
    }
}
