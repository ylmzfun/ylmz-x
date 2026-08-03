// Example: Comprehensive ylmz framework usage demonstration
package main

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/ylmzfun/ylmz-go/config"
	"github.com/ylmzfun/ylmz-go/health"
	"github.com/ylmzfun/ylmz-go/log"
	"github.com/ylmzfun/ylmz-go/middleware"
	"github.com/ylmzfun/ylmz-go/swagger"
	"github.com/ylmzfun/ylmz-go/websocket"
	"github.com/ylmzfun/ylmz-go/ylmz"
)

// AppConfig demonstrates config management.
type AppConfig struct {
	ServerPort string `json:"server_port" env:"SERVER_PORT"`
	AppName    string `json:"app_name" env:"APP_NAME"`
	DebugMode  bool   `json:"debug_mode" env:"DEBUG_MODE"`
}

// ==================== Request/Response Models ====================

// CreateUserRequest demonstrates request binding and validation.
type CreateUserRequest struct {
	Name  string `json:"name" form:"name" validate:"required,min=2,max=50"`
	Email string `json:"email" form:"email" validate:"required,email"`
	Age   int    `json:"age" form:"age" validate:"gte=0,lte=130"`
	Role  string `json:"role" form:"role" validate:"oneof=admin user guest"`
}

// UserResponse demonstrates response structures.
type UserResponse struct {
	ID    string `json:"id"`
	Name  string `json:"name"`
	Email string `json:"email"`
	Age   int    `json:"age"`
	Role  string `json:"role"`
}

// PaginatedResponse demonstrates pagination.
type PaginatedResponse struct {
	Data       any   `json:"data"`
	Total      int64 `json:"total"`
	Page       int   `json:"page"`
	PageSize   int   `json:"page_size"`
	TotalPages int   `json:"total_pages"`
}

