# frozen_string_literal: true

require_relative 'spec_helper'

RSpec.describe Ylmz::Response do
  describe '.json' do
    it 'creates a JSON response' do
      resp = described_class.json({ hello: 'world' })
      expect(resp.status).to eq(200)
      expect(resp.headers['Content-Type']).to include('application/json')
      expect(JSON.parse(resp.body)).to eq('hello' => 'world')
    end
  end

  describe '.text' do
    it 'creates a text response' do
      resp = described_class.text('plain text')
      expect(resp.status).to eq(200)
      expect(resp.headers['Content-Type']).to include('text/plain')
      expect(resp.body).to eq('plain text')
    end
  end

  describe '.redirect' do
    it 'creates a redirect response' do
      resp = described_class.redirect('/dashboard')
      expect(resp.status).to eq(302)
      expect(resp.headers['Location']).to eq('/dashboard')
    end
  end

  describe '.no_content' do
    it 'creates a 204 response' do
      resp = described_class.no_content
      expect(resp.status).to eq(204)
    end
  end

  describe '.error' do
    it 'creates an error JSON response' do
      resp = described_class.error('Not Found', 404)
      expect(resp.status).to eq(404)
      payload = JSON.parse(resp.body)
      expect(payload['error']).to eq('Not Found')
    end

    it 'includes validation errors' do
      resp = described_class.error('Validation', 422, { name: ['required'] })
      payload = JSON.parse(resp.body)
      expect(payload['errors']).to eq('name' => ['required'])
    end
  end

  describe '.success' do
    it 'creates a success response with data' do
      resp = described_class.success({ id: 1 }, 'Created', 201)
      expect(resp.status).to eq(201)
      payload = JSON.parse(resp.body)
      expect(payload['message']).to eq('Created')
      expect(payload['data']).to eq('id' => 1)
    end
  end

  describe '.html' do
    it 'creates an HTML response' do
      resp = described_class.html('<h1>Hello</h1>')
      expect(resp.headers['Content-Type']).to include('text/html')
      expect(resp.body).to eq('<h1>Hello</h1>')
    end
  end

  describe '#finish' do
    it 'returns a Rack-compatible array' do
      resp = described_class.json({ ok: true })
      status, headers, body = resp.finish
      expect(status).to eq(200)
      expect(headers['Content-Type']).to include('application/json')
      expect(body).to be_an(Array)
    end
  end

  describe '#status and #header' do
    it 'supports chaining' do
      resp = described_class.new.status(201).header('X-Custom', 'value')
      expect(resp.status).to eq(201)
      expect(resp.headers['X-Custom']).to eq('value')
    end
  end
end
