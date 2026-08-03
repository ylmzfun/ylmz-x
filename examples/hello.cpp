#include <ylmz/ylmz.h>
#include <iostream>

int main() {
    ylmz::App app;

    // Built-in middleware
    app.Use(ylmz::Logger());

    // Basic routes
    app.GET("/", [](ylmz::Context* ctx) {
        ctx->String(200, "Hello, ylmz!");
    });

    app.GET("/hello", [](ylmz::Context* ctx) {
        std::string name = ctx->Query("name");
        if (name.empty()) name = "World";
        ctx->String(200, "Hello, " + name + "!");
    });

    app.GET("/json", [](ylmz::Context* ctx) {
        ylmz::json data = {
            {"message", "Hello from ylmz"},
            {"version", "1.0.0"},
            {"features", {"HTTP", "WebSocket", "TCP"}}
        };
        ctx->JSON(200, data);
    });

    app.GET("/html", [](ylmz::Context* ctx) {
        ctx->HTML(200, "<h1>ylmz Framework</h1><p>A C++ web framework like Gin.</p>");
    });

    app.Run(":8080");
    return 0;
}
