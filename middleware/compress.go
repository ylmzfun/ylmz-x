package middleware

import (
	"bufio"
	"compress/gzip"
	"io"
	"net"
	"net/http"
	"strings"
	"sync"

	"github.com/ylmzfun/ylmz-go/ylmz"
)

type gzipResponseWriter struct {
	io.Writer
	http.ResponseWriter
}

func (w *gzipResponseWriter) Write(b []byte) (int, error) {
	return w.Writer.Write(b)
}

func (w *gzipResponseWriter) Flush() {
	if f, ok := w.ResponseWriter.(http.Flusher); ok {
		f.Flush()
	}
}

func (w *gzipResponseWriter) Hijack() (net.Conn, *bufio.ReadWriter, error) {
	if hj, ok := w.ResponseWriter.(http.Hijacker); ok {
		return hj.Hijack()
	}
	return nil, nil, nil
}

func (w *gzipResponseWriter) Status() int {
	if rw, ok := w.ResponseWriter.(ylmz.ResponseWriter); ok {
		return rw.Status()
	}
	return 200
}

func (w *gzipResponseWriter) Size() int {
	if rw, ok := w.ResponseWriter.(ylmz.ResponseWriter); ok {
		return rw.Size()
	}
	return 0
}

func (w *gzipResponseWriter) Written() bool {
	if rw, ok := w.ResponseWriter.(ylmz.ResponseWriter); ok {
		return rw.Written()
	}
	return false
}

func (w *gzipResponseWriter) WriteHeaderNow() {
	if rw, ok := w.ResponseWriter.(ylmz.ResponseWriter); ok {
		rw.WriteHeaderNow()
	}
}

// Gzip returns a middleware that compresses responses with gzip.
func Gzip(level int) ylmz.HandlerFunc {
	if level < 1 || level > 9 {
		level = gzip.DefaultCompression
	}
	pool := &sync.Pool{
		New: func() any {
			w, _ := gzip.NewWriterLevel(io.Discard, level)
			return w
		},
	}

	return func(c *ylmz.Context) {
		if !strings.Contains(c.GetHeader("Accept-Encoding"), "gzip") {
			c.Next()
			return
		}

		c.Header("Content-Encoding", "gzip")
		c.Header("Vary", "Accept-Encoding")

		gw := pool.Get().(*gzip.Writer)
		gw.Reset(c.Writer)
		defer func() {
			gw.Close()
			pool.Put(gw)
		}()

		c.Writer = &gzipResponseWriter{
			Writer:         gw,
			ResponseWriter: c.Writer,
		}

		c.Next()
	}
}