func main() {
	// ----- Config -----
	cfg := &AppConfig{
		ServerPort: "8080",
		AppName:    "ylmz-demo",
		DebugMode:  true,
	}

	// Load config from env (try APP_NAME, SERVER_PORT, DEBUG_MODE)
	config.LoadEnv("", cfg)

	// ----- Logger -----
	logger := log.New(log.Config{
		Level:        log.DebugLevel,
		EnableColor:  true,
		EnableCaller: false,
	})
	logger.Info("Starting application", log.Field{Key: "app", Value: cfg.AppName})

	// ----- Engine -----
	r := ylmz.New()

	// Global middleware
	r.Use(middleware.Recovery())
	r.Use(middleware.Logger())
	r.Use(middleware.CORS())
	r.Use(middleware.RequestID())
	r.Use(middleware.SecurityHeaders())

	// ----- Swagger / OpenAPI -----
	swag := swagger.New(swagger.Info{
		Title:       "ylmz-go Demo API",
		Description: "A comprehensive demo of the ylmz-go framework",
		Version:     "1.0.0",
	})
	swag.AddServer("http://localhost:"+cfg.ServerPort, "Development server")

	r.GET("/swagger.json", swag.Handler())
	r.GET("/docs", swagger.SwaggerUI("/swagger.json"))

	// ----- Health Checks -----
	h := health.New()
	h.Register("database", func() error {
		// Simulate DB check
		return nil
	})
	h.Register("cache", func() error {
		return nil
	})
	r.GET("/health", h.Handler())
	r.GET("/ready", health.ReadyHandler())
	r.GET("/ping", health.PingHandler())

	// ----- API Routes -----
	api := r.Group("/api/v1")
	{
		// JSON binding + validation
		api.POST("/users", createUser)
		swag.AddRoute(swagger.RouteDef{
			Method:   "POST",
			Path:     "/api/v1/users",
			Summary:  "Create a new user",
			Tags:     []string{"Users"},
			Request:  CreateUserRequest{},
			Response: UserResponse{},
		})

		// Query parameter binding
		api.GET("/users", listUsers)
		swag.AddRoute(swagger.RouteDef{
			Method:   "GET",
			Path:     "/api/v1/users",
			Summary:  "List users",
			Tags:     []string{"Users"},
			Response: PaginatedResponse{},
		})

		// Path parameter
		api.GET("/users/:id", getUserByID)
		swag.AddRoute(swagger.RouteDef{
			Method:  "GET",
			Path:    "/api/v1/users/:id",
			Summary: "Get user by ID",
			Tags:    []string{"Users"},
		})

		// Different response formats
		api.GET("/users/:id/xml", getUserAsXML)

		// Header binding
		api.GET("/headers", showHeaders)

		// Form binding
		api.POST("/login", login)
	}

	// ----- Protected Routes (JWT) -----
	secret := []byte("my-secret-key")
	authGroup := r.Group("/api/admin")
	authGroup.Use(middleware.JWT(secret))
	{
		authGroup.GET("/dashboard", func(c *ylmz.Context) {
			sub := c.GetString("jwt_sub")
			c.JSON(200, ylmz.H{
				"message": "Welcome to admin dashboard",
				"user":    sub,
			})
		})
	}

	// Login endpoint to get JWT token
	r.POST("/api/login", func(c *ylmz.Context) {
		var req struct {
			Username string `json:"username"`
			Password string `json:"password"`
		}
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(400, ylmz.H{"error": err.Error()})
			return
		}

		if req.Username == "admin" && req.Password == "admin123" {
			token, _ := middleware.GenerateJWT(secret, map[string]any{
				"sub": req.Username,
				"iat": time.Now().Unix(),
				"exp": time.Now().Add(24 * time.Hour).Unix(),
			})
			c.JSON(200, ylmz.H{"token": token})
			return
		}
		c.JSON(401, ylmz.H{"error": "invalid credentials"})
	})

	// ----- Rate Limited Route -----
	limitedGroup := r.Group("/api/limited")
	limitedGroup.Use(middleware.RateLimit(5, time.Minute))
	{
		limitedGroup.GET("/data", func(c *ylmz.Context) {
			c.JSON(200, ylmz.H{"message": "rate limited endpoint"})
		})
	}

	// ----- CSRF Protected Route -----
	csrfGroup := r.Group("/api/csrf")
	csrfGroup.Use(middleware.CSRF())
	{
		csrfGroup.POST("/submit", func(c *ylmz.Context) {
			c.JSON(200, ylmz.H{"message": "CSRF validated"})
		})
	}

	// ----- Basic Auth Route -----
	basicAuthGroup := r.Group("/api/basic")
	basicAuthAccounts := map[string]string{"admin": "secret"}
	basicAuthGroup.Use(middleware.BasicAuth(basicAuthAccounts))
	{
		basicAuthGroup.GET("/info", func(c *ylmz.Context) {
			user := c.GetString("auth_user")
			c.JSON(200, ylmz.H{"message": "authenticated", "user": user})
		})
	}

	// ----- WebSocket -----
	r.GET("/ws", websocket.Handler(func(conn *websocket.Conn) error {
		logger.Info("WebSocket connected")
		for {
			msg, err := conn.ReadMessage()
			if err != nil {
				logger.Info("WebSocket disconnected")
				return nil
			}
			logger.Info("Received", log.Field{Key: "msg", Value: string(msg.Data)})
			conn.WriteMessage(1, []byte("Echo: "+string(msg.Data)))
		}
	}))

	// ----- Static Files -----
	r.Static("/static", "./examples/basic/static")

	// ----- Error Handling -----
	r.NoRoute(func(c *ylmz.Context) {
		c.JSON(404, ylmz.H{"error": "route not found"})
	})
	r.NoMethod(func(c *ylmz.Context) {
		c.JSON(405, ylmz.H{"error": "method not allowed"})
	})

	// ----- Timeout Demo -----
	timeoutGroup := r.Group("/api/slow")
	timeoutGroup.Use(middleware.Timeout(2 * time.Second))
	{
		timeoutGroup.GET("/process", func(c *ylmz.Context) {
			// Simulate slow processing
			select {
			case <-time.After(3 * time.Second):
				c.JSON(200, ylmz.H{"message": "done"})
			case <-c.Request.Context().Done():
				return
			}
		})
	}

	// ----- Start Server -----
	addr := ":" + cfg.ServerPort
	logger.Info("Server starting", log.Field{Key: "addr", Value: addr})
	logger.Infof("Swagger docs: http://localhost%s/docs", addr)
	logger.Infof("Health check: http://localhost%s/health", addr)
	logger.Infof("WebSocket:    ws://localhost%s/ws", addr)

	if err := r.RunWithShutdown(addr); err != nil {
		logger.Fatal("Server failed", log.Field{Key: "error", Value: err})
	}
}

