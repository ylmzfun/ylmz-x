package middleware

import (
	"github.com/ylmzfun/ylmz-go/ylmz"
)

// SecurityHeaders returns a middleware that sets common security headers.
func SecurityHeaders() ylmz.HandlerFunc {
	return func(c *ylmz.Context) {
		c.Header("X-Content-Type-Options", "nosniff")
		c.Header("X-Frame-Options", "DENY")
		c.Header("X-XSS-Protection", "1; mode=block")
		c.Header("Referrer-Policy", "strict-origin-when-cross-origin")
		c.Header("X-Download-Options", "noopen")
		c.Header("X-Permitted-Cross-Domain-Policies", "none")
		c.Next()
	}
}

// CacheControl sets Cache-Control headers.
func CacheControl(maxAge string) ylmz.HandlerFunc {
	return func(c *ylmz.Context) {
		c.Header("Cache-Control", maxAge)
		c.Next()
	}
}

// NoCache sets no-cache headers.
func NoCache() ylmz.HandlerFunc {
	return func(c *ylmz.Context) {
		c.Header("Cache-Control", "no-cache, no-store, must-revalidate")
		c.Header("Pragma", "no-cache")
		c.Header("Expires", "0")
		c.Next()
	}
}
