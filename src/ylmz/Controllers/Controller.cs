using ylmz.Http;

namespace ylmz.Controllers;

public abstract class Controller
{
    public Request Request { get; internal set; } = null!;
    public Response Response { get; internal set; } = null!;

    protected async Task Json(object? data, int statusCode = 200)
    {
        await Response.Json(data, statusCode);
    }

    protected async Task Text(string text, int statusCode = 200)
    {
        await Response.Text(text, statusCode);
    }

    protected async Task Html(string html, int statusCode = 200)
    {
        await Response.Html(html, statusCode);
    }

    protected async Task NoContent()
    {
        await Response.NoContent();
    }

    protected string? RouteParam(string key) => Request.RouteParam(key);
    protected T? RouteParam<T>(string key) => Request.RouteParam<T>(key);
    protected string? QueryParam(string key) => Request.QueryParam(key);
    protected string? Header(string key) => Request.Header(key);
    protected async Task<string> BodyAsync() => await Request.BodyAsync();
    protected async Task<T?> BindAsync<T>() => await Request.BindAsync<T>();
}
