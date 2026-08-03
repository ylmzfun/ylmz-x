# frozen_string_literal: true

require_relative 'spec_helper'

RSpec.describe Ylmz::Router do
  describe '.define' do
    it 'creates a router with routes' do
      router = described_class.define do
        get '/hello', to: ->(_req) { Ylmz::Response.text('world') }
      end

      expect(router.routes.length).to eq(1)
      expect(router.routes.first[:method]).to eq('GET')
    end
  end

  describe '#dispatch' do
    let(:router) do
      described_class.define do
        get '/', to: ->(_req) { Ylmz::Response.json({ root: true }) }
        get '/users', to: ->(_req) { Ylmz::Response.json({ users: [] }) }
        get '/users/:id', to: ->(req) { Ylmz::Response.json({ id: req.param('id') }) }
        post '/users', to: ->(_req) { Ylmz::Response.json({ created: true }, 201) }
        delete '/users/:id', to: ->(req) { Ylmz::Response.no_content }
        any '/ping', to: ->(_req) { Ylmz::Response.text('pong') }
      end
    end

    it 'dispatches GET /' do
      env = Rack::MockRequest.env_for('/')
      request = Ylmz::Request.new(env)
      response = router.dispatch(request)
      expect(response.status).to eq(200)
    end

    it 'dispatches GET with route params' do
      env = Rack::MockRequest.env_for('/users/42')
      request = Ylmz::Request.new(env)
      response = router.dispatch(request)
      expect(response.status).to eq(200)
      expect(JSON.parse(response.body)).to eq('id' => '42')
    end

    it 'dispatches POST /users' do
      env = Rack::MockRequest.env_for('/users', method: 'POST')
      request = Ylmz::Request.new(env)
      response = router.dispatch(request)
      expect(response.status).to eq(201)
    end

    it 'dispatches DELETE /users/:id' do
      env = Rack::MockRequest.env_for('/users/1', method: 'DELETE')
      request = Ylmz::Request.new(env)
      response = router.dispatch(request)
      expect(response.status).to eq(204)
    end

    it 'matches any method with #any' do
      %w[GET POST PUT].each do |method|
        env = Rack::MockRequest.env_for('/ping', method: method)
        request = Ylmz::Request.new(env)
        response = router.dispatch(request)
        expect(response.status).to eq(200)
        expect(response.body).to eq('pong')
      end
    end

    it 'returns 404 for unknown routes' do
      env = Rack::MockRequest.env_for('/nonexistent')
      request = Ylmz::Request.new(env)
      response = router.dispatch(request)
      expect(response.status).to eq(404)
    end
  end

  describe 'route groups' do
    let(:router) do
      described_class.define do
        group prefix: '/api/v1' do
          get '/status', to: ->(_req) { Ylmz::Response.json({ ok: true }) }
        end

        group prefix: '/admin' do
          get '/dashboard', to: ->(_req) { Ylmz::Response.text('admin') }
        end
      end
    end

    it 'prepends group prefix to routes' do
      routes = router.routes.map { |r| r[:path] }
      expect(routes).to include('/api/v1/status')
      expect(routes).to include('/admin/dashboard')
    end

    it 'dispatches grouped routes' do
      env = Rack::MockRequest.env_for('/api/v1/status')
      request = Ylmz::Request.new(env)
      response = router.dispatch(request)
      expect(response.status).to eq(200)
    end
  end

  describe '#match' do
    let(:router) do
      described_class.define do
        match %i[get post], '/form', to: ->(_req) { Ylmz::Response.text('form') }
      end
    end

    it 'matches multiple methods' do
      get_env = Rack::MockRequest.env_for('/form', method: 'GET')
      post_env = Rack::MockRequest.env_for('/form', method: 'POST')

      expect(router.dispatch(Ylmz::Request.new(get_env)).status).to eq(200)
      expect(router.dispatch(Ylmz::Request.new(post_env)).status).to eq(200)
    end
  end

  describe '#url_for' do
    let(:router) do
      described_class.define do
        get '/users/:id/profile', to: ->(_req) { Ylmz::Response.text('profile') }, as: :user_profile
      end
    end

    it 'generates URL from named route' do
      expect(router.url_for(:user_profile, id: 5)).to eq('/users/5/profile')
    end
  end
end
