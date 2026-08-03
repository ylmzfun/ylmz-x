#pragma once

#include "context.h"
#include "router.h"
#include <functional>

namespace ylmz {

// Built-in middleware functions

// Logger: logs each request with method, path, status, and latency
MiddlewareFunc Logger();

// Recovery: catches exceptions in handlers and returns 500
MiddlewareFunc Recovery();

// CORS: adds Cross-Origin Resource Sharing headers
MiddlewareFunc CORS(const std::string& allow_origin = "*",
                    const std::string& allow_methods = "GET,POST,PUT,DELETE,PATCH,OPTIONS",
                    const std::string& allow_headers = "Content-Type,Authorization");

} // namespace ylmz
