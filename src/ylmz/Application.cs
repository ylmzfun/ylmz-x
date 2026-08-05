using System.Net;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using ylmz.Container;
using ylmz.Controllers;
using ylmz.Http;
using ylmz.Middleware;
using ylmz.Routing;

namespace ylmz;

public class Application
{
    private readonly Router _router = new();
    private readonly MiddlewarePipeline _middleware = new();
    private readonly ServiceContainer _container = new();
    private string[]? _urls;
    private Action<IServiceCollection>? _configureServices;
    private string _environment = "production";

    public string Environment => _environment;

    // ── Fluent configuration ──

    public Application WithUrls(params string[] urls)
    {
        _urls = urls;
        return this;
    }

    public Application WithEnvironment(string env)
    {
        _environment = env;
        return this;
    }

    public Application ConfigureServices(Action<IServiceCollection> configure)
    {
        _configureServices = configure;
        return this;
    }

    public Application AddSingleton<TInterface, TImpl>() where TImpl : TInterface, new()
    {
        _container.Singleton<TInterface, TImpl>();
        return this;
    }

    public Application AddSingleton<TInterface>(TInterface instance)
    {
        _container.Singleton(instance);
        return this;
    }

    public Application AddTransient<TInterface, TImpl>() where TImpl : TInterface, new()
    {
        _container.Transient<TInterface, TImpl>();
        return this;
    }

    // ── Routing ──

    public Application Routes(Action<Router> configure)
    {
        configure(_router);
        return this;
    }

    public Application Get(string path, RouteHandler handler) { _router.Get(path, handler); return this; }
    public Application Post(string path, RouteHandler handler) { _router.Post(path, handler); return this; }
    public Application Put(string path, RouteHandler handler) { _router.Put(path, handler); return this; }
    public Application Patch(string path, RouteHandler handler) { _router.Patch(path, handler); return this; }
    public Application Delete(string path, RouteHandler handler) { _router.Delete(path, handler); return this; }
    public Application Any(string path, RouteHandler handler) { _router.Any(path, handler); return this; }

    public Application Group(string prefix, Action<RouteCollection> configure)
    {
        _router.Group(prefix, configure);
        return this;
    }

    // ── Middleware ──

    public Application AddMiddleware(MiddlewareDelegate middleware)
    {
        _middleware.Add(middleware);
        return this;
    }

    // ── Services ──

    public T? Resolve<T>() => _container.Resolve<T>();
    public object? Resolve(Type type) => _container.Resolve(type);

    // ── Controller resolution ──

    private object ResolveController(Type controllerType)
    {
        var instance = _container.Resolve(controllerType);
        if (instance != null) return instance;

        return Activator.CreateInstance(controllerType)!;
    }

    // ── Run ──

    public async Task RunAsync()
    {
        var builder = Host.CreateDefaultBuilder();

        builder.ConfigureWebHostDefaults(webBuilder =>
        {
            webBuilder.Configure(app =>
            {
                app.Run(HandleRequestAsync);
            });

            if (_urls != null && _urls.Length > 0)
                webBuilder.UseUrls(_urls);
        });

        builder.ConfigureServices(services =>
        {
            _configureServices?.Invoke(services);
        });

        builder.UseEnvironment(_environment);

        var host = builder.Build();
        await host.RunAsync();
    }

    // ── Core request handling ──

    private async Task HandleRequestAsync(HttpContext httpContext)
    {
        var request = new Request(httpContext);
        var response = new Response(httpContext);

        try
        {
            await _middleware.ExecuteAsync(request, response, async () =>
            {
                var match = _router.Match(httpContext.Request.Method, httpContext.Request.Path.Value ?? "/");

                if (match == null)
                {
                    await WriteNotFound(response, httpContext.Request.Path.Value ?? "/");
                    return;
                }

                request.RouteParams = match.Parameters;

                // Check if handler target is a controller method
                if (match.Route.Handler.Target != null)
                {
                    var targetType = match.Route.Handler.Target.GetType();

                    // If the handler is a closure that wraps a controller method, we need
                    // to resolve the controller and set its Request/Response
                    InjectControllerProperties(match.Route.Handler.Target);
                }

                await match.Route.Handler(request, response);
            });
        }
        catch (Exception ex)
        {
            await HandleException(response, ex);
        }
    }

    private static void InjectControllerProperties(object? target)
    {
        // Walk through the closure chain to find controller instances
        // When using lambda like: app.Get("/path", HomeController.Index)
        // The target contains the controller instance
        var visited = new HashSet<object>();
        var queue = new Queue<object?>();
        queue.Enqueue(target);

        while (queue.Count > 0)
        {
            var obj = queue.Dequeue();
            if (obj == null || !visited.Add(obj)) continue;

            if (obj is Controller controller)
            {
                // Properties are set by the route handler — we mark them for injection
                // but the actual Request/Response are set in the handler
            }

            // Inspect fields of the target for controller references
            foreach (var field in obj.GetType().GetFields(
                System.Reflection.BindingFlags.NonPublic |
                System.Reflection.BindingFlags.Instance |
                System.Reflection.BindingFlags.Public))
            {
                var val = field.GetValue(obj);
                if (val != null && !visited.Contains(val))
                    queue.Enqueue(val);
            }
        }
    }

    private static async Task WriteNotFound(Response response, string path)
    {
        response.StatusCode = (int)HttpStatusCode.NotFound;
        response.Raw.ContentType = "application/json; charset=utf-8";
        await response.Raw.WriteAsync(
            $"{{\"error\":\"Not Found\",\"path\":\"{System.Web.HttpUtility.JavaScriptStringEncode(path)}\"}}");
    }

    private static async Task HandleException(Response response, Exception ex)
    {
        response.StatusCode = (int)HttpStatusCode.InternalServerError;
        response.Raw.ContentType = "application/json; charset=utf-8";
        var msg = System.Web.HttpUtility.JavaScriptStringEncode(ex.Message);
        await response.Raw.WriteAsync($"{{\"error\":\"{msg}\"}}");
    }

    // ── Static helper for quick controller → RouteHandler conversion ──

    public static RouteHandler Controller<TC>(string method) where TC : Controller, new()
    {
        return async (req, res) =>
        {
            var controller = new TC { Request = req, Response = res };
            var methodInfo = typeof(TC).GetMethod(method,
                System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);

            if (methodInfo == null)
            {
                res.StatusCode = 500;
                await res.Text($"Method '{method}' not found on controller '{typeof(TC).Name}'");
                return;
            }

            var result = methodInfo.Invoke(controller, null);

            if (result is Task task)
            {
                await task;
            }
        };
    }

    public static RouteHandler Controller<TC>(string method, Func<TC> factory) where TC : Controller
    {
        return async (req, res) =>
        {
            var controller = factory();
            controller.Request = req;
            controller.Response = res;
            var methodInfo = typeof(TC).GetMethod(method,
                System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);

            if (methodInfo == null)
            {
                res.StatusCode = 500;
                await res.Text($"Method '{method}' not found on controller '{typeof(TC).Name}'");
                return;
            }

            var result = methodInfo.Invoke(controller, null);

            if (result is Task task)
            {
                await task;
            }
        };
    }
}
