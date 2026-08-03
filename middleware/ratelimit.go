package middleware

import (
	"net/http"
	"sync"
	"time"

	"github.com/ylmzfun/ylmz-go/ylmz"
)

// RateLimitConfig holds rate limiting configuration.
type RateLimitConfig struct {
	// Rate is the number of requests allowed per period.
	Rate int

	// Period is the time window for rate limiting.
	Period time.Duration

	// Burst allows temporary bursting above the rate.
	Burst int

	// KeyFunc extracts the rate limit key from the request (default: ClientIP).
	KeyFunc func(c *ylmz.Context) string
}

// RateLimit returns a token-bucket based rate limiter.
func RateLimit(rate int, period time.Duration) ylmz.HandlerFunc {
	return RateLimitWithConfig(RateLimitConfig{
		Rate:   rate,
		Period: period,
	})
}

// RateLimitWithConfig returns a rate limiter with full configuration.
func RateLimitWithConfig(cfg RateLimitConfig) ylmz.HandlerFunc {
	if cfg.KeyFunc == nil {
		cfg.KeyFunc = func(c *ylmz.Context) string {
			return c.ClientIP()
		}
	}
	if cfg.Burst == 0 {
		cfg.Burst = cfg.Rate
	}

	limiter := &tokenBucketLimiter{
		buckets: make(map[string]*tokenBucket),
		rate:    cfg.Rate,
		period:  cfg.Period,
		burst:   cfg.Burst,
	}

	// Cleanup goroutine
	go func() {
		ticker := time.NewTicker(cfg.Period * 2)
		defer ticker.Stop()
		for range ticker.C {
			limiter.cleanup()
		}
	}()

	return func(c *ylmz.Context) {
		key := cfg.KeyFunc(c)
		if !limiter.allow(key) {
			c.AbortWithStatusJSON(http.StatusTooManyRequests, ylmz.H{
				"error": "rate limit exceeded",
			})
			return
		}
		c.Next()
	}
}

type tokenBucket struct {
	tokens    float64
	lastCheck time.Time
}

type tokenBucketLimiter struct {
	mu      sync.Mutex
	buckets map[string]*tokenBucket
	rate    int
	period  time.Duration
	burst   int
}

func (l *tokenBucketLimiter) allow(key string) bool {
	l.mu.Lock()
	defer l.mu.Unlock()

	bucket, exists := l.buckets[key]
	now := time.Now()

	if !exists {
		bucket = &tokenBucket{
			tokens:    float64(l.burst),
			lastCheck: now,
		}
		l.buckets[key] = bucket
	} else {
		elapsed := now.Sub(bucket.lastCheck).Seconds()
		bucket.tokens += elapsed * (float64(l.rate) / l.period.Seconds())
		if bucket.tokens > float64(l.burst) {
			bucket.tokens = float64(l.burst)
		}
		bucket.lastCheck = now
	}

	if bucket.tokens >= 1.0 {
		bucket.tokens--
		return true
	}

	return false
}

func (l *tokenBucketLimiter) cleanup() {
	l.mu.Lock()
	defer l.mu.Unlock()

	now := time.Now()
	for key, bucket := range l.buckets {
		if now.Sub(bucket.lastCheck) > l.period*2 {
			delete(l.buckets, key)
		}
	}
}
