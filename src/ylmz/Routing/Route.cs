using System.Text.RegularExpressions;
using ylmz.Http;

namespace ylmz.Routing;

public delegate Task RouteHandler(Request request, Response response);

public class Route
{
    public string HttpMethod { get; }
    public string Pattern { get; }
    public Regex Regex { get; }
    public List<string> ParamNames { get; }
    public RouteHandler Handler { get; }

    public Route(string httpMethod, string pattern, RouteHandler handler)
    {
        HttpMethod = httpMethod.ToUpperInvariant();
        Pattern = pattern;
        Handler = handler;
        ParamNames = new List<string>();
        Regex = BuildRegex(pattern);
    }

    private Regex BuildRegex(string pattern)
    {
        // Guard against null input
        if (string.IsNullOrWhiteSpace(pattern))
            pattern = "/";

        // Remove trailing slash for consistency (but keep root)
        if (pattern.Length > 1 && pattern.EndsWith('/'))
            pattern = pattern.TrimEnd('/');

        var regexPattern = "^";
        var segments = pattern.Split('/');

        for (int i = 0; i < segments.Length; i++)
        {
            var segment = segments[i];
            if (i > 0) regexPattern += "/";

            if (segment.StartsWith("{") && segment.EndsWith("}"))
            {
                var inner = segment[1..^1]; // Remove { and }
                string paramName;
                string constraint = "[^/]+";

                // Check for constraint: {name:int} or {name:alpha}
                var colonIdx = inner.IndexOf(':');
                if (colonIdx > 0)
                {
                    paramName = inner[..colonIdx];
                    var constraintType = inner[(colonIdx + 1)..];
                    constraint = constraintType switch
                    {
                        "int" => "\\d+",
                        "alpha" => "[a-zA-Z]+",
                        "guid" => "[0-9a-fA-F\\-]+",
                        _ => "[^/]+"
                    };
                }
                else
                {
                    paramName = inner;

                    // Check for optional: {name?}
                    if (paramName.EndsWith("?"))
                    {
                        paramName = paramName.TrimEnd('?');
                        // Make this segment optional
                        regexPattern = regexPattern[..^1]; // Remove the trailing /
                        regexPattern += "(?:/(?<" + paramName + ">" + constraint + "))?";
                        ParamNames.Add(paramName);
                        continue;
                    }
                }

                regexPattern += "(?<" + paramName + ">" + constraint + ")";
                ParamNames.Add(paramName);
            }
            else if (segment == "{*path}")
            {
                regexPattern += "(?<path>.*)";
                ParamNames.Add("path");
            }
            else
            {
                regexPattern += Regex.Escape(segment);
            }
        }

        regexPattern += "$";
        return new Regex(regexPattern, RegexOptions.IgnoreCase | RegexOptions.Compiled);
    }

    public RouteMatch? Match(string httpMethod, string path)
    {
        if (HttpMethod != "ANY" && !string.Equals(HttpMethod, httpMethod, StringComparison.OrdinalIgnoreCase))
            return null;

        // Normalize path
        if (path.Length > 1 && path.EndsWith('/'))
            path = path.TrimEnd('/');

        var match = Regex.Match(path);
        if (!match.Success) return null;

        var parameters = new Dictionary<string, object?>();
        foreach (var name in ParamNames)
        {
            var group = match.Groups[name];
            parameters[name] = group.Success ? group.Value : null;
        }

        return new RouteMatch(this, parameters);
    }
}

public class RouteMatch
{
    public Route Route { get; }
    public Dictionary<string, object?> Parameters { get; }

    public RouteMatch(Route route, Dictionary<string, object?> parameters)
    {
        Route = route;
        Parameters = parameters;
    }
}
