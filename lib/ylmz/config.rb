# frozen_string_literal: true

module Ylmz
  class Config
    def initialize
      @store = {}
    end

    def load!(dir)
      Dotenv.load(File.join(dir, '.env')) if File.exist?(File.join(dir, '.env'))

      config_dir = File.join(dir, 'config')
      return unless Dir.exist?(config_dir)

      Dir[File.join(config_dir, '*.rb')].sort.each do |file|
        instance_eval(File.read(file), file)
      end
    end

    def set(key, value)
      @store[key.to_sym] = value
    end

    def get(key, default = nil)
      k = key.to_sym
      return @store[k] if @store.key?(k)

      env_val = ENV[key.to_s] || ENV[key.to_s.upcase]
      return env_val unless env_val.nil?

      default
    end

    alias [] get

    def []=(key, value)
      set(key, value)
    end

    def to_h
      @store.dup
    end

    def merge!(hash)
      hash.each { |k, v| @store[k.to_sym] = v }
      self
    end

    def method_missing(name, *args, &_block)
      key = name.to_s
      if key.end_with?('=')
        set(key[0..-2], args.first)
      else
        get(key, *args)
      end
    end

    def respond_to_missing?(_name, _include_private = false)
      true
    end
  end
end
