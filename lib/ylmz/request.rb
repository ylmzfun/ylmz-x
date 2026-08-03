# frozen_string_literal: true

require 'json'
require 'rack'

module Ylmz
  class Request
    attr_reader :env, :params, :route_params

    def initialize(env)
      @env = env
      @rack_request = Rack::Request.new(env)
      @params = {}
      @route_params = {}
      parse_params!
    end

    # HTTP method (GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD).
    def method
      @rack_request.request_method
    end

    # Request path without query string.
    def path
      @rack_request.path
    end

    # Full URL.
    def url
      @rack_request.url
    end

    # Base URL (scheme + host + port).
    def base_url
      @rack_request.base_url
    end

    # Request scheme (http/https).
    def scheme
      @rack_request.scheme
    end

    # Host name.
    def host
      @rack_request.host
    end

    # Port number.
    def port
      @rack_request.port
    end

    # Query string parameters.
    def query
      indifferent_hash(@rack_request.GET)
    end

    # Get a header value.
    def header(key)
      env_key = "HTTP_#{key.to_s.upcase.tr('-', '_')}"
      @env[env_key] || @env[key.to_s.upcase.tr('-', '_')]
    end

    alias headers header

    # Content type of the request.
    def content_type
      @rack_request.content_type
    end

    # Request body (raw).
    def body
      @rack_request.body.rewind
      raw = @rack_request.body.read
      @rack_request.body.rewind
      raw
    end

    # Parsed JSON body.
    def json
      @json ||= JSON.parse(body)
    rescue JSON::ParserError
      {}
    end

    # Check if the request is JSON.
    def json?
      content_type&.include?('application/json')
    end

    # Check if the request is XMLHttpRequest (AJAX).
    def xhr?
      @env['HTTP_X_REQUESTED_WITH']&.downcase == 'xmlhttprequest'
    end

    # Client IP address.
    def ip
      @rack_request.ip
    end

    # User agent string.
    def user_agent
      @rack_request.user_agent
    end

    # Get a parameter (checks route params first, then body, then query).
    def input(key, default = nil)
      key_s = key.to_s
      return @route_params[key_s] if @route_params.key?(key_s)

      @params.key?(key_s) ? @params[key_s] : query[key_s] || default
    end

    alias param input

    # Get all input merged (query + body + route params).
    def all
      query.merge(@params).merge(@route_params)
    end

    # Get only the specified keys from input.
    def only(*keys)
      all.select { |k, _| keys.map(&:to_s).include?(k) }
    end

    # Get all input except specified keys.
    def except(*keys)
      all.reject { |k, _| keys.map(&:to_s).include?(k) }
    end

    # Check if a key exists in input.
    def has?(key)
      all.key?(key.to_s)
    end

    # Uploaded files.
    def files
      @rack_request.params.select { |_, v| v.is_a?(Hash) && v.key?(:tempfile) }
    end

    # Merge route parameters into the request.
    def merge_route_params!(params)
      @route_params.merge!(params.transform_keys(&:to_s))
    end

    private

    def parse_params!
      if json?
        @params = indifferent_hash(json)
      else
        @params = indifferent_hash(@rack_request.POST)
      end
    end

    def indifferent_hash(hash)
      hash.each_with_object({}) { |(k, v), h| h[k.to_s] = v }
    end
  end
end
