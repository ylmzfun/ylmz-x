// Package session provides HTTP session management with support for
// cookie-based and header-based sessions.
package session

import (
	"crypto/rand"
	"encoding/base64"
	"fmt"
	"sync"
	"time"

	"github.com/ylmzfun/ylmz-go/cache"
	"github.com/ylmzfun/ylmz-go/ylmz"
)

// Store defines the session storage interface.
type Store interface {
	Get(id string) (*Session, error)
	Save(s *Session) error
	Delete(id string) error
}

// Session holds session data.
type Session struct {
	ID        string
	Values    map[string]any
	CreatedAt time.Time
	UpdatedAt time.Time
	mu        sync.RWMutex
}

// Get retrieves a value.
func (s *Session) Get(key string) (any, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	v, ok := s.Values[key]
	return v, ok
}

// Set stores a value.
func (s *Session) Set(key string, value any) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.Values[key] = value
	s.UpdatedAt = time.Now()
}

// Delete removes a value.
func (s *Session) Delete(key string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.Values, key)
	s.UpdatedAt = time.Now()
}

// GetString returns a string value.
func (s *Session) GetString(key string) string {
	v, ok := s.Get(key)
	if !ok {
		return ""
	}
	val, _ := v.(string)
	return val
}

// GetInt returns an int value.
func (s *Session) GetInt(key string) int {
	v, ok := s.Get(key)
	if !ok {
		return 0
	}
	val, _ := v.(int)
	return val
}

// GetBool returns a bool value.
func (s *Session) GetBool(key string) bool {
	v, ok := s.Get(key)
	if !ok {
		return false
	}
	val, _ := v.(bool)
	return val
}

// MemoryStore is an in-memory session store.
type MemoryStore struct {
	cache cache.Cache
}

// NewMemoryStore creates a new in-memory session store.
func NewMemoryStore(cleanupInterval time.Duration) *MemoryStore {
	return &MemoryStore{
		cache: cache.NewMemory(cleanupInterval),
	}
}

// Get retrieves a session by ID.
func (s *MemoryStore) Get(id string) (*Session, error) {
	v, ok := s.cache.Get(id)
	if !ok {
		return nil, fmt.Errorf("session not found: %s", id)
	}
	sess, ok := v.(*Session)
	if !ok {
		return nil, fmt.Errorf("invalid session data")
	}
	return sess, nil
}

// Save stores a session.
func (s *MemoryStore) Save(sess *Session) error {
	s.cache.Set(sess.ID, sess, 24*time.Hour)
	return nil
}

// Delete removes a session.
func (s *MemoryStore) Delete(id string) error {
	s.cache.Del(id)
	return nil
}

// Config holds session middleware configuration.
type Config struct {
	// Store is the session storage backend.
	Store Store

	// CookieName is the session cookie name (default: "session_id").
	CookieName string

	// Expire is the session expiration time.
	Expire time.Duration

	// Secure sets the Secure flag on cookies.
	Secure bool

	// HTTPOnly sets the HttpOnly flag on cookies.
	HTTPOnly bool
}

// DefaultConfig returns a sensible default config.
func DefaultConfig() Config {
	return Config{
		CookieName: "session_id",
		Expire:     24 * time.Hour,
		HTTPOnly:   true,
	}
}

// Middleware returns a session management middleware.
func Middleware(cfg Config) ylmz.HandlerFunc {
	if cfg.Store == nil {
		cfg.Store = NewMemoryStore(5 * time.Minute)
	}
	if cfg.CookieName == "" {
		cfg.CookieName = "session_id"
	}
	if cfg.Expire == 0 {
		cfg.Expire = 24 * time.Hour
	}

	return func(c *ylmz.Context) {
		sessID, err := c.Cookie(cfg.CookieName)
		var sess *Session

		if err != nil || sessID == "" {
			// Create new session
			sess = &Session{
				ID:        generateSessionID(),
				Values:    make(map[string]any),
				CreatedAt: time.Now(),
				UpdatedAt: time.Now(),
			}
			if err := cfg.Store.Save(sess); err != nil {
				c.Next()
				return
			}
			c.SetSameSite(cfg.CookieName, sess.ID, int(cfg.Expire.Seconds()), "/", "", cfg.Secure, cfg.HTTPOnly, 3) // SameSiteLax
		} else {
			sess, err = cfg.Store.Get(sessID)
			if err != nil || sess == nil {
				sess = &Session{
					ID:        generateSessionID(),
					Values:    make(map[string]any),
					CreatedAt: time.Now(),
					UpdatedAt: time.Now(),
				}
				cfg.Store.Save(sess)
				c.SetSameSite(cfg.CookieName, sess.ID, int(cfg.Expire.Seconds()), "/", "", cfg.Secure, cfg.HTTPOnly, 3)
			}
		}

		c.Set("session", sess)
		c.Next()

		// Save session after request
		if s, ok := c.Get("session"); ok {
			if sess, ok := s.(*Session); ok {
				cfg.Store.Save(sess)
			}
		}
	}
}

func generateSessionID() string {
	b := make([]byte, 32)
	rand.Read(b)
	return base64.RawURLEncoding.EncodeToString(b)
}
