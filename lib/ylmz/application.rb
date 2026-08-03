# frozen_string_literal: true

module Ylmz
  class Application
    attr_reader :config, :container, :router, :middleware

    def initialize(base_path = Dir.pwd)
      @base_path = base_path
      @config = Config.new
      @container = Container.new
      @middleware = Middleware.new
      @router = nil
      @booted = false

      register_base_services
    end

    # Boot the application: load config, register providers, load routes.
    def boot!
      return self if @booted

      @config.load!(@base_path) if Dir.exist?(File.join(@base_path, 'config'))

      load_routes!
      @booted = true
      self
    end

    # Rack entry point — returns a Rack-compatible app.
    def call(env)
      boot! unless @booted

      request = Request.new(env)

      # Build middleware stack once.
      @rack_app ||= @middleware.build(method(:dispatch))

      @rack_app.call(env)
    end

    # Rack `to_app` interface (used by `rackup`).
    def to_app
      self
    end

    # Dispatch the request through the router.
    def dispatch(env)
      request = env.is_a?(Request) ? env : Request.new(env)
      response = @router.dispatch(request)
      response.finish
    end

    # Define routes.
    def routes(&block)
      @router = Router.define(&block)
      self
    end

    # Register a service provider (a module with a `register(app)` method).
    def register(provider)
      provider.register(self) if provider.respond_to?(:register)
      self
    end

    # Get base path.
    def base_path
      @base_path
    end

    # Get the environment (development, production, test).
    def env
      @config.get(:app_env) || ENV.fetch('APP_ENV', 'development')
    end

    # Check if in production.
    def production?
      env == 'production'
    end

    # Check if in development.
    def development?
      env == 'development'
    end

    # Check if in test.
    def test?
      env == 'test'
    end

    private

    def register_base_services
      @container.singleton(:config) { @config }
      @container.singleton(:app) { self }
    end

    def load_routes!
      routes_file = File.join(@base_path, 'config', 'routes.rb')
      return unless File.exist?(routes_file) && @router.nil?

      content = File.read(routes_file)
      @router = Router.define { instance_eval(content) }
    end
  end
end
