using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Primitives;

namespace ylmz.Http;

public class Request
{
    private readonly HttpContext _context;
    private Dictionary<string, object?>? _routeParams;
    private JsonElement? _jsonBody;

    public Request(HttpContext context)
    {
        _context = context;
    }

    public HttpContext HttpContext => _context;

    public string Method => _context.Request.Method;
    public string Path => _context.Request.Path.Value ?? "/";
    public string ContentType => _context.Request.ContentType ?? string.Empty;
    public IQueryCollection Query => _context.Request.Query;
    public IHeaderDictionary Headers => _context.Request.Headers;
    public Stream Body => _context.Request.Body;

    internal Dictionary<string, object?> RouteParams
    {
        get => _routeParams ??= new Dictionary<string, object?>();
        set => _routeParams = value;
    }

    public string? RouteParam(string key)
    {
        if (_routeParams != null && _routeParams.TryGetValue(key, out var val))
            return val?.ToString();
        return null;
    }

    public T? RouteParam<T>(string key)
    {
        var val = RouteParam(key);
        if (val == null) return default;
        return (T)Convert.ChangeType(val, typeof(T));
    }

    public string? QueryParam(string key) => _context.Request.Query[key].FirstOrDefault();

    public string? Header(string key) => _context.Request.Headers[key].FirstOrDefault();

    public async Task<string> BodyAsync()
    {
        using var reader = new StreamReader(_context.Request.Body);
        var body = await reader.ReadToEndAsync();
        _context.Request.Body = new MemoryStream(System.Text.Encoding.UTF8.GetBytes(body));
        return body;
    }

    public async Task<JsonElement?> JsonBodyAsync()
    {
        if (_jsonBody != null) return _jsonBody;
        var body = await BodyAsync();
        if (string.IsNullOrWhiteSpace(body)) return null;
        _jsonBody = JsonSerializer.Deserialize<JsonElement>(body);
        return _jsonBody;
    }

    public async Task<T?> BindAsync<T>()
    {
        var body = await BodyAsync();
        if (string.IsNullOrWhiteSpace(body)) return default;
        return JsonSerializer.Deserialize<T>(body, new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true
        });
    }
}
