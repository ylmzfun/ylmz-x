# frozen_string_literal: true

require 'rack'
require 'json'
require 'dotenv'

require_relative 'ylmz/version'
require_relative 'ylmz/config'
require_relative 'ylmz/container'
require_relative 'ylmz/request'
require_relative 'ylmz/response'
require_relative 'ylmz/middleware'
require_relative 'ylmz/router'
require_relative 'ylmz/controller'
require_relative 'ylmz/validation'
require_relative 'ylmz/application'
require_relative 'ylmz/cli'

module Ylmz
  class Error < StandardError; end
  class RouteNotFoundError < Error; end
  class ValidationError < Error; end
end
