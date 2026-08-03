# frozen_string_literal: true

require 'json'

module Ylmz
  class Response
    attr_reader :body, :headers

    def initialize(body = '', status = 200, headers = {})
      @body = body
      @status = status
      @headers = { 'Content-Type' => 'text/html; charset=utf-8' }.merge(headers)
    end

    # Get or set the HTTP status code.
    def status(code = nil)
      return @status if code.nil?

      @status = code
      self
    end

    # Set a response header.
    def header(key, value)
      @headers[key] = value
      self
    end

    # Set the Content-Type header.
    def content_type(type)
      header('Content-Type', "#{type}; charset=utf-8")
      self
    end

    # Set the response body.
    def write(data)
      @body = data
      self
    end

    # Convert to a Rack-compatible response array.
    def finish
      body_data = @body.is_a?(String) ? [@body] : @body
      [@status, @headers, body_data]
    end

    # --- Convenience factories ---

    # Create a JSON response.
    def self.json(data, status = 200, headers = {})
      body = data.is_a?(String) ? data : JSON.generate(data)
      new(body, status, { 'Content-Type' => 'application/json; charset=utf-8' }.merge(headers))
    end

    # Create a plain text response.
    def self.text(body, status = 200, headers = {})
      new(body, status, { 'Content-Type' => 'text/plain; charset=utf-8' }.merge(headers))
    end

    # Create an HTML response.
    def self.html(body, status = 200, headers = {})
      new(body, status, { 'Content-Type' => 'text/html; charset=utf-8' }.merge(headers))
    end

    # Create a redirect response.
    def self.redirect(url, status = 302)
      new('', status, 'Location' => url)
    end

    # Create a no-content response.
    def self.no_content
      new('', 204)
    end

    # Create an error response (JSON).
    def self.error(message, status = 500, errors = nil)
      payload = { error: message }
      payload[:errors] = errors if errors
      json(payload, status)
    end

    # Create a success response (JSON).
    def self.success(data = nil, message = 'OK', status = 200)
      payload = { message: message }
      payload[:data] = data unless data.nil?
      json(payload, status)
    end
  end
end
