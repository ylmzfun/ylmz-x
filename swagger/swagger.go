// Package swagger provides OpenAPI / Swagger documentation generation.
package swagger

import (
	"encoding/json"
	"fmt"
	"reflect"
	"strings"
	"sync"

	"github.com/ylmzfun/ylmz-go/ylmz"
)

// Spec represents an OpenAPI 3.0 specification.
type Spec struct {
	OpenAPI string      `json:"openapi"`
	Info    Info        `json:"info"`
	Servers []Server    `json:"servers,omitempty"`
	Paths   Paths       `json:"paths"`
	mu      sync.Mutex
}

// Info holds API metadata.
type Info struct {
	Title       string `json:"title"`
	Description string `json:"description,omitempty"`
	Version     string `json:"version"`
}

// Server represents a server URL.
type Server struct {
	URL         string `json:"url"`
	Description string `json:"description,omitempty"`
}

// Paths holds all API paths.
type Paths map[string]PathItem

// PathItem describes operations on a single path.
type PathItem map[string]Operation

// Operation describes an API operation.
type Operation struct {
	Summary     string              `json:"summary,omitempty"`
	Description string              `json:"description,omitempty"`
	Tags        []string            `json:"tags,omitempty"`
	Parameters  []Parameter         `json:"parameters,omitempty"`
	RequestBody *RequestBody        `json:"requestBody,omitempty"`
	Responses   map[string]Response `json:"responses"`
}

// Parameter describes an operation parameter.
type Parameter struct {
	Name        string `json:"name"`
	In          string `json:"in"` // path, query, header, cookie
	Required    bool   `json:"required,omitempty"`
	Description string `json:"description,omitempty"`
	Schema      Schema `json:"schema"`
}

// RequestBody describes a request body.
type RequestBody struct {
	Required bool              `json:"required,omitempty"`
	Content  map[string]Schema `json:"content"`
}

// Response describes an API response.
type Response struct {
	Description string              `json:"description"`
	Content     map[string]Schema   `json:"content,omitempty"`
}

// Schema describes a JSON schema.
type Schema struct {
	Type       string            `json:"type,omitempty"`
	Properties map[string]Schema `json:"properties,omitempty"`
	Items      *Schema           `json:"items,omitempty"`
	Required   []string          `json:"required,omitempty"`
	Example    any               `json:"example,omitempty"`
	Ref        string            `json:"$ref,omitempty"`
}

// Generator generates OpenAPI specs from route definitions.
type Generator struct {
	spec  *Spec
	routes []RouteDef
}

// RouteDef describes a route for documentation.
type RouteDef struct {
	Method      string
	Path        string
	Summary     string
	Description string
	Tags        []string
	Request     any // example request struct
	Response    any // example response struct
}

// New creates a new Generator.
func New(info Info) *Generator {
	return &Generator{
		spec: &Spec{
			OpenAPI: "3.0.3",
			Info:    info,
			Paths:   make(Paths),
		},
	}
}

// AddServer adds a server URL.
func (g *Generator) AddServer(url, description string) {
	g.spec.Servers = append(g.spec.Servers, Server{URL: url, Description: description})
}

// AddRoute adds a route definition.
func (g *Generator) AddRoute(r RouteDef) {
	g.spec.mu.Lock()
	defer g.spec.mu.Unlock()
	g.routes = append(g.routes, r)
}

