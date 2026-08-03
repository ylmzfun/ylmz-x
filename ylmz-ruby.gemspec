# frozen_string_literal: true

require_relative 'lib/ylmz/version'

Gem::Specification.new do |spec|
  spec.name          = 'ylmz-ruby'
  spec.version       = Ylmz::VERSION
  spec.authors       = ['ylmz']
  spec.email         = ['ylmz@example.com']
  spec.summary       = 'A lightweight yet comprehensive Ruby web micro-framework inspired by Lumen.'
  spec.description   = <<~DESC
    Ylmz is a Rack-based Ruby web micro-framework that combines simplicity with
    power. It provides routing, middleware, dependency injection, configuration
    management, CLI tools, database integration, and more — all in a minimal
    footprint. Think of it as the Ruby equivalent of Laravel's Lumen.
  DESC
  spec.homepage      = 'https://github.com/ylmz/ylmz-ruby'
  spec.license       = 'MIT'
  spec.required_ruby_version = '>= 2.6.0'

  spec.metadata['homepage_uri']    = spec.homepage
  spec.metadata['source_code_uri'] = spec.homepage

  spec.files = Dir['lib/**/*.rb', 'bin/*', 'README.md', 'LICENSE.txt', '.gitignore']
  spec.bindir        = 'bin'
  spec.executables   = ['ylmz']
  spec.require_paths = ['lib']

  spec.add_dependency 'rack', '>= 2.2', '< 4'
  spec.add_dependency 'thor', '~> 1.2'
  spec.add_dependency 'dotenv', '~> 2.8'

  spec.add_development_dependency 'bundler', '>= 1.17'
  spec.add_development_dependency 'rake', '~> 13.0'
  spec.add_development_dependency 'rspec', '~> 3.12'
  spec.add_development_dependency 'rack-test', '~> 2.1'
end
