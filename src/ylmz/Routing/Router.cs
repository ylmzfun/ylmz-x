using ylmz.Http;

namespace ylmz.Routing;

public class Router
{
    private readonly List<Route> _routes = new();

    public IReadOnlyList<Route> Routes => _routes;

    public RouteCollection Map() => new();

    public Router AddRoutes(RouteCollection collection)
    {
        _routes.AddRange(collection.Routes);
        return this;
    }

    public Router Get(string path, RouteHandler handler)
    {
        _routes.Add(new Route("GET", path, handler));
        return this;
    }

    public Router Post(string path, RouteHandler handler)
    {
        _routes.Add(new Route("POST", path, handler));
        return this;
    }

    public Router Put(string path, RouteHandler handler)
    {
        _routes.Add(new Route("PUT", path, handler));
        return this;
    }

    public Router Patch(string path, RouteHandler handler)
    {
        _routes.Add(new Route("PATCH", path, handler));
        return this;
    }

    public Router Delete(string path, RouteHandler handler)
    {
        _routes.Add(new Route("DELETE", path, handler));
        return this;
    }

    public Router Any(string path, RouteHandler handler)
    {
        _routes.Add(new Route("ANY", path, handler));
        return this;
    }

    public Router Group(string prefix, Action<RouteCollection> configure)
    {
        var group = new RouteCollection(prefix);
        configure(group);
        _routes.AddRange(group.Routes);
        return this;
    }

    public RouteMatch? Match(string httpMethod, string path)
    {
        foreach (var route in _routes)
        {
            var match = route.Match(httpMethod, path);
            if (match != null) return match;
        }
        return null;
    }
}
