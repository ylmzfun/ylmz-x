// Package health provides health check endpoints.
package health

import (
	"net/http"
	"sync"
	"time"

	"github.com/ylmzfun/ylmz-go/ylmz"
)

// Checker is a function that returns an error if unhealthy.
type Checker func() error

// Health holds registered health checkers.
type Health struct {
	mu       sync.RWMutex
	checks   map[string]Checker
	started  time.Time
}

// New creates a new Health instance.
func New() *Health {
	return &Health{
		checks:  make(map[string]Checker),
		started: time.Now(),
	}
}

// Register adds a health checker.
func (h *Health) Register(name string, check Checker) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.checks[name] = check
}

// Handler returns a /health endpoint handler.
func (h *Health) Handler() ylmz.HandlerFunc {
	return func(c *ylmz.Context) {
		h.mu.RLock()
		defer h.mu.RUnlock()

		type checkResult struct {
			Status  string `json:"status"`
			Message string `json:"message,omitempty"`
		}

		result := ylmz.H{
			"status":    "ok",
			"uptime":    time.Since(h.started).String(),
			"timestamp": time.Now().Format(time.RFC3339),
		}

		checks := make(map[string]checkResult)
		allHealthy := true

		for name, check := range h.checks {
			if err := check(); err != nil {
				checks[name] = checkResult{
					Status:  "unhealthy",
					Message: err.Error(),
				}
				allHealthy = false
			} else {
				checks[name] = checkResult{Status: "healthy"}
			}
		}

		if len(checks) > 0 {
			result["checks"] = checks
		}
		if !allHealthy {
			result["status"] = "degraded"
			c.JSON(http.StatusServiceUnavailable, result)
			return
		}

		c.JSON(http.StatusOK, result)
	}
}

// ReadyHandler returns a simple readiness check.
func ReadyHandler() ylmz.HandlerFunc {
	return func(c *ylmz.Context) {
		c.JSON(http.StatusOK, ylmz.H{
			"status": "ready",
		})
	}
}

// PingHandler returns a simple ping-pong handler.
func PingHandler() ylmz.HandlerFunc {
	return func(c *ylmz.Context) {
		c.String(http.StatusOK, "pong")
	}
}
