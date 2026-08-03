# frozen_string_literal: true

require_relative 'spec_helper'

RSpec.describe Ylmz::Config do
  subject(:config) { described_class.new }

  describe '#set and #get' do
    it 'stores and retrieves values' do
      config.set(:app_name, 'MyApp')
      expect(config.get(:app_name)).to eq('MyApp')
    end

    it 'returns nil for unknown keys' do
      expect(config.get(:unknown)).to be_nil
    end

    it 'returns default value when key not found' do
      expect(config.get(:unknown, 'default')).to eq('default')
    end

    it 'falls back to ENV' do
      ENV['TEST_CONFIG_KEY'] = 'from_env'
      expect(config.get(:test_config_key)).to eq('from_env')
      ENV.delete('TEST_CONFIG_KEY')
    end
  end

  describe '#[] and #[]=' do
    it 'supports bracket access' do
      config[:debug] = true
      expect(config[:debug]).to be true
    end
  end

  describe '#method_missing' do
    it 'reads via method' do
      config.set(:host, 'localhost')
      expect(config.host).to eq('localhost')
    end

    it 'writes via method=' do
      config.port = 3000
      expect(config.get(:port)).to eq(3000)
    end
  end

  describe '#merge!' do
    it 'merges a hash into config' do
      config.merge!(a: 1, b: 2)
      expect(config.to_h).to include(a: 1, b: 2)
    end
  end
end