// ==================== Handlers ====================

func createUser(c *ylmz.Context) {
	var req CreateUserRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(400, ylmz.H{"error": "invalid request", "detail": err.Error()})
		return
	}

	user := UserResponse{
		ID:    fmt.Sprintf("user_%d", time.Now().UnixNano()),
		Name:  req.Name,
		Email: req.Email,
		Age:   req.Age,
		Role:  req.Role,
	}

	c.JSON(201, ylmz.H{"data": user})
}

func listUsers(c *ylmz.Context) {
	type queryParams struct {
		Page     int    `form:"page"`
		PageSize int    `form:"page_size"`
		Search   string `form:"search"`
	}
	var params queryParams
	params.Page = 1
	params.PageSize = 10

	if p := c.Query("page"); p != "" {
		fmt.Sscanf(p, "%d", &params.Page)
	}
	if s := c.Query("page_size"); s != "" {
		fmt.Sscanf(s, "%d", &params.PageSize)
	}
	params.Search = c.Query("search")

	// Simulate DB results
	users := []UserResponse{
		{ID: "1", Name: "Alice", Email: "alice@example.com", Age: 28, Role: "admin"},
		{ID: "2", Name: "Bob", Email: "bob@example.com", Age: 35, Role: "user"},
	}

	c.JSON(200, ylmz.H{
		"data": users,
		"pagination": ylmz.H{
			"page":     params.Page,
			"page_size": params.PageSize,
			"total":    2,
		},
	})
}

func getUserByID(c *ylmz.Context) {
	id := c.Param("id")
	user := UserResponse{
		ID:    id,
		Name:  "John Doe",
		Email: "john@example.com",
		Age:   30,
		Role:  "user",
	}
	c.JSON(200, ylmz.H{"data": user})
}

func getUserAsXML(c *ylmz.Context) {
	id := c.Param("id")
	type xmlResponse struct {
		XMLName struct{} `xml:"user"`
		ID      string   `xml:"id"`
		Name    string   `xml:"name"`
	}
	c.XML(200, xmlResponse{ID: id, Name: "John Doe"})
}

func showHeaders(c *ylmz.Context) {
	type headerInfo struct {
		Authorization string `header:"Authorization"`
		ContentType   string `header:"Content-Type"`
		UserAgent     string `header:"User-Agent"`
	}
	var info headerInfo
	c.ShouldBindHeader(&info)

	c.JSON(200, ylmz.H{
		"headers":     info,
		"client_ip":   c.ClientIP(),
		"user_agent":  c.GetHeader("User-Agent"),
		"content_type": c.ContentType(),
	})
}

func login(c *ylmz.Context) {
	type loginForm struct {
		Username string `form:"username" validate:"required"`
		Password string `form:"password" validate:"required,min=6"`
	}
	var form loginForm
	if err := c.ShouldBindForm(&form); err != nil {
		c.JSON(400, ylmz.H{"error": err.Error()})
		return
	}
	c.JSON(200, ylmz.H{"message": "login successful", "user": form.Username})
}

// Ensure unused imports are valid
var _ = json.Marshal
