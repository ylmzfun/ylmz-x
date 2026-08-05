# ylmz

> 一个受 Lumen 启发的轻量级 C# Web 微框架，构建于 ASP.NET Core Kestrel 之上。

[![.NET](https://img.shields.io/badge/.NET-8.0-512BD4?logo=dotnet)](https://dotnet.microsoft.com/)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

---

## 快速开始

```bash
# 1. 克隆项目
git clone <repo-url> && cd ylmz-c#

# 2. 运行示例应用
dotnet run --project examples/BasicApp
# → http://localhost:5000
```

### 30 秒示例

```csharp
using ylmz;

var app = new Application();

app.Get("/", async (req, res) =>
{
    await res.Json(new { message = "Hello, ylmz!" });
});

app.Get("/hello/{name}", async (req, res) =>
{
    var name = req.RouteParam("name");
    await res.Json(new { greeting = $"Hello, {name}!" });
});

await app.WithUrls("http://localhost:5000").RunAsync();
```

---

## 特性

| 模块 | 说明 |
|---|---|
| **路由** | `Get` / `Post` / `Put` / `Patch` / `Delete` / `Any`，支持 `{param}` 参数和 `{id:int}` 类型约束 |
| **路由组** | `app.Group("/prefix", group => { ... })` — 共享前缀，类似 Lumen `$router->group()` |
| **中间件** | `app.AddMiddleware(...)` — 洋葱模型管道，类似 Lumen `$app->middleware()` |
| **控制器** | 继承 `Controller` 基类，自动注入 `Request` / `Response` |
| **依赖注入** | 内置 `ServiceContainer`，支持 `Singleton` / `Transient` |
| **JSON** | `res.Json()` / `req.BindAsync<T>()`，基于 `System.Text.Json` |

---

## 项目结构

```
ylmz-c#/
├── ylmz.sln
├── src/
│   └── ylmz/                    # 框架核心
│       ├── ylmz.csproj
│       ├── Application.cs       # 应用入口 / 构建器
│       ├── Http/
│       │   ├── Request.cs       # HTTP 请求封装（Query/Route/Body）
│       │   └── Response.cs      # HTTP 响应封装（Json/Text/Html）
│       ├── Routing/
│       │   ├── Route.cs         # 路由定义 + URL 模式匹配
│       │   ├── RouteCollection.cs  # 路由组
│       │   └── Router.cs        # 路由注册与分发
│       ├── Middleware/
│       │   └── MiddlewarePipeline.cs  # 中间件管道
│       ├── Controllers/
│       │   └── Controller.cs    # 控制器基类
│       └── Container/
│           └── ServiceContainer.cs  # 轻量 DI 容器
└── examples/
    └── BasicApp/                # 示例应用
        ├── BasicApp.csproj
        ├── Program.cs
        └── Controllers/
            └── HomeController.cs
```

---

## 核心 API

### Application 构建器

```csharp
var app = new Application();

// 配置
app.WithUrls("http://localhost:5000")
   .WithEnvironment("development");

// 启动
await app.RunAsync();
```

### 路由

```csharp
// 基本路由
app.Get("/users", handler);
app.Post("/users", handler);
app.Put("/users/{id}", handler);
app.Delete("/users/{id}", handler);

// 路由参数 + 约束
app.Get("/users/{id:int}", handler);      // 只匹配数字
app.Get("/files/{*path}", handler);      // 通配符

// 获取路由参数
var id = req.RouteParam("id");
var id = req.RouteParam<int>("id");
```

### 路由组

```csharp
app.Group("/api/v1", group =>
{
    group.Get("/items", handler);
    group.Get("/items/{id}", handler);
    group.Post("/items", handler);
});
```

### 中间件

```csharp
// 日志中间件
app.AddMiddleware(async (req, res, next) =>
{
    Console.WriteLine($"{req.Method} {req.Path}");
    await next();
});

// CORS 中间件
app.AddMiddleware(async (req, res, next) =>
{
    res.Header("Access-Control-Allow-Origin", "*");
    if (req.Method == "OPTIONS") { res.StatusCode = 204; return; }
    await next();
});
```

### 控制器

```csharp
public class UserController : Controller
{
    public async Task Index()
    {
        var users = new[] { new { id = 1, name = "Alice" } };
        await Json(new { data = users });
    }

    public async Task Show()
    {
        var id = RouteParam<int>("id");
        await Json(new { id, name = $"User {id}" });
    }

    public async Task Store()
    {
        var body = await BindAsync<Dictionary<string, object?>>();
        await Json(new { created = true, user = body }, 201);
    }
}

// 注册控制器路由
app.Get("/users", Application.Controller<UserController>(nameof(UserController.Index)));
app.Get("/users/{id:int}", Application.Controller<UserController>(nameof(UserController.Show)));
app.Post("/users", Application.Controller<UserController>(nameof(UserController.Store)));
```

### 请求 / 响应

```csharp
// Request
req.Method                     // "GET" | "POST" | ...
req.Path                       // "/api/users"
req.RouteParam("id")           // 路由参数
req.QueryParam("page")         // Query 参数
req.Header("Authorization")    // 请求头
await req.BodyAsync()          // 原始 body
await req.BindAsync<T>()       // JSON → 对象

// Response
await res.Json(data, 200);     // JSON 响应
await res.Text("ok", 200);     // 纯文本
await res.Html("<h1>hi</h1>"); // HTML
res.Status(201);               // 设置状态码
res.Header("X-Custom", "v");   // 设置响应头
```

### 依赖注入

```csharp
app.AddSingleton<IMyService, MyServiceImpl>();
app.AddSingleton<IMyService>(new MyServiceImpl());
app.AddTransient<IMyRepository, MyRepository>();

// 在控制器或中间件中通过容器获取
var svc = app.Resolve<IMyService>();
```

---

## 与 Lumen 对比

| Lumen | ylmz |
|---|---|
| `$router->get('/path', fn)` | `app.Get("/path", handler)` |
| `$router->group(['prefix' => '/api'], fn)` | `app.Group("/api", group => { ... })` |
| `$app->middleware(fn)` | `app.AddMiddleware(async (req, res, next) => ...)` |
| `$app->singleton(Iface::class, Impl::class)` | `app.AddSingleton<Iface, Impl>()` |
| `return response()->json($data)` | `await res.Json(data)` |
| `$request->input('key')` | `req.QueryParam("key")` |
| `$request->route('id')` | `req.RouteParam("id")` |
| `$request->all()` | `await req.BindAsync<T>()` |

---

## 环境要求

- [.NET 8.0 SDK](https://dotnet.microsoft.com/download/dotnet/8.0) 或更高版本

## License

MIT
