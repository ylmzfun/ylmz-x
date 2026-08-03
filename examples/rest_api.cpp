#include <ylmz/ylmz.h>
#include <iostream>

// Simple in-memory "database"
std::vector<ylmz::json> users = {
    {{"id", 1}, {"name", "Alice"}, {"email", "alice@example.com"}},
    {{"id", 2}, {"name", "Bob"},   {"email", "bob@example.com"}},
};

int main() {
    ylmz::App app;

    app.Use(ylmz::Logger(), ylmz::Recovery());
    app.Use(ylmz::CORS());

    // GET /api/users - list all users
    app.GET("/api/users", [](ylmz::Context* ctx) {
        ctx->JSON(200, users);
    });

    // GET /api/users/:id - get user by ID
    app.GET("/api/users/:id", [](ylmz::Context* ctx) {
        int id = std::stoi(ctx->Param("id"));
        for (auto& u : users) {
            if (u["id"] == id) {
                ctx->JSON(200, u);
                return;
            }
        }
        ctx->JSON(404, {{"error", "User not found"}});
    });

    // POST /api/users - create a new user
    app.POST("/api/users", [](ylmz::Context* ctx) {
        try {
            auto body = ctx->GetJSON();
            ylmz::json new_user = {
                {"id", users.size() + 1},
                {"name", body["name"]},
                {"email", body["email"]}
            };
            users.push_back(new_user);
            ctx->JSON(201, new_user);
        } catch (...) {
            ctx->JSON(400, {{"error", "Invalid JSON"}});
        }
    });

    // Using route groups
    auto v1 = app.Group("/api/v1");
    {
        v1.GET("/ping", [](ylmz::Context* ctx) {
            ctx->JSON(200, {{"msg", "pong"}, {"version", "v1"}});
        });
    }

    std::cout << "REST API server starting on :8080" << std::endl;
    app.Run(":8080");
    return 0;
}
