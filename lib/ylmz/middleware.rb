# frozen_string_literal: true

module Ylmz
  class Middleware
    attr_reader :stack

    def initialize
      @stack = []
      @named = {}
    end

    # Add a middleware to the global stack.
    #   middleware.use(Rack::Runtime)
    #   middleware.use(AuthMiddleware, only: ['/admin'])
    def use(klass, *args, &block)
      entry = { klass: klass, args: args, block: block }
      @stack << entry
      @named[klass.name] = entry
      self
    end

    # Insert a middleware before another in the stack.
    def insert_before(before_klass, klass, *args, &block)
      idx = @stack.index { |e| e[:klass] == before_klass }
      raise ArgumentError, "Middleware #{before_klass} not found in stack" unless idx

      entry = { klass: klass, args: args, block: block }
      @stack.insert(idx, entry)
      @named[klass.name] = entry
      self
    end

    # Insert a middleware after another in the stack.
    def insert_after(after_klass, klass, *args, &block)
      idx = @stack.index { |e| e[:klass] == after_klass }
      raise ArgumentError, "Middleware #{after_klass} not found in stack" unless idx

      entry = { klass: klass, args: args, block: block }
      @stack.insert(idx + 1, entry)
      @named[klass.name] = entry
      self
    end

    # Remove a middleware from the stack.
    def remove(klass)
      @stack.reject! { |e| e[:klass] == klass }
      @named.delete(klass.name)
      self
    end

    # Build the Rack middleware stack.
    def build(app)
      @stack.reverse_each do |entry|
        app = build_middleware(entry[:klass], app, *entry[:args], &entry[:block])
      end
      app
    end

    private

    def build_middleware(klass, app, *args, &block)
      if block
        klass.new(app, *args, &block)
      else
        klass.new(app, *args)
      end
    end
  end
end
