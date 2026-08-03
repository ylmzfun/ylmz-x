// Package config provides configuration management with support for
// JSON, environment variables, and defaults.
package config

import (
	"encoding/json"
	"fmt"
	"os"
	"reflect"
	"strconv"
	"strings"
)

// Loader defines the interface for loading configuration.
type Loader interface {
	Load(cfg any) error
}

// JSONLoader loads configuration from a JSON file.
type JSONLoader struct {
	Path string
}

// Load implements Loader.
func (l *JSONLoader) Load(cfg any) error {
	data, err := os.ReadFile(l.Path)
	if err != nil {
		return fmt.Errorf("config: failed to read file %s: %w", l.Path, err)
	}
	if err := json.Unmarshal(data, cfg); err != nil {
		return fmt.Errorf("config: failed to parse JSON: %w", err)
	}
	return nil
}

// EnvLoader loads configuration from environment variables.
type EnvLoader struct {
	Prefix string
}

// Load implements Loader.
func (l *EnvLoader) Load(cfg any) error {
	return loadFromEnv(cfg, l.Prefix)
}

// Load loads configuration from multiple loaders, merging in order.
func Load(cfg any, loaders ...Loader) error {
	for _, loader := range loaders {
		if err := loader.Load(cfg); err != nil {
			return err
		}
	}
	return nil
}

// MustLoad is like Load but panics on error.
func MustLoad(cfg any, loaders ...Loader) {
	if err := Load(cfg, loaders...); err != nil {
		panic(err)
	}
}

// LoadFile loads configuration from a JSON file.
func LoadFile(path string, cfg any) error {
	return Load(cfg, &JSONLoader{Path: path})
}

// LoadEnv loads configuration from environment variables.
func LoadEnv(prefix string, cfg any) error {
	return Load(cfg, &EnvLoader{Prefix: prefix})
}

// Getenv returns the environment variable value or the default.
func Getenv(key, defaultVal string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return defaultVal
}

// GetenvInt returns the environment variable as int or the default.
func GetenvInt(key string, defaultVal int) int {
	val := os.Getenv(key)
	if val == "" {
		return defaultVal
	}
	i, err := strconv.Atoi(val)
	if err != nil {
		return defaultVal
	}
	return i
}

// GetenvBool returns the environment variable as bool or the default.
func GetenvBool(key string, defaultVal bool) bool {
	val := os.Getenv(key)
	if val == "" {
		return defaultVal
	}
	b, err := strconv.ParseBool(val)
	if err != nil {
		return defaultVal
	}
	return b
}

// ==================== Internal ====================

func loadFromEnv(cfg any, prefix string) error {
	v := reflect.ValueOf(cfg)
	if v.Kind() != reflect.Ptr || v.Elem().Kind() != reflect.Struct {
		return fmt.Errorf("config: cfg must be a pointer to struct")
	}
	return populateFromEnv(v.Elem(), prefix)
}

func populateFromEnv(v reflect.Value, prefix string) error {
	t := v.Type()
	for i := 0; i < t.NumField(); i++ {
		field := t.Field(i)
		fieldVal := v.Field(i)

		if !fieldVal.CanSet() {
			continue
		}

		envTag := field.Tag.Get("env")
		if envTag == "" {
			envTag = field.Tag.Get("json")
		}
		if envTag == "" || envTag == "-" {
			continue
		}

		envName := strings.ToUpper(strings.ReplaceAll(envTag, "-", "_"))
		if prefix != "" {
			envName = strings.ToUpper(prefix) + "_" + envName
		}

		envVal := os.Getenv(envName)
		if envVal == "" {
			continue
		}

		switch fieldVal.Kind() {
		case reflect.String:
			fieldVal.SetString(envVal)
		case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
			if i64, err := strconv.ParseInt(envVal, 10, 64); err == nil {
				fieldVal.SetInt(i64)
			}
		case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
			if u64, err := strconv.ParseUint(envVal, 10, 64); err == nil {
				fieldVal.SetUint(u64)
			}
		case reflect.Float32, reflect.Float64:
			if f64, err := strconv.ParseFloat(envVal, 64); err == nil {
				fieldVal.SetFloat(f64)
			}
		case reflect.Bool:
			if b, err := strconv.ParseBool(envVal); err == nil {
				fieldVal.SetBool(b)
			}
		case reflect.Slice:
			if fieldVal.Type().Elem().Kind() == reflect.String {
				parts := strings.Split(envVal, ",")
				slice := reflect.MakeSlice(fieldVal.Type(), len(parts), len(parts))
				for j, part := range parts {
					slice.Index(j).SetString(strings.TrimSpace(part))
				}
				fieldVal.Set(slice)
			}
		}
	}
	return nil
}
