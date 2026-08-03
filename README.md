# ylmz-go

一个比 Gin 更全面的 Go Web 框架。核心轻量、零外部依赖，内置丰富的中间件生态和开箱即用的辅助模块。

## 特性

| 功能 | ylmz-go | Gin |
|------|---------|-----|
| 路由 | Radix Tree + 参数/通配符 | Radix Tree |
| 中间件 | 内置 **11 个**常用中间件 | 需自行引入 |
| 参数绑定 | JSON/XML/Form/Query/Header/URI + 文件上传 | JSON/XML/Form |
| 验证器 | 内置验证器，中文错误信息 | go-playground/validator |
| 错误信息 | 类型化错误体系 | 简单 error |
| 配置管理 | JSON + 环境变量 | ❌ |
| 日志 | 结构化分级日志（彩色） | ❌ |
| 缓存 | 内存缓存（TTL + 自动清理） | ❌ |
| 会话管理 | Cookie + 可插拔存储 | ❌ |
| OpenAPI | 自动生成 Swagger 文档 + UI | ❌ |
| WebSocket | 纯标准库实现 | 需 gorilla/websocket |
| 健康检查 | /health + /ready 端点 | ❌ |
| 优雅关闭 | 内置信号处理 | ❌ |
| CLI 工具 | 项目脚手架 | ❌ |

## 快速开始

### 安装

```bash
go get github.com/ylmzfun/ylmz-go
```

### 最小示例

```go
package main

import "github.com/ylmzfun/ylmz-go/ylmz"

func main() {
    r := ylmz.New()
    r.GET("/ping", func(c *ylmz.Context) {
        c.JSON(200, ylmz.H{"message": "pong"})
    })
    r.Run(":8080")
}
```

### 绑定与验证

```go
type CreateUser struct {
    Name  string `json:"name" validate:"required,min=2,max=50"`
    Email string `json:"email" validate:"required,email"`
    Age   int    `json:"age" validate:"gte=0,lte=130"`
}

r.POST("/users", func(c *ylmz.Context) {
    var user CreateUser
    if err := c.ShouldBindJSON(&user); err != nil {
        c.JSON(400, ylmz.H{"error": err.Error()})
        return
    }
    c.JSON(201, user)
})
```

### 中间件

```go
r := ylmz.New()

// 全局中间件
r.Use(middleware.Logger())
r.Use(middleware.Recovery())
r.Use(middleware.CORS())
r.Use(middleware.RequestID())

// 路由组中间件
admin := r.Group("/admin")
admin.Use(middleware.JWT([]byte("secret")))
{
    admin.GET("/dashboard", handler)
}

// 限流
limited := r.Group("/api")
limited.Use(middleware.RateLimit(100, time.Minute))
```

### 路由

```go
// 参数路由
r.GET("/users/:id", func(c *ylmz.Context) {
    id := c.Param("id")
    c.JSON(200, ylmz.H{"id": id})
})

// 通配符路由
r.GET("/static/*filepath", func(c *ylmz.Context) {
    filepath := c.Param("filepath")
    c.File("./public/" + filepath)
})

// 路由分组
v1 := r.Group("/api/v1")
{
    v1.GET("/users", listUsers)
    v1.POST("/users", createUser)
}
```

### WebSocket

```go
r.GET("/ws", websocket.Handler(func(conn *websocket.Conn) error {
    for {
        msg, err := conn.ReadMessage()
        if err != nil {
            return nil
        }
        conn.WriteMessage(1, []byte("Echo: "+string(msg.Data)))
    }
}))
```

### Swagger 文档

```go
swag := swagger.New(swagger.Info{
    Title:   "My API",
    Version: "1.0.0",
})
swag.AddRoute(swagger.RouteDef{
    Method:   "POST",
    Path:     "/api/v1/users",
    Summary:  "创建用户",
    Tags:     []string{"Users"},
    Request:  CreateUser{},
    Response: UserResponse{},
})

r.GET("/swagger.json", swag.Handler())
r.GET("/docs", swagger.SwaggerUI("/swagger.json"))
```

### 优雅关闭

```go
r.RunWithShutdown(":8080") // 监听 SIGINT / SIGTERM
```

## 内置中间件一览

| 中间件 | 说明 |
|--------|------|
| `Logger()` | 彩色结构化请求日志 |
| `Recovery()` | Panic 恢复，防止服务崩溃 |
| `CORS()` | 跨域资源共享 |
| `JWT(secret)` | JWT 鉴权（HS256） |
| `RateLimit(rate, period)` | 令牌桶限流 |
| `CSRF()` | CSRF 令牌防护 |
| `BasicAuth(accounts)` | HTTP Basic 认证 |
| `BearerToken(token)` | Bearer Token 认证 |
| `Timeout(duration)` | 请求超时 |
| `Gzip(level)` | Gzip 压缩 |
| `SecurityHeaders()` | 安全响应头 |
| `RequestID()` | 请求 ID 注入 |
| `CacheControl(maxAge)` | 缓存控制头 |
| `NoCache()` | 禁止缓存 |

## 内置验证规则

| 规则 | 说明 |
|------|------|
| `required` | 必填 |
| `min=n` / `max=n` | 最小/最大值或长度 |
| `len=n` | 精确长度 |
| `gte=n` / `lte=n` | 大于等于 / 小于等于 |
| `email` | 邮箱格式 |
| `url` | URL 格式 |
| `regex=pattern` | 正则匹配 |
| `oneof=a b c` | 枚举值 |
| `alpha` / `alphanum` / `numeric` | 字符类型 |

## 辅助模块

```go
// 配置
cfg := &MyConfig{}
config.Load(cfg, &config.JSONLoader{Path: "config.json"})
config.LoadEnv("APP", cfg)

// 日志
log.Info("server started", log.Field{Key: "port", Value: 8080})
logger := log.New(log.Config{Level: log.DebugLevel})

// 缓存
c := cache.NewMemory(5 * time.Minute)
c.Set("key", "value", time.Hour)
val, ok := c.Get("key")

// 会话
r.Use(session.Middleware(session.DefaultConfig()))
sess := c.MustGet("session").(*session.Session)
```

## CLI 工具

```bash
# 创建新项目
go run cmd/ylmz/main.go new my-project

# 进入项目
cd my-project
go run cmd/server/main.go
```

## 项目结构

```
ylmz-go/
├── ylmz/            # 核心引擎（零外部依赖）
├── middleware/       # 内置中间件
├── config/          # 配置管理
├── log/             # 结构化日志
├── cache/           # 内存缓存
├── session/         # 会话管理
├── websocket/       # WebSocket
├── swagger/         # OpenAPI 文档
├── health/          # 健康检查
├── cmd/ylmz/        # CLI 脚手架
└── examples/basic/  # 综合示例
```

## License

MIT
