# frozen_string_literal: true

module Ylmz
  class Container
    def initialize
      @bindings = {}
      @instances = {}
      @aliases = {}
    end

    # Bind an abstract type to a concrete resolver.
    #   container.bind(:logger, Logger, Logger::WARN)
    #   container.bind(:logger, -> { Logger.new(STDOUT) })
    def bind(abstract, *args, shared: false, &block)
      resolver = block || (args.shift unless args.first.nil?)

      raise ArgumentError, 'Must provide a concrete class or a block' unless resolver

      @bindings[abstract.to_sym] = {
        resolver: resolver,
        args: args,
        shared: shared
      }
    end

    # Bind a shared (singleton) service.
    def singleton(abstract, *args, &block)
      bind(abstract, *args, shared: true, &block)
    end

    # Register an alias for an existing binding.
    def alias(abstract, target)
      @aliases[abstract.to_sym] = target.to_sym
    end

    # Resolve a binding, instantiating it if needed.
    def make(abstract)
      key = resolve_alias(abstract.to_sym)

      binding = @bindings[key]

      return @instances[key] if binding && binding[:shared] && @instances.key?(key)

      instance = if binding
                   resolve_binding(binding)
                 elsif key.to_s.end_with?('_path')
                   resolve_path_method(key)
                 else
                   attempt_class_resolution(key)
                 end

      @instances[key] = instance if binding && binding[:shared]
      instance
    end

    alias get make
    alias [] make

    # Resolve and invoke a callable.
    def call(abstract, method, *args)
      obj = make(abstract)
      obj.public_send(method, *args)
    end

    # Check if a binding exists.
    def bound?(abstract)
      @bindings.key?(resolve_alias(abstract.to_sym))
    end

    # Remove a binding.
    def forget(abstract)
      key = abstract.to_sym
      @bindings.delete(key)
      @instances.delete(key)
      @aliases.delete(key)
    end

    # Clear all bindings and instances.
    def flush!
      @bindings.clear
      @instances.clear
      @aliases.clear
    end

    private

    def resolve_alias(key)
      chain = [key]
      current = @aliases[key]
      while current
        raise "Circular alias detected: #{chain.join(' -> ')} -> #{current}" if chain.include?(current)

        chain << current
        current = @aliases[current]
      end
      chain.last
    end

    def resolve_binding(binding)
      resolver = binding[:resolver]
      if resolver.respond_to?(:call)
        if resolver.is_a?(Proc) || resolver.is_a?(Method)
          arity = resolver.arity
          arity.zero? || arity == -1 ? resolver.call : resolver.call(self)
        else
          resolver.call
        end
      elsif resolver.is_a?(Class) || resolver.is_a?(Module)
        args = binding[:args] || []
        resolver.new(*args)
      else
        resolver
      end
    end

    def resolve_path_method(key)
      base = key.to_s.sub(/_path$/, '')
      config = make(:config) if bound?(:config)
      config ? config.get("#{base}_path".to_sym) : nil
    end

    def attempt_class_resolution(key)
      class_name = key.to_s.split('_').map(&:capitalize).join
      klass = Object.const_get(class_name) rescue nil
      klass&.new
    end
  end
end
