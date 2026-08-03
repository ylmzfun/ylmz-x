# frozen_string_literal: true

require 'thor'
require 'fileutils'

module Ylmz
  class CLI < Thor
    package_name 'Ylmz'
    default_command :help

    desc 'new PROJECT_NAME', 'Create a new Ylmz project'
    method_option :path, type: :string, default: '.', desc: 'Target directory'
    def new(name)
      target = File.expand_path(name, options[:path])

      if Dir.exist?(target) && !Dir.empty?(target)
        say "Directory '#{target}' already exists and is not empty.", :red
        exit 1
      end

      say "Creating new Ylmz project: #{name}", :green

      scaffold_project(target)
      say "\nProject '#{name}' created successfully!", :green
      say "  cd #{name}"
      say '  bundle install'
      say '  ylmz serve'
    end

    desc 'serve', 'Start the development server'
    method_option :port, type: :numeric, default: 3000, desc: 'Port to listen on'
    method_option :host, type: :string, default: '0.0.0.0', desc: 'Host to bind to'
    method_option :env, type: :string, default: 'development', desc: 'Environment'
    def serve
      ENV['APP_ENV'] = options[:env]
      ENV['RACK_ENV'] = options[:env]

      require 'rack'
      require 'ylmz'

      app_file = File.join(Dir.pwd, 'config', 'application.rb')
      if File.exist?(app_file)
        require app_file
        app = App rescue nil
      end

      unless app
        $stderr.puts 'No config/application.rb found. Creating a basic app.'
        app = Ylmz::Application.new(Dir.pwd)
        app.routes do
          get '/', to: ->(_) { Ylmz::Response.json({ message: 'Ylmz is running!' }) }
        end
      end

      handler = Rack::Handler.get('webrick') || Rack::Handler::WEBrick rescue Rack::Handler::WEBrick

      say "Starting Ylmz server on http://#{options[:host]}:#{options[:port]} [#{options[:env]}]", :green
      handler.run(app, Host: options[:host], Port: options[:port])
    end

    desc 'routes', 'List all registered routes'
    def routes
      require 'ylmz'

      app_file = File.join(Dir.pwd, 'config', 'application.rb')
      if File.exist?(app_file)
        require app_file
        app = App rescue nil
      end

      if app && app.router
        say "\nRegistered Routes:\n"
        say '─' * 70
        say format("%-8s %-40s %s", 'METHOD', 'PATH', 'HANDLER')
        say '─' * 70

        app.router.routes.each do |route|
          say format("%-8s %-40s %s", route[:method], route[:path], route[:handler])
        end
        say '─' * 70
      else
        say 'No routes found.', :yellow
      end
    end

    desc 'console', 'Start an interactive console (IRB) with the app loaded'
    def console
      require 'irb'

      ENV['APP_ENV'] ||= 'development'
      ENV['RACK_ENV'] ||= 'development'

      app_file = File.join(Dir.pwd, 'config', 'application.rb')
      if File.exist?(app_file)
        require app_file
        app = App rescue nil
      end

      require 'ylmz' unless defined?(Ylmz)

      say "Ylmz console [#{ENV['APP_ENV']}]", :green
      say 'App is available as `app`', :cyan if app

      IRB.start
    end

    desc 'version', 'Show Ylmz version'
    def version
      require 'ylmz/version'
      say "Ylmz v#{Ylmz::VERSION}"
    end

    private

    def scaffold_project(target)
      FileUtils.mkdir_p(target)

      %w[config app/controllers app/middleware app/models public db log tmp].each do |dir|
        FileUtils.mkdir_p(File.join(target, dir))
      end

      write_file(target, '.env', <<~ENV)
        APP_ENV=development
        APP_DEBUG=true
        APP_PORT=3000
      ENV

      write_file(target, 'config/application.rb', <<~RUBY)
        # frozen_string_literal: true

        require 'ylmz'

        class App < Ylmz::Application
          def initialize(base_path = __dir__ + '/..')
            super(base_path)

            # Register middleware (run in order).
            middleware.use(Rack::Runtime)
            middleware.use(Rack::CommonLogger)

            # Register service providers here.
            # container.singleton(:logger) { Logger.new(STDOUT) }
          end
        end

        App = App.new
      RUBY

      write_file(target, 'config/routes.rb', <<~RUBY)
        # frozen_string_literal: true

        get '/', to: ->(_req) { Ylmz::Response.json({ message: 'Welcome to Ylmz!' }) }

        get '/health', to: ->(_req) { Ylmz::Response.json({ status: 'ok' }) }

        # Example: route group with prefix
        # group prefix: '/api/v1' do
        #   get '/users', to: 'UsersController@index'
        #   post '/users', to: 'UsersController@create'
        #   get '/users/:id', to: 'UsersController@show'
        # end
      RUBY

      write_file(target, 'config/database.rb', <<~RUBY)
        # frozen_string_literal: true

        # Uncomment and configure if using Sequel.
        # require 'sequel'
        #
        # DB = Sequel.connect(
        #   adapter: 'sqlite',
        #   database: File.join(App.base_path, 'db', 'app.sqlite3')
        # )
      RUBY

      write_file(target, 'Gemfile', <<~RUBY)
        # frozen_string_literal: true

        source 'https://rubygems.org'

        gem 'ylmz-ruby', path: '#{File.expand_path(File.join(__dir__, '..', '..'))}'
        gem 'puma', '~> 6.0'

        # gem 'sequel', '~> 5.0'
        # gem 'sqlite3', '~> 1.6'
      RUBY

      write_file(target, 'config.ru', <<~RUBY)
        # frozen_string_literal: true

        require_relative 'config/application'

        run App
      RUBY

      write_file(target, '.gitignore', <<~GITIGNORE)
        .env
        *.sqlite3
        *.sqlite3-journal
        /tmp/
        /log/*.log
        vendor/bundle/
        .bundle/
      GITIGNORE
    end

    def write_file(target, relative_path, content)
      full_path = File.join(target, relative_path)
      FileUtils.mkdir_p(File.dirname(full_path))
      File.write(full_path, content)
      say "  create  #{relative_path}"
    end
  end
end
