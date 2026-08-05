using ylmz;
using ylmz.Http;
using BasicApp.Controllers;

var app = new Application();

// ── Global middleware ──

// Logging middleware
app.AddMiddleware(async (req, res, next) =>
{
    Console.WriteLine($"[{DateTime.UtcNow:HH:mm:ss}] {req.Method} {req.Path}");
    var sw = System.Diagnostics.Stopwatch.StartNew();
    await next();
    sw.Stop();
    Console.WriteLine($"[{DateTime.UtcNow:HH:mm:ss}] {req.Method} {req.Path} → {res.StatusCode} ({sw.ElapsedMilliseconds}ms)");
});

// CORS middleware
app.AddMiddleware(async (req, res, next) =>
{
    res.Header("Access-Control-Allow-Origin", "*");
    res.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, PATCH, OPTIONS");
    res.Header("Access-Control-Allow-Headers", "Content-Type, Authorization");

    if (req.Method == "OPTIONS")
    {
        res.StatusCode = 204;
        return;
    }

    await next();
});

// ── Routes ──

// Basic GET
app.Get("/", async (req, res) =>
{
    await res.Json(new
    {
        framework = "ylmz",
        message = "A Lumen-like web framework for C#",
        endpoints = new[]
        {
            "GET  /",
            "GET  /hello",
            "GET  /hello/{name}",
            "GET  /info",
            "POST /users",
            "GET  /api/v1/items",
            "GET  /api/v1/items/{id}",
            "POST /api/v1/items"
        }
    });
});

// Route with optional parameter
app.Get("/hello", async (req, res) =>
{
    await res.Json(new { greeting = "Hello, World!" });
});

app.Get("/hello/{name}", async (req, res) =>
{
    var name = req.RouteParam("name");
    await res.Json(new { greeting = $"Hello, {name}!" });
});

// Request inspection endpoint
app.Get("/info", async (req, res) =>
{
    await res.Json(new
    {
        method = req.Method,
        path = req.Path,
        queryParams = req.Query.ToDictionary(q => q.Key, q => q.Value.ToString()),
        headers = req.Headers
            .Where(h => !h.Key.StartsWith(":"))
            .ToDictionary(h => h.Key, h => h.Value.ToString())
    });
});

// POST with body binding
app.Post("/users", async (req, res) =>
{
    var body = await req.BindAsync<Dictionary<string, object?>>();
    await res.Json(new
    {
        created = true,
        user = body,
        id = Guid.NewGuid().ToString()
    }, 201);
});

// ── Route groups (like Lumen's $router->group) ──

app.Group("/api/v1", group =>
{
    group.Get("/items", Application.Controller<ApiController>(nameof(ApiController.List)));
    group.Get("/items/{id:int}", Application.Controller<ApiController>(nameof(ApiController.Show)));
    group.Post("/items", Application.Controller<ApiController>(nameof(ApiController.Store)));
});

// ── Controller-based routing (alternative pattern) ──

// Using the built-in controller helper
app.Get("/home", Application.Controller<HomeController>(nameof(HomeController.Index)));

// ── Start the server ──

app.WithUrls("http://localhost:5000")
   .WithEnvironment("development");

Console.WriteLine("╔══════════════════════════════════════════╗");
Console.WriteLine("║   ylmz Framework - C# Micro-Framework   ║");
Console.WriteLine("║   Listening on http://localhost:5000     ║");
Console.WriteLine("╚══════════════════════════════════════════╝");

await app.RunAsync();
