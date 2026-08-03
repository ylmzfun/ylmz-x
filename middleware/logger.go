// Package middleware provides a collection of HTTP middleware for the ylmz framework.
package middleware

import (
	"fmt"
	"log"
	"os"
	"time"

	"github.com/ylmzfun/ylmz-go/ylmz"
)

// LoggerConfig holds configuration for the logger middleware.
type LoggerConfig struct {
	// Output is the writer for log output (default: os.Stdout).
	Output *os.File

	// Formatter is a custom log formatter function.
	Formatter func(params LogFormatterParams) string

	// SkipPaths is a list of paths to skip logging.
	SkipPaths []string
}

// LogFormatterParams holds data for log formatting.
type LogFormatterParams struct {
	// TimeStamp is the time the request was made.
	TimeStamp time.Time

	// StatusCode is the HTTP response code.
	StatusCode int

	// Latency is the request processing time.
	Latency time.Duration

	// ClientIP is the client's IP address.
	ClientIP string

	// Method is the HTTP method.
	Method string

	// Path is the request path.
	Path string

	// BodySize is the response body size in bytes.
	BodySize int

	// ErrorMessage contains error messages if any.
	ErrorMessage string
}

var defaultLogFormatter = func(params LogFormatterParams) string {
	statusColor := colorForStatus(params.StatusCode)
	resetColor := colorReset
	if params.ErrorMessage != "" {
		return fmt.Sprintf("[ylmz] %v |%s %3d %s| %13v | %15s | %-7s %s %s\n",
			params.TimeStamp.Format("2006/01/02 - 15:04:05"),
			statusColor, params.StatusCode, resetColor,
			params.Latency,
			params.ClientIP,
			params.Method,
			params.Path,
			params.ErrorMessage,
		)
	}
	return fmt.Sprintf("[ylmz] %v |%s %3d %s| %13v | %15s | %-7s %s\n",
		params.TimeStamp.Format("2006/01/02 - 15:04:05"),
		statusColor, params.StatusCode, resetColor,
		params.Latency,
		params.ClientIP,
		params.Method,
		params.Path,
	)
}

// Logger returns a middleware that logs each request.
func Logger() ylmz.HandlerFunc {
	return LoggerWithConfig(LoggerConfig{})
}

// LoggerWithConfig returns a logger middleware with custom configuration.
func LoggerWithConfig(cfg LoggerConfig) ylmz.HandlerFunc {
	if cfg.Output == nil {
		cfg.Output = os.Stdout
	}
	if cfg.Formatter == nil {
		cfg.Formatter = defaultLogFormatter
	}

	logger := log.New(cfg.Output, "", 0)
	skipPaths := make(map[string]bool, len(cfg.SkipPaths))
	for _, path := range cfg.SkipPaths {
		skipPaths[path] = true
	}

	return func(c *ylmz.Context) {
		start := time.Now()
		path := c.Request.URL.Path

		if skipPaths[path] {
			c.Next()
			return
		}

		c.Next()

		latency := time.Since(start)
		params := LogFormatterParams{
			TimeStamp: time.Now(),
			StatusCode: c.Writer.Status(),
			Latency:   latency,
			ClientIP:  c.ClientIP(),
			Method:    c.Request.Method,
			Path:      path,
			BodySize:  c.Writer.Size(),
		}

		if len(c.Errors) > 0 {
			params.ErrorMessage = c.Errors.String()
		}

		logger.Print(cfg.Formatter(params))
	}
}

// Color helpers for terminal output.
const (
	colorGreen  = "\033[32m"
	colorYellow = "\033[33m"
	colorRed    = "\033[31m"
	colorCyan   = "\033[36m"
	colorReset  = "\033[0m"
)

func colorForStatus(code int) string {
	switch {
	case code >= 200 && code < 300:
		return colorGreen
	case code >= 300 && code < 400:
		return colorCyan
	case code >= 400 && code < 500:
		return colorYellow
	default:
		return colorRed
	}
}
