# Ylmz-Ruby

A lightweight yet comprehensive Ruby web micro-framework inspired by PHP's Lumen.

Ylmz is a **Rack-based** Ruby web framework that combines simplicity with power — like a micro version of Rails, or Ruby's answer to Lumen.

## Features

- 🚀 **Fast Routing** — RESTful routes, route parameters, named routes, and group prefixes
- 🔗 **Middleware Pipeline** — Global and route-level middleware with insert/remove control
- 📦 **Service Container** — Dependency injection with singleton and alias support
- ⚙️ **Configuration** — `.env` + `config/` directory, with ENV fallback
- 🛠️ **CLI Tool** — Project scaffolding, dev server, route listing, interactive console
- ✅ **Validation** — Built-in validators (required, string, integer, email, URL, min/max, enum)
- 🗄️ **Database Ready** — Optional Sequel integration (just uncomment in config/database.rb)
- 📝 **Controller Base** — JSON/text/HTML/redirect helpers built in

## Installation

### Requirements

- Ruby >= 2.6.0
- Bundler

```ruby
# In your Gemfile
gem 'ylmz-ruby'
```

Or use the CLI to create a new project:

```bash
ylmz new my-app
cd my-app
bundle install
ylmz serve
```

## Quick Start

### Create a new project

```bash
ylmz new my-api
cd my-api
bundle install
```

### Define routes

Edit `config/routes.rb`:

```ruby
# Basic routes
get '/', to: ->(_req) { Ylmz::Response.json({ message: 'Hello Ylmz!' }) }

# Route with parameters
get '/users/:id', to: ->(req) {
  Ylmz::Response.json({ user_id: req.param('id') })
}

# Route groups
group prefix: '/api/v1' do
  get '/status', to: ->(_req) { Ylmz::Response.json({ status: 'ok' }) }

  post '/users', to: ->(req) {
    Ylmz::Response.json(req.all, 201)
  }
end

# Named routes
get '/profile', to: ->(_req) { Ylmz::Response.text('Profile') }, as: :profile
```

### Using Controllers

Create `app/controllers/users_controller.rb`:

```ruby
class UsersController < Ylmz::Controller
  def index
    users = [{ id: 1, name: 'Alice' }, { id: 2, name: 'Bob' }]
    success(users)
  end

  def show
    success({ id: request.param('id') })
  end

  def create
    validate do
      required :name
      email :email
    end

    success({ created: true }, 'User created')
  end
end
```

Then in `config/routes.rb`:

```ruby
get  '/users',     to: 'UsersController@index'
get  '/users/:id', to: 'UsersController@show'
post '/users',     to: 'UsersController@create'
```

### Middleware

In `config/application.rb`:

```ruby
class App < Ylmz::Application
  def initialize(base_path = __dir__ + '/..')
    super(base_path)

    middleware.use(Rack::Runtime)
    middleware.use(Rack::CommonLogger)
    middleware.use(MyCustomMiddleware)
  end
end
```

### Service Container

```ruby
# Register a service
App.container.singleton(:logger, Logger, STDOUT)

# Resolve it anywhere
logger = App.container.make(:logger)
logger.info('Hello from Ylmz!')
```

### Validation

```ruby
validation = Ylmz::Validation.check(params) do
  required :name
  email :email
  min :password, 8
  in_range :status, %w[active inactive]
end

if validation.valid?
  # proceed
else
  # validation.errors contains the error messages
end
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `ylmz new NAME` | Create a new Ylmz project |
| `ylmz serve` | Start development server (default :3000) |
| `ylmz routes` | List all registered routes |
| `ylmz console` | Start IRB with app loaded |
| `ylmz version` | Show framework version |

Options for `ylmz serve`:
- `--port=N` — Listen on port N (default 3000)
- `--host=HOST` — Bind to HOST (default 0.0.0.0)
- `--env=ENV` — Environment (development/production)

## Project Structure

```
my-app/
├── config/
│   ├── application.rb    # App configuration & middleware
│   ├── routes.rb         # Route definitions
│   └── database.rb       # Database config (optional)
├── app/
│   ├── controllers/      # Controller classes
│   ├── middleware/        # Custom middleware
│   └── models/           # Model classes
├── config.ru             # Rack config
├── .env                  # Environment variables
├── Gemfile
└── db/                   # SQLite databases
```

## Development

```bash
# Clone and install dependencies
git clone https://github.com/ylmz/ylmz-ruby.git
cd ylmz-ruby
bundle install --path vendor/bundle

# Run tests (86 examples)
bundle exec rspec

# Or via Rake
bundle exec rake spec
```

## License

MIT — see [LICENSE.txt](LICENSE.txt).
