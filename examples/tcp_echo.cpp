#include <ylmz/ylmz.h>
#include <iostream>

int main() {
    ylmz::App app;

    // TCP echo server on port 9000
    auto& tcp = app.TCP("0.0.0.0", 9000);

    tcp.OnConnection([](ylmz::TCPConn* conn) {
        std::cout << "[TCP] New connection from fd=" << conn->fd() << std::endl;

        // Echo back all received data
        conn->OnData([](ylmz::TCPConn* c, const char* data, size_t len) {
            std::string msg(data, len);
            std::cout << "[TCP] Received " << len << " bytes: " << msg;
            c->Send(data, len); // Echo
        });

        conn->OnClose([](ylmz::TCPConn* c) {
            std::cout << "[TCP] Connection closed fd=" << c->fd() << std::endl;
        });
    });

    std::cout << "TCP Echo server on :9000, HTTP on :8080" << std::endl;

    // Also serve HTTP on :8080
    app.GET("/", [](ylmz::Context* ctx) {
        ctx->String(200, "TCP Echo server is running on port 9000");
    });

    app.Run(":8080");
    return 0;
}
