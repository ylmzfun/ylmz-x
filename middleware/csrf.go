package middleware

import (
	"crypto/rand"
	"encoding/base64"
	"net/http"
	"strings"

	"github.com/ylmzfun/ylmz-go/ylmz"
)

// CSRFConfig holds CSRF protection configuration.
type CSRFConfig struct {
	// TokenLength is the CSRF token length in bytes.
	TokenLength int

	// CookieName is the name of the CSRF cookie.
	CookieName string

	// HeaderName is the name of the CSRF header.
	HeaderName string

	// FieldName is the name of the form field for CSRF token.
	FieldName string

	// SkipMethods are HTTP methods that skip CSRF validation.
	SkipMethods []string
}

// DefaultCSRFConfig returns a sensible default config.
func DefaultCSRFConfig() CSRFConfig {
	return CSRFConfig{
		TokenLength: 32,
		CookieName:  "_csrf",
		HeaderName:  "X-CSRF-Token",
		FieldName:   "_csrf",
		SkipMethods: []string{"GET", "HEAD", "OPTIONS", "TRACE"},
	}
}

// CSRF returns a CSRF protection middleware.
func CSRF() ylmz.HandlerFunc {
	return CSRFWithConfig(DefaultCSRFConfig())
}

// CSRFWithConfig returns a CSRF middleware with custom config.
func CSRFWithConfig(cfg CSRFConfig) ylmz.HandlerFunc {
	if cfg.TokenLength == 0 {
		cfg.TokenLength = 32
	}
	if cfg.CookieName == "" {
		cfg.CookieName = "_csrf"
	}
	if cfg.HeaderName == "" {
		cfg.HeaderName = "X-CSRF-Token"
	}
	if cfg.FieldName == "" {
		cfg.FieldName = "_csrf"
	}
	if len(cfg.SkipMethods) == 0 {
		cfg.SkipMethods = []string{"GET", "HEAD", "OPTIONS", "TRACE"}
	}

	skipMethods := make(map[string]bool, len(cfg.SkipMethods))
	for _, m := range cfg.SkipMethods {
		skipMethods[strings.ToUpper(m)] = true
	}

	return func(c *ylmz.Context) {
		// Get or generate CSRF token
		token, err := c.Cookie(cfg.CookieName)
		if err != nil || token == "" {
			token = generateCSRFToken(cfg.TokenLength)
			c.SetSameSite(cfg.CookieName, token, 0, "/", "", false, false, http.SameSiteStrictMode)
		}

		// Store token in context for template rendering
		c.Set("csrf_token", token)
		c.Set("csrf_field", `<input type="hidden" name="`+cfg.FieldName+`" value="`+token+`">`)
		c.Set("csrf_header", cfg.HeaderName)

		// Skip safe methods
		if skipMethods[c.Request.Method] {
			c.Next()
			return
		}

		// Validate token
		clientToken := c.GetHeader(cfg.HeaderName)
		if clientToken == "" {
			clientToken = c.PostForm(cfg.FieldName)
		}

		if clientToken == "" || clientToken != token {
			c.AbortWithStatusJSON(http.StatusForbidden, ylmz.H{
				"error": "CSRF token missing or invalid",
			})
			return
		}

		c.Next()
	}
}

func generateCSRFToken(length int) string {
	b := make([]byte, length)
	rand.Read(b)
	return base64.RawURLEncoding.EncodeToString(b)
}
