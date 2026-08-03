# frozen_string_literal: true

module Ylmz
  class Router
    Route = Struct.new(:method, :pattern, :handler, :options, keyword_init: true)

    def initialize
      @routes = []
      @named_routes = {}
      @group_stack = []
    end

    # Define routes via DSL block.
    def self.define(&block)
      router = new
      router.instance_eval(&block)
      router
    end

    # HTTP verb methods.
    %i[get post put patch delete options head].each do |verb|
      define_method(verb) do |path, to: nil, as: nil, &handler|
        add_route(verb.to_s.upcase, path, to: to, as: as, handler: handler)
      end
    end

    # Match any HTTP method.
    def any(path, to: nil, as: nil, &handler)
      add_route('ANY', path, to: to, as: as, handler: handler)
    end

    # Match multiple HTTP methods.
    def match(methods, path, to: nil, as: nil, &handler)
      [*methods].each do |method|
        add_route(method.to_s.upcase, path, to: to, as: as, handler: handler)
      end
    end

    # Create a route group with shared attributes.
    def group(prefix: '', as: nil, middleware: nil, &block)
      @group_stack.push({ prefix: prefix, as: as, middleware: [*middleware].compact })
      instance_eval(&block)
      @group_stack.pop
    end

    # Register a named route.
    def name(name, path)
      @named_routes[name.to_sym] = path
    end

    # Generate URL from a named route.
    def url_for(name, params = {})
      path = @named_routes[name.to_sym]
      raise ArgumentError, "Named route '#{name}' not found" unless path

      result = path.gsub(/:(\w+)/) { |_| params[$1.to_sym] || params[$1] || ":#{$1}" }
      result.start_with?('/') ? result : "/#{result}"
    end

    # Dispatch a request to the matching route handler.
    def dispatch(request)
      route, route_params = match_route(request)

      unless route
        return Response.error("Route not found: #{request.method} #{request.path}", 404)
      end

      request.merge_route_params!(route_params || {})

      handler = route[:handler]
      options = route[:options] || {}

      # Run route-specific middleware first.
      if options[:middleware] && !options[:middleware].empty?
        result = run_middleware_stack(options[:middleware], request) do
          execute_handler(handler, request)
        end
        result.is_a?(Response) ? result : Response.json(result)
      else
        result = execute_handler(handler, request)
        result.is_a?(Response) ? result : Response.json(result)
      end
    rescue ValidationError => e
      Response.error('Validation failed', 422, JSON.parse(e.message))
    rescue StandardError => e
      Response.error(e.message, 500)
    end

    # Get all registered routes (for debugging).
    def routes
      @routes.map do |r|
        {
          method: r[:method],
          path: resolve_pattern_string(r[:pattern]),
          handler: r[:handler].inspect
        }
      end
    end

    private

    def add_route(method, path, to: nil, as: nil, handler: nil)
      full_path = build_full_path(path)
      middleware = collect_group_middleware

      h = if to
            to.is_a?(String) ? resolve_controller_action(to) : to
          elsif handler
            handler
          else
            raise ArgumentError, 'Route must have either :to or a block'
          end

      @routes << {
        method: method,
        pattern: compile_pattern(full_path),
        path: full_path,
        handler: h,
        options: { middleware: middleware, as: as }
      }

      @named_routes[as.to_sym] = full_path if as
    end

    def build_full_path(path)
      prefix = @group_stack.map { |g| g[:prefix] }.join
      result = "#{prefix}#{path}"
      result.start_with?('/') ? result : "/#{result}"
    end

    def collect_group_middleware
      @group_stack.flat_map { |g| g[:middleware] }.compact.uniq
    end

    def compile_pattern(path)
      regex_str = path.gsub(/:(\w+)/) { |_| "(?<#{$1}>[^/]+)" }
      Regexp.new("\\A#{regex_str}\\z")
    end

    def resolve_pattern_string(pattern)
      pattern.source.gsub('\A', '').gsub('\z', '').gsub('\/', '/')
    end

    def resolve_controller_action(to)
      controller_name, action = to.split('@')
      proc do |request|
        controller_class = resolve_controller_class(controller_name)
        controller = controller_class.new
        controller.send(:request=, request)
        controller.send(action.to_sym)
      end
    end

    def resolve_controller_class(name)
      return Object.const_get(name) if name.include?('::')

      # Try common naming conventions.
      candidates = [
        "#{classify(name)}Controller",
        name
      ]

      candidates.each do |candidate|
        klass = Object.const_get(candidate) rescue nil
        return klass if klass
      end

      raise NameError, "Controller not found: #{name}"
    end

    def classify(str)
      str.to_s.split(/[_\/-]/).map(&:capitalize).join
    end

    def match_route(request)
      @routes.each do |route|
        next unless route[:method] == 'ANY' || route[:method] == request.method

        match = route[:pattern].match(request.path)
        next unless match

        params = match.named_captures || {}
        return [route, params]
      end
      nil
    end

    def execute_handler(handler, request)
      case handler
      when Proc
        if handler.arity == 1
          handler.call(request)
        elsif handler.arity.zero?
          handler.call
        else
          handler.call(request, Response.new)
        end
      else
        handler.to_s
      end
    end

    def run_middleware_stack(middlewares, request, &core)
      stack = middlewares.reverse.reduce(core) do |app, middleware_klass|
        mw = middleware_klass.new
        proc { mw.call(request, &app) }
      end
      stack.call
    end
  end
end
