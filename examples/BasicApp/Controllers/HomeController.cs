using ylmz.Controllers;
using ylmz.Http;

namespace BasicApp.Controllers;

public class HomeController : Controller
{
    public async Task Index()
    {
        await Json(new
        {
            message = "Welcome to ylmz framework!",
            version = "1.0.0",
            time = DateTime.UtcNow
        });
    }

    public async Task Hello()
    {
        var name = RouteParam("name") ?? "World";
        await Json(new { greeting = $"Hello, {name}!" });
    }

    public async Task Info()
    {
        await Json(new
        {
            method = Request.Method,
            path = Request.Path,
            headers = Request.Headers
                .ToDictionary(h => h.Key, h => h.Value.ToString()),
            queryParams = Request.Query
                .ToDictionary(q => q.Key, q => q.Value.ToString())
        });
    }

    public async Task CreateUser()
    {
        var body = await BindAsync<Dictionary<string, object?>>();
        await Json(new
        {
            created = true,
            user = body,
            id = Guid.NewGuid().ToString()
        }, 201);
    }
}

public class ApiController : Controller
{
    private static readonly List<object> _items = new()
    {
        new { id = 1, name = "Item One" },
        new { id = 2, name = "Item Two" }
    };

    public async Task List()
    {
        await Json(new { data = _items });
    }

    public async Task Show()
    {
        var id = RouteParam<int>("id");
        var item = _items.FirstOrDefault(i =>
            ((dynamic)i).id == id);

        if (item == null)
        {
            await Json(new { error = "Not Found" }, 404);
            return;
        }

        await Json(item);
    }

    public async Task Store()
    {
        var body = await BindAsync<Dictionary<string, object?>>();
        var newItem = new { id = _items.Count + 1, name = body?["name"] ?? "unnamed" };
        _items.Add(newItem);
        await Json(newItem, 201);
    }
}
