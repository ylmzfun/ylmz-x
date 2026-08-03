// Package log provides a structured, leveled logging library.
package log

import (
	"fmt"
	"io"
	"os"
	"runtime"
	"strings"
	"sync"
	"time"
)

// Level defines log severity levels.
type Level uint32

const (
	// DebugLevel logs detailed debug information.
	DebugLevel Level = iota
	// InfoLevel logs general operational information.
	InfoLevel
	// WarnLevel logs warning events.
	WarnLevel
	// ErrorLevel logs error events.
	ErrorLevel
	// FatalLevel logs fatal events and exits.
	FatalLevel
)

func (l Level) String() string {
	switch l {
	case DebugLevel:
		return "DEBUG"
	case InfoLevel:
		return "INFO"
	case WarnLevel:
		return "WARN"
	case ErrorLevel:
		return "ERROR"
	case FatalLevel:
		return "FATAL"
	default:
		return "UNKNOWN"
	}
}

func (l Level) Color() string {
	switch l {
	case DebugLevel:
		return "\033[36m" // cyan
	case InfoLevel:
		return "\033[32m" // green
	case WarnLevel:
		return "\033[33m" // yellow
	case ErrorLevel:
		return "\033[31m" // red
	case FatalLevel:
		return "\033[35m" // magenta
	default:
		return "\033[0m"
	}
}

// Field is a key-value pair for structured logging.
type Field struct {
	Key   string
	Value any
}

// Logger is the core logger instance.
type Logger struct {
	mu     sync.Mutex
	out    io.Writer
	level  Level
	fields []Field

	// EnableColor enables ANSI color output.
	EnableColor bool

	// EnableCaller adds caller info (file:line).
	EnableCaller bool

	// CallerSkip adjusts the caller skip count.
	CallerSkip int
}

// Config holds logger configuration.
type Config struct {
	Out          io.Writer
	Level        Level
	EnableColor  bool
	EnableCaller bool
}

// DefaultConfig returns a sensible default config.
func DefaultConfig() Config {
	return Config{
		Out:          os.Stdout,
		Level:        DebugLevel,
		EnableColor:  true,
		EnableCaller: true,
	}
}

// New creates a new Logger.
func New(cfg Config) *Logger {
	if cfg.Out == nil {
		cfg.Out = os.Stdout
	}
	return &Logger{
		out:          cfg.Out,
		level:        cfg.Level,
		EnableColor:  cfg.EnableColor,
		EnableCaller: cfg.EnableCaller,
		CallerSkip:   2,
	}
}

// WithFields returns a logger with additional fields.
func (l *Logger) WithFields(fields ...Field) *Logger {
	newLogger := &Logger{
		out:          l.out,
		level:        l.level,
		fields:       make([]Field, len(l.fields)+len(fields)),
		EnableColor:  l.EnableColor,
		EnableCaller: l.EnableCaller,
		CallerSkip:   l.CallerSkip,
	}
	copy(newLogger.fields, l.fields)
	copy(newLogger.fields[len(l.fields):], fields)
	return newLogger
}

// With returns a logger with a single field.
func (l *Logger) With(key string, value any) *Logger {
	return l.WithFields(Field{Key: key, Value: value})
}

// SetLevel sets the minimum log level.
func (l *Logger) SetLevel(level Level) {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.level = level
}

// ==================== Log Methods ====================

// Debug logs at DebugLevel.
func (l *Logger) Debug(msg string, fields ...Field) {
	l.log(DebugLevel, msg, fields...)
}

// Info logs at InfoLevel.
func (l *Logger) Info(msg string, fields ...Field) {
	l.log(InfoLevel, msg, fields...)
}

// Warn logs at WarnLevel.
func (l *Logger) Warn(msg string, fields ...Field) {
	l.log(WarnLevel, msg, fields...)
}

// Error logs at ErrorLevel.
func (l *Logger) Error(msg string, fields ...Field) {
	l.log(ErrorLevel, msg, fields...)
}

// Fatal logs at FatalLevel and calls os.Exit(1).
func (l *Logger) Fatal(msg string, fields ...Field) {
	l.log(FatalLevel, msg, fields...)
	os.Exit(1)
}

