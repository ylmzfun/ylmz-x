package middleware

import (
	"encoding/base64"
	"net/http"
	"strings"

	"github.com/ylmzfun/ylmz-go/ylmz"
)

// BasicAuth returns a basic authentication middleware.
func BasicAuth(accounts map[string]string) ylmz.HandlerFunc {
	return func(c *ylmz.Context) {
		auth := c.GetHeader("Authorization")
		if auth == "" || !strings.HasPrefix(auth, "Basic ") {
			c.Header("WWW-Authenticate", `Basic realm="Restricted"`)
			c.AbortWithStatusJSON(http.StatusUnauthorized, ylmz.H{
				"error": "authorization required",
			})
			return
		}

		payload, err := base64.StdEncoding.DecodeString(auth[6:])
		if err != nil {
			c.AbortWithStatus(http.StatusUnauthorized)
			return
		}

		pair := strings.SplitN(string(payload), ":", 2)
		if len(pair) != 2 {
			c.AbortWithStatus(http.StatusUnauthorized)
			return
		}

		password, ok := accounts[pair[0]]
		if !ok || password != pair[1] {
			c.AbortWithStatusJSON(http.StatusUnauthorized, ylmz.H{
				"error": "invalid credentials",
			})
			return
		}

		c.Set("auth_user", pair[0])
		c.Next()
	}
}

// BearerToken returns a bearer token authentication middleware.
func BearerToken(token string) ylmz.HandlerFunc {
	return func(c *ylmz.Context) {
		auth := c.GetHeader("Authorization")
		if auth == "" || !strings.HasPrefix(auth, "Bearer ") {
			c.AbortWithStatusJSON(http.StatusUnauthorized, ylmz.H{
				"error": "bearer token required",
			})
			return
		}

		if auth[7:] != token {
			c.AbortWithStatusJSON(http.StatusUnauthorized, ylmz.H{
				"error": "invalid bearer token",
			})
			return
		}

		c.Next()
	}
}
