using System.Net;
using System.Text.Json;
using Microsoft.AspNetCore.Http;

namespace ylmz.Http;

public class Response
{
    private readonly HttpContext _context;

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase
    };

    public Response(HttpContext context)
    {
        _context = context;
    }

    public HttpContext HttpContext => _context;
    public HttpResponse Raw => _context.Response;

    public int StatusCode
    {
        get => _context.Response.StatusCode;
        set => _context.Response.StatusCode = value;
    }

    public Response Status(int code)
    {
        StatusCode = code;
        return this;
    }

    public Response Header(string key, string value)
    {
        _context.Response.Headers[key] = value;
        return this;
    }

    public async Task Json(object? data, int statusCode = 200)
    {
        StatusCode = statusCode;
        _context.Response.ContentType = "application/json; charset=utf-8";
        if (data != null)
        {
            var json = JsonSerializer.Serialize(data, JsonOptions);
            await _context.Response.WriteAsync(json);
        }
    }

    public async Task Text(string text, int statusCode = 200, string contentType = "text/plain; charset=utf-8")
    {
        StatusCode = statusCode;
        _context.Response.ContentType = contentType;
        await _context.Response.WriteAsync(text);
    }

    public async Task Html(string html, int statusCode = 200)
    {
        await Text(html, statusCode, "text/html; charset=utf-8");
    }

    public async Task NoContent()
    {
        StatusCode = (int)HttpStatusCode.NoContent;
        await Task.CompletedTask;
    }

    public async Task Send(object? data = null, int statusCode = 200)
    {
        if (data is string s)
        {
            await Text(s, statusCode);
        }
        else
        {
            await Json(data, statusCode);
        }
    }
}