// Debugf logs a formatted debug message.
func (l *Logger) Debugf(format string, args ...any) {
	l.log(DebugLevel, fmt.Sprintf(format, args...))
}

// Infof logs a formatted info message.
func (l *Logger) Infof(format string, args ...any) {
	l.log(InfoLevel, fmt.Sprintf(format, args...))
}

// Warnf logs a formatted warn message.
func (l *Logger) Warnf(format string, args ...any) {
	l.log(WarnLevel, fmt.Sprintf(format, args...))
}

// Errorf logs a formatted error message.
func (l *Logger) Errorf(format string, args ...any) {
	l.log(ErrorLevel, fmt.Sprintf(format, args...))
}

// Fatalf logs a formatted fatal message and exits.
func (l *Logger) Fatalf(format string, args ...any) {
	l.log(FatalLevel, fmt.Sprintf(format, args...))
	os.Exit(1)
}

// ==================== Internal ====================

func (l *Logger) log(level Level, msg string, fields ...Field) {
	if level < l.level {
		return
	}

	l.mu.Lock()
	defer l.mu.Unlock()

	now := time.Now()
	var b strings.Builder

	if l.EnableColor {
		b.WriteString(level.Color())
	}

	b.WriteString(fmt.Sprintf("%-5s", level.String()))

	if l.EnableColor {
		b.WriteString("\033[0m")
	}

	b.WriteString(fmt.Sprintf(" [%s]", now.Format("2006-01-02 15:04:05.000")))

	if l.EnableCaller {
		_, file, line, ok := runtime.Caller(l.CallerSkip)
		if ok {
			idx := strings.LastIndexByte(file, '/')
			if idx >= 0 {
				file = file[idx+1:]
			}
			b.WriteString(fmt.Sprintf(" [%s:%d]", file, line))
		}
	}

	b.WriteString(" " + msg)

	// Base fields
	for _, f := range l.fields {
		b.WriteString(fmt.Sprintf(" %s=%v", f.Key, f.Value))
	}
	// Message fields
	for _, f := range fields {
		b.WriteString(fmt.Sprintf(" %s=%v", f.Key, f.Value))
	}

	b.WriteString("\n")

	io.WriteString(l.out, b.String())
}

// ==================== Default Logger ====================

var defaultLogger = New(DefaultConfig())

// Default returns the default logger.
func Default() *Logger {
	return defaultLogger
}

// SetDefaultLevel sets the level for the default logger.
func SetDefaultLevel(level Level) {
	defaultLogger.SetLevel(level)
}

// Debug logs at DebugLevel using the default logger.
func Debug(msg string, fields ...Field) {
	defaultLogger.Debug(msg, fields...)
}

// Info logs at InfoLevel using the default logger.
func Info(msg string, fields ...Field) {
	defaultLogger.Info(msg, fields...)
}

// Warn logs at WarnLevel using the default logger.
func Warn(msg string, fields ...Field) {
	defaultLogger.Warn(msg, fields...)
}

// Error logs at ErrorLevel using the default logger.
func Error(msg string, fields ...Field) {
	defaultLogger.Error(msg, fields...)
}

// Fatal logs at FatalLevel using the default logger.
func Fatal(msg string, fields ...Field) {
	defaultLogger.Fatal(msg, fields...)
}

// Debugf logs a formatted debug message using default logger.
func Debugf(format string, args ...any) {
	defaultLogger.Debugf(format, args...)
}

// Infof logs a formatted info message using default logger.
func Infof(format string, args ...any) {
	defaultLogger.Infof(format, args...)
}

// Warnf logs a formatted warn message using default logger.
func Warnf(format string, args ...any) {
	defaultLogger.Warnf(format, args...)
}

// Errorf logs a formatted error message using default logger.
func Errorf(format string, args ...any) {
	defaultLogger.Errorf(format, args...)
}

// Fatalf logs a formatted fatal message using default logger.
func Fatalf(format string, args ...any) {
	defaultLogger.Fatalf(format, args...)
}
