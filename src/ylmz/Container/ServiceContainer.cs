namespace ylmz.Container;

public class ServiceContainer
{
    private readonly Dictionary<Type, Func<object?>> _factories = new();
    private readonly Dictionary<Type, object?> _singletons = new();

    public ServiceContainer Singleton<TInterface, TImpl>() where TImpl : TInterface, new()
    {
        _factories[typeof(TInterface)] = () =>
        {
            if (!_singletons.ContainsKey(typeof(TInterface)))
                _singletons[typeof(TInterface)] = new TImpl();
            return _singletons[typeof(TInterface)];
        };
        return this;
    }

    public ServiceContainer Singleton<TInterface>(Func<object?> factory)
    {
        _factories[typeof(TInterface)] = () =>
        {
            if (!_singletons.ContainsKey(typeof(TInterface)))
                _singletons[typeof(TInterface)] = factory();
            return _singletons[typeof(TInterface)];
        };
        return this;
    }

    public ServiceContainer Singleton<TInterface>(TInterface instance)
    {
        _singletons[typeof(TInterface)] = instance;
        _factories[typeof(TInterface)] = () => instance;
        return this;
    }

    public ServiceContainer Transient<TInterface, TImpl>() where TImpl : TInterface, new()
    {
        _factories[typeof(TInterface)] = () => new TImpl();
        return this;
    }

    public ServiceContainer Transient<TInterface>(Func<object?> factory)
    {
        _factories[typeof(TInterface)] = factory;
        return this;
    }

    public T? Resolve<T>()
    {
        return (T?)Resolve(typeof(T));
    }

    public object? Resolve(Type type)
    {
        if (_factories.TryGetValue(type, out var factory))
            return factory();
        return null;
    }

    public bool Has<T>() => _factories.ContainsKey(typeof(T));
}
