# ylmz

> 一个类似 [Gin](https://github.com/gin-gonic/gin) 的 C++17 高性能网络框架，支持 HTTP、WebSocket 和 TCP 服务。

## 特性

- **高性能 HTTP 路由** — 基于 Radix Tree 的路由器，支持 `:param` 路径参数和 `*wildcard` 通配符
- **中间件支持** — 全局中间件链，内置 Logger、Recovery、CORS
- **路由分组** — 类似 Gin 的 `Group()` API，支持嵌套分组
- **JSON 支持** — 集成 [nlohmann/json](https://github.com/nlohmann/json)，轻松处理 JSON 请求/响应
- **WebSocket** — 自实现 RFC 6455 协议，含 SHA1 握手与帧解析
- **TCP 服务器** — 独立 TCP 服务支持，可复用同一事件循环
- **跨平台** — macOS (kqueue) / Linux (epoll) 事件驱动
- **零外部依赖** — 除 nlohmann/json 单头文件外，完全自包含

## 快速开始

### 构建

```bash
# macOS / Linux
make all
```

需要 C++17 编译器（Clang 或 GCC）。

### 示例

**Hello World**

```cpp
#include <ylmz/ylmz.h>

int main() {
    ylmz::App app;

    app.Use(ylmz::Logger());

    app.GET("/", [](ylmz::Context* ctx) {
        ctx->String(200, "Hello, ylmz!");
    });

    app.GET("/hello", [](ylmz::Context* ctx) {
        std::string name = ctx->Query("name");
        if (name.empty()) name = "World";
        ctx->String(200, "Hello, " + name + "!");
    });

    app.Run(":8080");
}
```

**RESTful API**

```cpp
#include <ylmz/ylmz.h>

int main() {
    ylmz::App app;

    app.Use(ylmz::Logger(), ylmz::Recovery());

    // 路由分组
    auto v1 = app.Group("/api/v1");
    {
        v1.GET("/ping", [](ylmz::Context* ctx) {
            ctx->JSON(200, {{"msg", "pong"}});
        });

        v1.GET("/user/:id", [](ylmz::Context* ctx) {
            std::string id = ctx->Param("id");
            ctx->JSON(200, {{"id", id}, {"name", "Alice"}});
        });

        v1.POST("/user", [](ylmz::Context* ctx) {
            auto body = ctx->GetJSON();
            ctx->JSON(201, body);
        });
    }

    app.Run(":8080");
}
```

**WebSocket**

```cpp
app.WS("/ws", [](ylmz::WSConn* ws) {
    ws->OnMessage([](ylmz::WSConn* conn, const std::string& msg) {
        conn->Send("Echo: " + msg);
    });

    ws->OnClose([](ylmz::WSConn*) {
        std::cout << "Connection closed" << std::endl;
    });
});
```

**TCP 服务器**

```cpp
auto& tcp = app.TCP("0.0.0.0", 9000);
tcp.OnConnection([](ylmz::TCPConn* conn) {
    conn->OnData([](ylmz::TCPConn* c, const char* data, size_t len) {
        c->Send(data, len); // Echo
    });
});
```

### 运行示例

```bash
# HTTP 基础服务
./example_hello

# RESTful API (带 CORS)
./example_rest

# WebSocket Echo
./example_ws

# TCP Echo + HTTP 混合
./example_tcp
```

### 测试

```bash
make test
```

## API 概览

### 路由

| 方法 | 路径示例 | 说明 |
|------|---------|------|
| `GET` / `POST` / `PUT` / `DELETE` / `PATCH` / `HEAD` / `OPTIONS` | `/static/path` | 精确匹配 |
| — | `/user/:id` | 路径参数，`ctx->Param("id")` |
| — | `/static/*filepath` | 通配符，`ctx->Param("filepath")` |

### 中间件

```cpp
app.Use(ylmz::Logger());                           // 请求日志
app.Use(ylmz::Recovery());                         // panic 恢复
app.Use(ylmz::CORS("*", "GET,POST", "Content-Type")); // 跨域
```

### Context 常用方法

```cpp
// 请求
ctx->Method()              // "GET" / "POST" / ...
ctx->Path()                // "/user/42"
ctx->Param("id")           // "42"
ctx->Query("name")         // query string
ctx->GetJSON()             // 解析 JSON body
ctx->GetHeader("Host")     // 请求头

// 响应
ctx->String(200, "OK")
ctx->JSON(200, {{"msg", "hello"}})
ctx->HTML(200, "<h1>Hello</h1>")
ctx->Data(200, "image/png", binary_data)
ctx->SetHeader("X-Custom", "value")
```

## 目录结构

```
ylmz-cc/
├── include/ylmz/
│   ├── ylmz.h              # 主入口
│   ├── app.h               # App 框架类
│   ├── router.h            # Radix Tree 路由器
│   ├── context.h           # 请求/响应上下文
│   ├── middleware.h         # 内置中间件
│   ├── event_loop.h        # epoll/kqueue 事件循环
│   ├── http_parser.h       # HTTP/1.1 状态机解析器
│   ├── ws.h                # WebSocket (RFC 6455)
│   └── tcp.h               # TCP 服务器
├── src/                    # 实现文件
├── examples/               # 示例代码
├── tests/                  # 单元测试
├── Makefile
└── CMakeLists.txt          # 备用 CMake 构建
```

## 许可证

MIT
