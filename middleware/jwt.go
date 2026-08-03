package middleware

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"net/http"
	"strings"
	"time"

	"github.com/ylmzfun/ylmz-go/ylmz"
)

// JWTConfig holds the JWT middleware configuration.
type JWTConfig struct {
	// Secret is the HMAC signing key.
	Secret []byte

	// SigningMethod is the JWT signing algorithm (default: HS256).
	SigningMethod string

	// TokenLookup is where to look for the token: "header:Authorization", "query:token", "cookie:jwt".
	TokenLookup string

	// AuthScheme is the authorization header scheme (default: "Bearer").
	AuthScheme string

	// Claims is a function that returns a new claims instance.
	Claims func() jwtClaims

	// KeyFunc returns the signing key.
	KeyFunc func() []byte
}

type jwtClaims interface {
	Valid() error
}

// StandardClaims represents standard JWT claims.
type StandardClaims struct {
	Issuer    string `json:"iss,omitempty"`
	Subject   string `json:"sub,omitempty"`
	Audience  string `json:"aud,omitempty"`
	ExpiresAt int64  `json:"exp,omitempty"`
	IssuedAt  int64  `json:"iat,omitempty"`
	ID        string `json:"jti,omitempty"`
}

// Valid implements jwtClaims.
func (s *StandardClaims) Valid() error {
	if s.ExpiresAt > 0 && time.Now().Unix() > s.ExpiresAt {
		return nil // expired but no error for claims validation
	}
	return nil
}

// JWT returns a JWT authentication middleware.
func JWT(secret []byte) ylmz.HandlerFunc {
	return JWTWithConfig(JWTConfig{
		Secret:       secret,
		TokenLookup:  "header:Authorization",
		AuthScheme:   "Bearer",
		SigningMethod: "HS256",
	})
}

// JWTWithConfig returns a JWT middleware with custom config.
func JWTWithConfig(cfg JWTConfig) ylmz.HandlerFunc {
	if cfg.TokenLookup == "" {
		cfg.TokenLookup = "header:Authorization"
	}
	if cfg.AuthScheme == "" {
		cfg.AuthScheme = "Bearer"
	}
	if cfg.SigningMethod == "" {
		cfg.SigningMethod = "HS256"
	}
	if cfg.KeyFunc == nil {
		cfg.KeyFunc = func() []byte { return cfg.Secret }
	}

	return func(c *ylmz.Context) {
		token, err := extractToken(c, cfg.TokenLookup, cfg.AuthScheme)
		if err != nil {
			c.AbortWithStatusJSON(http.StatusUnauthorized, ylmz.H{
				"error": "missing or malformed token",
			})
			return
		}

		claims, err := parseJWT(token, cfg.KeyFunc(), cfg.SigningMethod)
		if err != nil {
			c.AbortWithStatusJSON(http.StatusUnauthorized, ylmz.H{
				"error": "invalid or expired token",
			})
			return
		}

		// Store claims and token in context
		c.Set("jwt_claims", claims)
		c.Set("jwt_token", token)

		// Also extract standard claims for convenience
		if std, ok := claims.(*StandardClaims); ok {
			c.Set("jwt_sub", std.Subject)
			c.Set("jwt_iss", std.Issuer)
		}

		c.Next()
	}
}

func extractToken(c *ylmz.Context, lookup, scheme string) (string, error) {
	parts := strings.SplitN(lookup, ":", 2)
	if len(parts) != 2 {
		return "", ylmz.NewError("invalid token lookup format")
	}

	switch parts[0] {
	case "header":
		auth := c.GetHeader(parts[1])
		if auth == "" {
			return "", ylmz.NewError("missing authorization header")
		}
		if scheme != "" {
			if !strings.HasPrefix(strings.ToLower(auth), strings.ToLower(scheme)+" ") {
				return "", ylmz.NewError("invalid authorization scheme")
			}
			auth = auth[len(scheme)+1:]
		}
		return auth, nil
	case "query":
		return c.Query(parts[1]), nil
	case "cookie":
		val, err := c.Cookie(parts[1])
		if err != nil {
			return "", err
		}
		return val, nil
	default:
		return "", ylmz.NewError("unsupported token lookup source")
	}
}

// parseJWT parses and validates a JWT token (HS256).
func parseJWT(tokenString string, secret []byte, method string) (jwtClaims, error) {
	parts := strings.Split(tokenString, ".")
	if len(parts) != 3 {
		return nil, ylmz.NewError("invalid token format")
	}

	// Verify signature
	signingInput := parts[0] + "." + parts[1]
	mac := hmac.New(sha256.New, secret)
	mac.Write([]byte(signingInput))
	expectedSig := base64.RawURLEncoding.EncodeToString(mac.Sum(nil))

	if expectedSig != parts[2] {
		return nil, ylmz.NewError("invalid token signature")
	}

	// Decode payload
	payloadBytes, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return nil, ylmz.NewError("invalid token payload encoding")
	}

	var claims StandardClaims
	if err := json.Unmarshal(payloadBytes, &claims); err != nil {
		return nil, ylmz.NewError("invalid token payload")
	}

	// Check expiration
	if claims.ExpiresAt > 0 && time.Now().Unix() > claims.ExpiresAt {
		return nil, ylmz.NewError("token expired")
	}

	return &claims, nil
}

// NewError helps with creating framework errors.
var NewError = ylmz.NewError

// helper for generating JWT tokens (for testing / sign-in endpoints)
func GenerateJWT(secret []byte, claims map[string]any) (string, error) {
	header := map[string]string{"alg": "HS256", "typ": "JWT"}
	headerBytes, _ := json.Marshal(header)
	payloadBytes, _ := json.Marshal(claims)

	headerB64 := base64.RawURLEncoding.EncodeToString(headerBytes)
	payloadB64 := base64.RawURLEncoding.EncodeToString(payloadBytes)

	signingInput := headerB64 + "." + payloadB64
	mac := hmac.New(sha256.New, secret)
	mac.Write([]byte(signingInput))
	sig := base64.RawURLEncoding.EncodeToString(mac.Sum(nil))

	return signingInput + "." + sig, nil
}
