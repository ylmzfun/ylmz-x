#pragma once

#include "router.h"
#include "context.h"
#include "middleware.h"
#include "event_loop.h"
#include "ws.h"
#include "tcp.h"
#include "http_parser.h"

#include <string>
#include <vector>
#include <functional>
#include <memory>
#include <unordered_map>

namespace ylmz {

class App {
public:
    App();
    ~App();

    App(const App&) = delete;
    App& operator=(const App&) = delete;

    // --- HTTP Routing ---
    void GET(const std::string& path, HandlerFunc handler);
    void POST(const std::string& path, HandlerFunc handler);
    void PUT(const std::string& path, HandlerFunc handler);
    void DELETE(const std::string& path, HandlerFunc handler);
    void PATCH(const std::string& path, HandlerFunc handler);
    void HEAD(const std::string& path, HandlerFunc handler);
    void OPTIONS(const std::string& path, HandlerFunc handler);

    // Route group
    Router::Group Group(const std::string& prefix);

    // --- Middleware ---
    // Add global middleware (applied to all routes)
    void Use(MiddlewareFunc mw);

    // Add a middleware factory (e.g., Logger() returns a MiddlewareFunc)
    template<typename... Mws>
    void Use(Mws... middlewares) {
        (mws_.push_back(middlewares), ...);
    }

    // --- WebSocket upgrade handler ---
    // Called after successful WebSocket upgrade
    using WSHandler = std::function<void(WSConn*)>;
    void WS(const std::string& path, WSHandler handler);

    // --- TCP server ---
    // Start TCP server on the given address
    TCPServer& TCP(const std::string& host, int port);

    // --- Static files ---
    void Static(const std::string& url_prefix, const std::string& dir_path);

    // --- Run the server ---
    // addr format: ":8080" or "0.0.0.0:8080"
    void Run(const std::string& addr);

private:
    Router router_;
    EventLoop loop_;
    std::vector<MiddlewareFunc> mws_;
    std::unique_ptr<TCPServer> tcp_server_;

    // WebSocket routes: path -> handler
    std::unordered_map<std::string, WSHandler> ws_routes_;

    int listen_fd_ = -1;

    // Connection state
    struct ConnState {
        int fd;
        HttpParser parser;
        std::string read_buf;
        std::string write_buf;
        bool writing = false;
        bool upgraded = false; // true if upgraded to WebSocket
        std::unique_ptr<WSConn> ws_conn;
    };

    std::unordered_map<int, std::unique_ptr<ConnState>> connections_;

    void handle_accept();
    void handle_read(int fd);
    void handle_write(int fd);
    void dispatch_request(ConnState* conn, HttpRequest& req);
    void close_connection(int fd);
};

} // namespace ylmz
