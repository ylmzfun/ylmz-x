package middleware

import (
	"crypto/rand"
	"fmt"

	"github.com/ylmzfun/ylmz-go/ylmz"
)

// RequestIDConfig holds request ID configuration.
type RequestIDConfig struct {
	// HeaderName is the header to check/generate (default: X-Request-ID).
	HeaderName string
}

// RequestID returns a middleware that injects a request ID into each request.
func RequestID() ylmz.HandlerFunc {
	return RequestIDWithConfig(RequestIDConfig{HeaderName: "X-Request-ID"})
}

// RequestIDWithConfig returns a request ID middleware with custom config.
func RequestIDWithConfig(cfg RequestIDConfig) ylmz.HandlerFunc {
	if cfg.HeaderName == "" {
		cfg.HeaderName = "X-Request-ID"
	}

	return func(c *ylmz.Context) {
		id := c.GetHeader(cfg.HeaderName)
		if id == "" {
			id = generateID()
		}
		c.Set("request_id", id)
		c.Header(cfg.HeaderName, id)
		c.Next()
	}
}

func generateID() string {
	b := make([]byte, 16)
	rand.Read(b)
	return fmt.Sprintf("%x-%x-%x-%x-%x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:])
}
