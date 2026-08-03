/// HTTP status codes
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Status(u16);

impl Status {
    pub const OK: Status = Status(200);
    pub const CREATED: Status = Status(201);
    pub const ACCEPTED: Status = Status(202);
    pub const NO_CONTENT: Status = Status(204);
    pub const MOVED_PERMANENTLY: Status = Status(301);
    pub const FOUND: Status = Status(302);
    pub const NOT_MODIFIED: Status = Status(304);
    pub const BAD_REQUEST: Status = Status(400);
    pub const UNAUTHORIZED: Status = Status(401);
    pub const FORBIDDEN: Status = Status(403);
    pub const NOT_FOUND: Status = Status(404);
    pub const METHOD_NOT_ALLOWED: Status = Status(405);
    pub const CONFLICT: Status = Status(409);
    pub const UNPROCESSABLE_ENTITY: Status = Status(422);
    pub const INTERNAL_SERVER_ERROR: Status = Status(500);
    pub const NOT_IMPLEMENTED: Status = Status(501);
    pub const BAD_GATEWAY: Status = Status(502);
    pub const SERVICE_UNAVAILABLE: Status = Status(503);

    pub fn new(code: u16) -> Self {
        Status(code)
    }

    pub fn code(&self) -> u16 {
        self.0
    }
}

impl std::fmt::Display for Status {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}
