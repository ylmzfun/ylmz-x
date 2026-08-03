#include <ylmz/ylmz.h>
#include <cassert>
#include <iostream>

int main() {
    std::cout << "=== Router Tests ===" << std::endl;

    ylmz::Router router;

    bool called = false;

    // Test 1: Static route
    router.GET("/hello", [&](ylmz::Context*) { called = true; });
    {
        std::map<std::string, std::string> params;
        auto h = router.find("GET", "/hello", params);
        assert(h != nullptr);
        assert(params.empty());
        std::cout << "  PASS: static route /hello" << std::endl;
    }

    // Test 2: Param route
    called = false;
    router.GET("/user/:id", [&](ylmz::Context*) { called = true; });
    {
        std::map<std::string, std::string> params;
        auto h = router.find("GET", "/user/42", params);
        assert(h != nullptr);
        assert(params["id"] == "42");
        std::cout << "  PASS: param route /user/:id -> id=42" << std::endl;
    }

    // Test 3: Wildcard route
    router.GET("/static/*filepath", [&](ylmz::Context*) { called = true; });
    {
        std::map<std::string, std::string> params;
        auto h = router.find("GET", "/static/css/main.css", params);
        assert(h != nullptr);
        assert(params["filepath"] == "css/main.css");
        std::cout << "  PASS: wildcard /static/*filepath -> css/main.css" << std::endl;
    }

    // Test 4: Nested route
    router.GET("/a/b/c", [&](ylmz::Context*) { called = true; });
    {
        std::map<std::string, std::string> params;
        auto h = router.find("GET", "/a/b/c", params);
        assert(h != nullptr);
        std::cout << "  PASS: nested route /a/b/c" << std::endl;
    }

    // Test 5: 404
    {
        std::map<std::string, std::string> params;
        auto h = router.find("GET", "/nonexistent", params);
        assert(h == nullptr);
        std::cout << "  PASS: 404 for /nonexistent" << std::endl;
    }

    // Test 6: Route group
    ylmz::Router router2;
    auto api = router2.CreateGroup("/api");
    api.GET("/ping", [&](ylmz::Context*) { called = true; });
    {
        std::map<std::string, std::string> params;
        auto h = router2.find("GET", "/api/ping", params);
        assert(h != nullptr);
        std::cout << "  PASS: route group /api/ping" << std::endl;
    }

    // Test 7: Nested group
    ylmz::Router router3;
    auto v1 = router3.CreateGroup("/api/v1");
    auto users = v1.SubGroup("/users");
    users.GET("/list", [&](ylmz::Context*) { called = true; });
    {
        std::map<std::string, std::string> params;
        auto h = router3.find("GET", "/api/v1/users/list", params);
        assert(h != nullptr);
        std::cout << "  PASS: nested group /api/v1/users/list" << std::endl;
    }

    // Test 8: Multiple params
    ylmz::Router router4;
    router4.GET("/user/:uid/post/:pid", [&](ylmz::Context*) { called = true; });
    {
        std::map<std::string, std::string> params;
        auto h = router4.find("GET", "/user/10/post/20", params);
        assert(h != nullptr);
        assert(params["uid"] == "10");
        assert(params["pid"] == "20");
        std::cout << "  PASS: multiple params uid=10, pid=20" << std::endl;
    }

    std::cout << "\n=== HTTP Parser Tests ===" << std::endl;

    // Test: parse simple GET request
    ylmz::HttpParser parser;
    ylmz::HttpRequest captured_req;

    parser.set_callback([&](ylmz::HttpRequest& r) {
        captured_req = r;
    });

    const char* raw = "GET /api/users HTTP/1.1\r\n"
                      "Host: localhost:8080\r\n"
                      "Content-Length: 0\r\n"
                      "\r\n";
    parser.parse(raw, strlen(raw));

    assert(captured_req.method == "GET");
    assert(captured_req.path == "/api/users");
    assert(captured_req.version == "HTTP/1.1");
    assert(captured_req.headers["host"] == "localhost:8080");
    std::cout << "  PASS: HTTP GET request parsed" << std::endl;

    // Test: parse POST request with body
    ylmz::HttpParser parser2;
    ylmz::HttpRequest captured_req2;

    parser2.set_callback([&](ylmz::HttpRequest& r) {
        captured_req2 = r;
    });

    const char* raw2 = "POST /api/users HTTP/1.1\r\n"
                       "Host: localhost:8080\r\n"
                       "Content-Type: application/json\r\n"
                       "Content-Length: 17\r\n"
                       "\r\n"
                       "{\"name\": \"Alice\"}";
    parser2.parse(raw2, strlen(raw2));

    assert(captured_req2.method == "POST");
    assert(captured_req2.path == "/api/users");
    assert(captured_req2.headers["content-type"] == "application/json");
    assert(captured_req2.body == "{\"name\": \"Alice\"}");
    std::cout << "  PASS: HTTP POST with JSON body parsed" << std::endl;

    std::cout << "\n=== All tests passed! ===" << std::endl;
    return 0;
}
