# frozen_string_literal: true

require_relative 'spec_helper'
require 'rack/test'

RSpec.describe Ylmz::Application do
  include Rack::Test::Methods

  let(:app) do
    a = Ylmz::Application.new
    a.routes do
      get '/hello', to: ->(_req) { Ylmz::Response.json({ hello: 'world' }) }
      post '/echo', to: ->(req) { Ylmz::Response.json(req.all) }
      get '/users', to: ->(_req) { Ylmz::Response.json({ users: [{ id: 1 }, { id: 2 }] }) }
      get '/error', to: ->(_req) { raise 'Something went wrong' }
    end
    a
  end

  describe 'GET requests' do
    it 'returns JSON response for /hello' do
      get '/hello'
      expect(last_response.status).to eq(200)
      expect(JSON.parse(last_response.body)).to eq('hello' => 'world')
    end

    it 'returns 404 for unknown routes' do
      get '/nonexistent'
      expect(last_response.status).to eq(404)
    end

    it 'handles errors gracefully' do
      get '/error'
      expect(last_response.status).to eq(500)
      expect(JSON.parse(last_response.body)['error']).to include('Something went wrong')
    end
  end

  describe 'POST requests' do
    it 'echoes posted data' do
      post '/echo', JSON.generate({ name: 'test' }), 'CONTENT_TYPE' => 'application/json'
      expect(last_response.status).to eq(200)
      expect(JSON.parse(last_response.body)).to include('name' => 'test')
    end
  end

  describe '#routes' do
    it 'returns array of routes' do
      routes = app.router.routes
      expect(routes.length).to be >= 3
      expect(routes.map { |r| r[:method] }).to include('GET', 'POST')
    end
  end

  describe '#env' do
    it 'defaults to development' do
      expect(app.env).to eq('development')
    end
  end

  describe '#development?' do
    it { expect(app.development?).to be true }
    it { expect(app.production?).to be false }
  end
end
