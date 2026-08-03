package middleware

import (
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"runtime"
	"strings"

	"github.com/ylmzfun/ylmz-go/ylmz"
)

// RecoveryConfig holds configuration for the recovery middleware.
type RecoveryConfig struct {
	// StackSize is the max stack trace size (default: 4KB).
	StackSize int

	// DisableStackAll disables the full stack trace.
	DisableStackAll bool

	// DisablePrintStack disables printing stack to stderr.
	DisablePrintStack bool

	// RecoveryHandler is a custom handler for panic recovery.
	RecoveryHandler func(c *ylmz.Context, err any)
}

// Recovery returns a middleware that recovers from panics.
func Recovery() ylmz.HandlerFunc {
	return RecoveryWithConfig(RecoveryConfig{})
}

// RecoveryWithConfig returns a recovery middleware with custom config.
func RecoveryWithConfig(cfg RecoveryConfig) ylmz.HandlerFunc {
	if cfg.StackSize == 0 {
		cfg.StackSize = 4 << 10 // 4KB
	}

	logger := log.New(os.Stderr, "\n[ylmz-recovery] ", log.LstdFlags)

	return func(c *ylmz.Context) {
		defer func() {
			if err := recover(); err != nil {
				// Check for broken pipe
				var brokenPipe bool
				if ne, ok := err.(*net.OpError); ok {
					if se, ok := ne.Err.(*os.SyscallError); ok {
						if strings.Contains(strings.ToLower(se.Error()), "broken pipe") ||
							strings.Contains(strings.ToLower(se.Error()), "connection reset by peer") {
							brokenPipe = true
						}
					}
				}

				stack := make([]byte, cfg.StackSize)
				stack = stack[:runtime.Stack(stack, cfg.DisableStackAll)]

				if !cfg.DisablePrintStack && !brokenPipe {
					logger.Printf("panic recovered: %v\n%s\n", err, stack)
				}

				if brokenPipe {
					c.Error(fmt.Errorf("broken pipe: %v", err))
					c.Abort()
					return
				}

				if cfg.RecoveryHandler != nil {
					cfg.RecoveryHandler(c, err)
					return
				}

				c.AbortWithStatusJSON(http.StatusInternalServerError, ylmz.H{
					"error":   "Internal Server Error",
					"message": fmt.Sprintf("%v", err),
				})
			}
		}()
		c.Next()
	}
}
