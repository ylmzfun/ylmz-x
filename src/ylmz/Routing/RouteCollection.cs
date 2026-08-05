using ylmz.Http;

namespace ylmz.Routing;

public class RouteCollection
{
    private readonly List<Route> _routes = new();
    private readonly string _prefix;

    public RouteCollection(string prefix = "")
    {
        _prefix = prefix;
    }

    public IReadOnlyList<Route> Routes => _routes;

    private string BuildPath(string path)
    {
        if (string.IsNullOrEmpty(_prefix))
            return path;

        var combined = _prefix.TrimEnd('/') + "/" + path.TrimStart('/');
        return combined.TrimEnd('/') == "" ? "/" : combined;
    }

    public RouteCollection Get(string path, RouteHandler handler)
    {
        _routes.Add(new Route("GET", BuildPath(path), handler));
        return this;
    }

    public RouteCollection Post(string path, RouteHandler handler)
    {
        _routes.Add(new Route("POST", BuildPath(path), handler));
        return this;
    }

    public RouteCollection Put(string path, RouteHandler handler)
    {
        _routes.Add(new Route("PUT", BuildPath(path), handler));
        return this;
    }

    public RouteCollection Patch(string path, RouteHandler handler)
    {
        _routes.Add(new Route("PATCH", BuildPath(path), handler));
        return this;
    }

    public RouteCollection Delete(string path, RouteHandler handler)
    {
        _routes.Add(new Route("DELETE", BuildPath(path), handler));
        return this;
    }

    public RouteCollection Any(string path, RouteHandler handler)
    {
        _routes.Add(new Route("ANY", BuildPath(path), handler));
        return this;
    }

    public RouteCollection Group(string prefix, Action<RouteCollection> configure)
    {
        var group = new RouteCollection(BuildPath(prefix));
        configure(group);
        _routes.AddRange(group.Routes);
        return this;
    }
}
