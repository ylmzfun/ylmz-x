using ylmz.Http;

namespace ylmz.Middleware;

public delegate Task MiddlewareDelegate(Request request, Response response, Func<Task> next);

public class MiddlewarePipeline
{
    private readonly List<MiddlewareDelegate> _middlewares = new();

    public MiddlewarePipeline Add(MiddlewareDelegate middleware)
    {
        _middlewares.Add(middleware);
        return this;
    }

    public async Task ExecuteAsync(Request request, Response response, Func<Task> finalHandler)
    {
        if (_middlewares.Count == 0)
        {
            await finalHandler();
            return;
        }

        int index = 0;

        async Task Next()
        {
            if (index < _middlewares.Count)
            {
                var middleware = _middlewares[index++];
                await middleware(request, response, Next);
            }
            else
            {
                await finalHandler();
            }
        }

        await Next();
    }
}
