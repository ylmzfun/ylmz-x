# frozen_string_literal: true

require_relative 'spec_helper'

RSpec.describe Ylmz::Request do
  let(:env) do
    Rack::MockRequest.env_for('/users/42?page=1&sort=desc',
                              method: 'GET',
                              'HTTP_ACCEPT' => 'application/json')
  end

  subject(:request) { described_class.new(env) }

  describe '#method' do
    it { expect(request.method).to eq('GET') }
  end

  describe '#path' do
    it { expect(request.path).to eq('/users/42') }
  end

  describe '#query' do
    it 'parses query string parameters' do
      expect(request.query).to include('page' => '1', 'sort' => 'desc')
    end
  end

  describe '#header' do
    it 'reads HTTP headers' do
      expect(request.header('Accept')).to eq('application/json')
    end
  end

  describe '#url' do
    it { expect(request.url).to include('/users/42') }
  end

  describe '#route_params' do
    it 'stores and retrieves route params' do
      request.merge_route_params!('id' => '42')
      expect(request.param('id')).to eq('42')
    end
  end

  describe '#all' do
    it 'merges query, body, and route params' do
      request.merge_route_params!('id' => '42')
      all = request.all
      expect(all).to include('page' => '1', 'id' => '42')
    end
  end

  describe '#only' do
    it 'filters to specified keys' do
      expect(request.only('page')).to eq('page' => '1')
    end
  end

  describe '#except' do
    it 'excludes specified keys' do
      result = request.except('sort')
      expect(result).not_to include('sort')
      expect(result).to include('page')
    end
  end

  describe '#has?' do
    it { expect(request.has?('page')).to be true }
    it { expect(request.has?('unknown')).to be false }
  end

  describe 'JSON body parsing' do
    let(:env) do
      Rack::MockRequest.env_for('/api/data',
                                method: 'POST',
                                'CONTENT_TYPE' => 'application/json',
                                input: JSON.generate(name: 'test', age: 30))
    end

    it 'parses JSON body' do
      expect(request.all).to include('name' => 'test', 'age' => 30)
    end

    it 'detects JSON requests' do
      expect(request.json?).to be true
    end
  end
end
