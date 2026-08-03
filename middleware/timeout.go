package middleware

import (
	"context"
	"net/http"
	"time"

	"github.com/ylmzfun/ylmz-go/ylmz"
)

// Timeout returns a middleware that sets a request timeout.
func Timeout(duration time.Duration) ylmz.HandlerFunc {
	return func(c *ylmz.Context) {
		ctx, cancel := context.WithTimeout(c.Request.Context(), duration)
		defer cancel()

		c.Request = c.Request.WithContext(ctx)

		done := make(chan struct{})
		go func() {
			c.Next()
			close(done)
		}()

		select {
		case <-ctx.Done():
			if ctx.Err() == context.DeadlineExceeded {
				c.AbortWithStatusJSON(http.StatusGatewayTimeout, ylmz.H{
					"error": "request timeout",
				})
			}
		case <-done:
		}
	}
}