// Build generates the final spec.
func (g *Generator) Build() {
	g.spec.mu.Lock()
	defer g.spec.mu.Unlock()

	for _, r := range g.routes {
		pathItem := g.spec.Paths[r.Path]
		if pathItem == nil {
			pathItem = make(PathItem)
		}

		op := Operation{
			Summary:     r.Summary,
			Description: r.Description,
			Tags:        r.Tags,
			Responses:   make(map[string]Response),
		}

		// Parameters from path
		params := extractPathParams(r.Path)
		for _, p := range params {
			op.Parameters = append(op.Parameters, Parameter{
				Name:     p,
				In:       "path",
				Required: true,
				Schema:   Schema{Type: "string"},
			})
		}

		// Request body
		if r.Request != nil && (r.Method == "POST" || r.Method == "PUT" || r.Method == "PATCH") {
			op.RequestBody = &RequestBody{
				Required: true,
				Content: map[string]Schema{
					"application/json": structToSchema(r.Request),
				},
			}
		}

		// Response
		desc := "Successful response"
		content := make(map[string]Schema)
		if r.Response != nil {
			content["application/json"] = structToSchema(r.Response)
		}
		op.Responses["200"] = Response{
			Description: desc,
			Content:     content,
		}

		op.Responses["400"] = Response{Description: "Bad request"}
		op.Responses["500"] = Response{Description: "Internal server error"}

		pathItem[strings.ToLower(r.Method)] = op
		g.spec.Paths[r.Path] = pathItem
	}
}

// JSON returns the spec as JSON.
func (g *Generator) JSON() ([]byte, error) {
	g.Build()
	return json.MarshalIndent(g.spec, "", "  ")
}

// Handler returns an HTTP handler that serves the Swagger spec.
func (g *Generator) Handler() ylmz.HandlerFunc {
	g.Build()
	return func(c *ylmz.Context) {
		c.JSON(200, g.spec)
	}
}

// SwaggerUI serves a simple Swagger UI page.
func SwaggerUI(specURL string) ylmz.HandlerFunc {
	html := fmt.Sprintf(`<!DOCTYPE html>
<html>
<head>
    <title>API Documentation</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        SwaggerUIBundle({
            url: "%s",
            dom_id: '#swagger-ui',
            presets: [SwaggerUIBundle.presets.apis],
            layout: "BaseLayout"
        });
    </script>
</body>
</html>`, specURL)

	return func(c *ylmz.Context) {
		c.Data(200, "text/html; charset=utf-8", []byte(html))
	}
}

// ==================== Helpers ====================

func extractPathParams(path string) []string {
	var params []string
	parts := strings.Split(path, "/")
	for _, part := range parts {
		if strings.HasPrefix(part, ":") {
			params = append(params, part[1:])
		}
	}
	return params
}

func structToSchema(v any) Schema {
	typ := reflect.TypeOf(v)
	if typ.Kind() == reflect.Ptr {
		typ = typ.Elem()
	}
	if typ.Kind() != reflect.Struct {
		// Return basic type
		return basicTypeSchema(typ.Kind())
	}

	schema := Schema{
		Type:       "object",
		Properties: make(map[string]Schema),
	}

	for i := 0; i < typ.NumField(); i++ {
		field := typ.Field(i)
		jsonTag := field.Tag.Get("json")
		name := field.Name
		if jsonTag != "" && jsonTag != "-" {
			name = strings.SplitN(jsonTag, ",", 2)[0]
		}

		fieldSchema := goTypeToSchema(field.Type)
		schema.Properties[name] = fieldSchema
	}

	return schema
}

func goTypeToSchema(t reflect.Type) Schema {
	if t.Kind() == reflect.Ptr {
		t = t.Elem()
	}

	switch t.Kind() {
	case reflect.String:
		return Schema{Type: "string"}
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64,
		reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
		return Schema{Type: "integer"}
	case reflect.Float32, reflect.Float64:
		return Schema{Type: "number"}
	case reflect.Bool:
		return Schema{Type: "boolean"}
	case reflect.Slice:
		itemSchema := goTypeToSchema(t.Elem())
		return Schema{Type: "array", Items: &itemSchema}
	case reflect.Struct:
		if t == reflect.TypeOf((*any)(nil)).Elem() {
			return Schema{Type: "object"}
		}
		return structToSchema(reflect.New(t).Interface())
	case reflect.Map:
		return Schema{Type: "object"}
	default:
		return Schema{Type: "string"}
	}
}

func basicTypeSchema(k reflect.Kind) Schema {
	switch k {
	case reflect.String:
		return Schema{Type: "string"}
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		return Schema{Type: "integer"}
	case reflect.Float32, reflect.Float64:
		return Schema{Type: "number"}
	case reflect.Bool:
		return Schema{Type: "boolean"}
	default:
		return Schema{Type: "string"}
	}
}
