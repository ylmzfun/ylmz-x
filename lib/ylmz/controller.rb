# frozen_string_literal: true

module Ylmz
  class Controller
    attr_reader :request

    def request=(req)
      @request = req
    end

    # Return a JSON response.
    def json(data, status = 200)
      Response.json(data, status)
    end

    # Return a success response.
    def success(data = nil, message = 'OK')
      Response.success(data, message)
    end

    # Return an error response.
    def error(message, status = 400, errors = nil)
      Response.error(message, status, errors)
    end

    # Return a text response.
    def text(body, status = 200)
      Response.text(body, status)
    end

    # Return an HTML response.
    def html(body, status = 200)
      Response.html(body, status)
    end

    # Return a redirect response.
    def redirect(url, status = 302)
      Response.redirect(url, status)
    end

    # Get a request parameter.
    def params
      @request&.all || {}
    end

    # Get a single input value.
    def input(key, default = nil)
      @request&.input(key, default)
    end

    # Validate incoming data.
    def validate(data = nil, &block)
      source = data || @request&.all || {}
      validation = Validation.check(source, &block)
      validation.validate!
      validation.validated
    end
  end
end
