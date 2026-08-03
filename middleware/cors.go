package middleware

import (
	"net/http"
	"strconv"
	"strings"

	"github.com/ylmzfun/ylmz-go/ylmz"
)

// CORSConfig holds the CORS middleware configuration.
type CORSConfig struct {
	// AllowOrigins is a list of allowed origins.
	AllowOrigins []string

	// AllowMethods is a list of allowed HTTP methods.
	AllowMethods []string

	// AllowHeaders is a list of allowed request headers.
	AllowHeaders []string

	// ExposeHeaders is a list of headers exposed to the client.
	ExposeHeaders []string

	// AllowCredentials indicates whether credentials are allowed.
	AllowCredentials bool

	// MaxAge is the max age for preflight caching (seconds).
	MaxAge int

	// AllowWildcard enables wildcard origin matching.
	AllowWildcard bool
}

// DefaultCORSConfig returns a sensible default config.
func DefaultCORSConfig() CORSConfig {
	return CORSConfig{
		AllowOrigins: []string{"*"},
		AllowMethods: []string{"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"},
		AllowHeaders: []string{"Origin", "Content-Type", "Accept", "Authorization", "X-Request-ID"},
	}
}

// CORS returns a CORS middleware with default config.
func CORS() ylmz.HandlerFunc {
	return CORSWithConfig(DefaultCORSConfig())
}

// CORSWithConfig returns a CORS middleware with custom config.
func CORSWithConfig(cfg CORSConfig) ylmz.HandlerFunc {
	if len(cfg.AllowMethods) == 0 {
		cfg.AllowMethods = []string{"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
	}
	if len(cfg.AllowHeaders) == 0 {
		cfg.AllowHeaders = []string{"Origin", "Content-Type", "Accept", "Authorization"}
	}
	allowMethods := strings.Join(cfg.AllowMethods, ", ")
	allowHeaders := strings.Join(cfg.AllowHeaders, ", ")
	exposeHeaders := strings.Join(cfg.ExposeHeaders, ", ")

	allowAllOrigins := false
	for _, origin := range cfg.AllowOrigins {
		if origin == "*" {
			allowAllOrigins = true
			break
		}
	}

	return func(c *ylmz.Context) {
		origin := c.GetHeader("Origin")

		if origin == "" {
			c.Next()
			return
		}

		allowed := false
		if allowAllOrigins {
			allowed = true
			c.Header("Access-Control-Allow-Origin", "*")
		} else {
			for _, allowedOrigin := range cfg.AllowOrigins {
				if allowedOrigin == origin {
					allowed = true
					c.Header("Access-Control-Allow-Origin", origin)
					break
				}
			}
		}

		if cfg.AllowCredentials && !allowAllOrigins {
			c.Header("Access-Control-Allow-Credentials", "true")
		}

		if c.Request.Method == http.MethodOptions {
			// Preflight
			c.Header("Access-Control-Allow-Methods", allowMethods)
			c.Header("Access-Control-Allow-Headers", allowHeaders)
			if cfg.MaxAge > 0 {
				c.Header("Access-Control-Max-Age", strconv.Itoa(cfg.MaxAge))
			}
			if exposeHeaders != "" {
				c.Header("Access-Control-Expose-Headers", exposeHeaders)
			}
			c.AbortWithStatus(http.StatusNoContent)
			return
		}

		if exposeHeaders != "" {
			c.Header("Access-Control-Expose-Headers", exposeHeaders)
		}

		if !allowed {
			c.AbortWithStatusJSON(http.StatusForbidden, ylmz.H{
				"error": "origin not allowed",
			})
			return
		}

		c.Next()
	}
}
