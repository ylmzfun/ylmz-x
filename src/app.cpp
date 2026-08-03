#include "ylmz/app.h"

#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <cstring>
#include <sstream>
#include <iostream>
#include <fstream>

namespace ylmz {

App::App() = default;
App::~App() = default;

// ============================================================
// HTTP Routing
// ============================================================

void App::GET(const std::string& path, HandlerFunc handler) {
    router_.add_route("GET", path, std::move(handler));
}
void App::POST(const std::string& path, HandlerFunc handler) {
    router_.add_route("POST", path, std::move(handler));
}
void App::PUT(const std::string& path, HandlerFunc handler) {
    router_.add_route("PUT", path, std::move(handler));
}
void App::DELETE(const std::string& path, HandlerFunc handler) {
    router_.add_route("DELETE", path, std::move(handler));
}
void App::PATCH(const std::string& path, HandlerFunc handler) {
    router_.add_route("PATCH", path, std::move(handler));
}
void App::HEAD(const std::string& path, HandlerFunc handler) {
    router_.add_route("HEAD", path, std::move(handler));
}
void App::OPTIONS(const std::string& path, HandlerFunc handler) {
    router_.add_route("OPTIONS", path, std::move(handler));
}

Router::Group App::Group(const std::string& prefix) {
    return Router::Group(&router_, prefix);
}

// ============================================================
// Middleware
// ============================================================

void App::Use(MiddlewareFunc mw) {
    mws_.push_back(std::move(mw));
}

// ============================================================
// WebSocket
// ============================================================

void App::WS(const std::string& path, WSHandler handler) {
    ws_routes_[path] = std::move(handler);
}

// ============================================================
// TCP
// ============================================================

TCPServer& App::TCP(const std::string& host, int port) {
    if (!tcp_server_) {
        tcp_server_ = std::make_unique<TCPServer>(&loop_);
    }
    tcp_server_->Listen(host, port);
    return *tcp_server_;
}

// ============================================================
// Static files
// ============================================================

void App::Static(const std::string& url_prefix, const std::string& dir_path) {
    std::string prefix = url_prefix;
    if (!prefix.empty() && prefix.back() == '/') prefix.pop_back();

    std::string dir = dir_path;
    if (!dir.empty() && dir.back() == '/') dir.pop_back();

    std::string path_pattern = prefix + "/*filepath";

    router_.add_route("GET", path_pattern, [dir, prefix](Context* ctx) {
        std::string filepath = dir + "/" + ctx->Param("filepath");
        std::ifstream file(filepath, std::ios::binary);
        if (!file.is_open()) {
            ctx->String(404, "Not Found");
            return;
        }

        std::ostringstream content;
        content << file.rdbuf();
        std::string data = content.str();

        // Simple MIME detection by extension
        auto ends_with = [](const std::string& s, const std::string& suffix) -> bool {
            return s.size() >= suffix.size() &&
                   s.compare(s.size() - suffix.size(), suffix.size(), suffix) == 0;
        };

        std::string content_type = "application/octet-stream";
        if (ends_with(filepath, ".html") || ends_with(filepath, ".htm"))
            content_type = "text/html; charset=utf-8";
        else if (ends_with(filepath, ".css"))
            content_type = "text/css; charset=utf-8";
        else if (ends_with(filepath, ".js"))
            content_type = "application/javascript; charset=utf-8";
        else if (ends_with(filepath, ".json"))
            content_type = "application/json; charset=utf-8";
        else if (ends_with(filepath, ".png"))
            content_type = "image/png";
        else if (ends_with(filepath, ".jpg") || ends_with(filepath, ".jpeg"))
            content_type = "image/jpeg";
        else if (ends_with(filepath, ".svg"))
            content_type = "image/svg+xml";
        else if (ends_with(filepath, ".txt"))
            content_type = "text/plain; charset=utf-8";

        ctx->Data(200, content_type, data);
    });
}

// ============================================================
// Run
// ============================================================

void App::Run(const std::string& addr) {
    std::string host = "0.0.0.0";
    int port = 8080;

    size_t colon = addr.find(':');
    if (colon != std::string::npos) {
        std::string host_part = addr.substr(0, colon);
        std::string port_part = addr.substr(colon + 1);
        if (!host_part.empty()) host = host_part;
        if (!port_part.empty()) port = std::stoi(port_part);
    }

    listen_fd_ = create_listen_socket(host.c_str(), port);
    std::cout << "[ylmz] HTTP server listening on " << host << ":" << port << std::endl;

    auto* self = this;
    loop_.add_fd(listen_fd_, EPOLLIN, [self](uint32_t) {
        self->handle_accept();
    });

    loop_.run();
}

// ============================================================
// Connection handling
// ============================================================

void App::handle_accept() {
    while (true) {
        struct sockaddr_in client_addr;
        socklen_t addr_len = sizeof(client_addr);
        int client_fd = accept(listen_fd_, (struct sockaddr*)&client_addr, &addr_len);
        if (client_fd < 0) {
            if (errno == EAGAIN || errno == EWOULDBLOCK) break;
            break;
        }

        set_nonblocking(client_fd);

        auto conn = std::make_unique<ConnState>();
        conn->fd = client_fd;

        auto* conn_ptr = conn.get();
        // The parser callback captures both this and conn_ptr
        conn->parser.set_callback([this, conn_ptr](HttpRequest& req) {
            this->dispatch_request(conn_ptr, req);
        });

        connections_[client_fd] = std::move(conn);

        loop_.add_fd(client_fd, EPOLLIN, [this, client_fd](uint32_t events) {
            if (events & (EPOLLIN | EPOLLPRI)) {
                this->handle_read(client_fd);
            }
            if (events & (EPOLLERR | EPOLLHUP)) {
                this->close_connection(client_fd);
            }
        });
    }
}

void App::handle_read(int fd) {
    auto it = connections_.find(fd);
    if (it == connections_.end()) return;

    auto& conn = it->second;

    // WebSocket mode
    if (conn->upgraded && conn->ws_conn) {
        char buf[65536];
        while (true) {
            ssize_t n = read(fd, buf, sizeof(buf));
            if (n > 0) {
                conn->ws_conn->feed_data(buf, n);
            } else if (n == 0) {
                close_connection(fd);
                return;
            } else {
                if (errno == EAGAIN || errno == EWOULDBLOCK) break;
                close_connection(fd);
                return;
            }
        }
        return;
    }

    // HTTP mode
    char buf[65536];
    while (true) {
        ssize_t n = read(fd, buf, sizeof(buf));
        if (n > 0) {
            conn->parser.parse(buf, n);
            // Parser callback dispatches when complete
        } else if (n == 0) {
            close_connection(fd);
            return;
        } else {
            if (errno == EAGAIN || errno == EWOULDBLOCK) break;
            close_connection(fd);
            return;
        }
    }
}

void App::dispatch_request(ConnState* conn, HttpRequest& req) {
    // Check WebSocket upgrade first
    auto ws_it = ws_routes_.find(req.path);
    if (ws_it != ws_routes_.end()) {
        // Try upgrade
        std::ostringstream header_str;
        for (auto& [k, v] : req.headers) {
            header_str << k << ": " << v << "\r\n";
        }
        std::string accept_key;
        if (WSUpgrader::try_upgrade(conn->fd, header_str.str(), accept_key)) {
            conn->upgraded = true;
            conn->ws_conn = std::make_unique<WSConn>(conn->fd);
            ws_it->second(conn->ws_conn.get());
            return;
        }
    }

    // HTTP routing - create context first to strip query string
    Context ctx(conn->fd);
    ctx.set_request(req);

    std::map<std::string, std::string> params;
    auto handler = router_.find(req.method, ctx.Path(), params);
    ctx.set_params(std::move(params));

    if (!handler) {
        ctx.JSON(404, {{"error", "Not Found"}});
        return;
    }

    // Build middleware chain: global mws + handler
    std::vector<MiddlewareFunc> chain = mws_;
    chain.push_back([handler](Context* c) {
        handler(c);
    });

    ctx.set_middlewares(&chain);
    ctx.Next();
}

void App::close_connection(int fd) {
    auto it = connections_.find(fd);
    if (it == connections_.end()) return;

    auto& conn = it->second;
    if (conn->upgraded && conn->ws_conn) {
        conn->ws_conn.release(); // Don't double-close fd in WSConn destructor
    }

    loop_.del_fd(fd);
    close(fd);
    connections_.erase(it);
}

} // namespace ylmz
