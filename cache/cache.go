// Package cache provides an in-memory cache with TTL support and
// a simple interface for pluggable backends.
package cache

import (
	"sync"
	"time"
)

// Cache is the core cache interface.
type Cache interface {
	Get(key string) (any, bool)
	Set(key string, value any, ttl time.Duration)
	Del(key string)
	Has(key string) bool
	Clear()
	Len() int
	Keys() []string
}

// item represents a cached item.
type item struct {
	value    any
	expireAt time.Time
}

// MemoryCache is an in-memory implementation of Cache.
type MemoryCache struct {
	mu       sync.RWMutex
	items    map[string]*item
	stopCh   chan struct{}
	interval time.Duration
}

// NewMemory creates a new MemoryCache.
func NewMemory(cleanupInterval time.Duration) *MemoryCache {
	c := &MemoryCache{
		items:    make(map[string]*item),
		stopCh:   make(chan struct{}),
		interval: cleanupInterval,
	}
	if cleanupInterval > 0 {
		go c.cleanupLoop()
	}
	return c
}

// Get retrieves a value from cache.
func (c *MemoryCache) Get(key string) (any, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	it, ok := c.items[key]
	if !ok {
		return nil, false
	}
	if !it.expireAt.IsZero() && time.Now().After(it.expireAt) {
		return nil, false
	}
	return it.value, true
}

// Set stores a value in cache with TTL.
func (c *MemoryCache) Set(key string, value any, ttl time.Duration) {
	c.mu.Lock()
	defer c.mu.Unlock()

	it := &item{value: value}
	if ttl > 0 {
		it.expireAt = time.Now().Add(ttl)
	}
	c.items[key] = it
}

// Del removes a key from cache.
func (c *MemoryCache) Del(key string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	delete(c.items, key)
}

// Has reports whether a key exists and is not expired.
func (c *MemoryCache) Has(key string) bool {
	_, ok := c.Get(key)
	return ok
}

// Clear removes all items.
func (c *MemoryCache) Clear() {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.items = make(map[string]*item)
}

// Len returns the number of items.
func (c *MemoryCache) Len() int {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return len(c.items)
}

// Keys returns all non-expired keys.
func (c *MemoryCache) Keys() []string {
	c.mu.RLock()
	defer c.mu.RUnlock()

	keys := make([]string, 0, len(c.items))
	now := time.Now()
	for k, it := range c.items {
		if it.expireAt.IsZero() || now.Before(it.expireAt) {
			keys = append(keys, k)
		}
	}
	return keys
}

// GetString returns a cached string value.
func GetString(c Cache, key string) (string, bool) {
	v, ok := c.Get(key)
	if !ok {
		return "", false
	}
	s, ok := v.(string)
	return s, ok
}

// GetInt returns a cached int value.
func GetInt(c Cache, key string) (int, bool) {
	v, ok := c.Get(key)
	if !ok {
		return 0, false
	}
	i, ok := v.(int)
	return i, ok
}

// GetDuration returns a cached duration value.
func GetDuration(c Cache, key string) (time.Duration, bool) {
	v, ok := c.Get(key)
	if !ok {
		return 0, false
	}
	d, ok := v.(time.Duration)
	return d, ok
}

// Remember gets or sets a cache value.
func Remember(c Cache, key string, ttl time.Duration, fn func() (any, error)) (any, error) {
	if val, ok := c.Get(key); ok {
		return val, nil
	}
	val, err := fn()
	if err != nil {
		return nil, err
	}
	c.Set(key, val, ttl)
	return val, nil
}

func (c *MemoryCache) cleanupLoop() {
	ticker := time.NewTicker(c.interval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			c.cleanup()
		case <-c.stopCh:
			return
		}
	}
}

func (c *MemoryCache) cleanup() {
	c.mu.Lock()
	defer c.mu.Unlock()

	now := time.Now()
	for k, it := range c.items {
		if !it.expireAt.IsZero() && now.After(it.expireAt) {
			delete(c.items, k)
		}
	}
}

// Stop stops the cleanup goroutine.
func (c *MemoryCache) Stop() {
	close(c.stopCh)
}
