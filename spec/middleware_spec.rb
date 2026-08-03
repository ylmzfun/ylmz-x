# frozen_string_literal: true

require_relative 'spec_helper'

RSpec.describe Ylmz::Middleware do
  subject(:middleware) { described_class.new }

  let(:simple_mw) do
    Class.new do
      def initialize(app)
        @app = app
      end

      def call(env)
        status, headers, body = @app.call(env)
        headers['X-Middleware'] = 'yes'
        [status, headers, body]
      end
    end
  end

  let(:block_mw) do
    Class.new do
      def initialize(app, &block)
        @app = app
        @block = block
      end

      def call(env)
        @block.call(env)
        @app.call(env)
      end
    end
  end

  describe '#use' do
    it 'adds middleware to the stack' do
      middleware.use(simple_mw)
      expect(middleware.stack.length).to eq(1)
      expect(middleware.stack.first[:klass]).to eq(simple_mw)
    end
  end

  describe '#build' do
    it 'wraps the app in middleware' do
      middleware.use(simple_mw)

      app = proc { [200, {}, ['ok']] }
      wrapped = middleware.build(app)

      status, headers, body = wrapped.call({})
      expect(status).to eq(200)
      expect(headers['X-Middleware']).to eq('yes')
      expect(body).to eq(['ok'])
    end
  end

  describe '#insert_before' do
    it 'inserts middleware before another' do
      mw_a = Class.new do
        def initialize(app); @app = app; end
        def call(e); @app.call(e); end
      end
      mw_b = Class.new do
        def initialize(app); @app = app; end
        def call(e); @app.call(e); end
      end

      middleware.use(mw_a)
      middleware.insert_before(mw_a, mw_b)

      expect(middleware.stack[0][:klass]).to eq(mw_b)
      expect(middleware.stack[1][:klass]).to eq(mw_a)
    end
  end

  describe '#insert_after' do
    it 'inserts middleware after another' do
      mw_a = Class.new do
        def initialize(app); @app = app; end
        def call(e); @app.call(e); end
      end
      mw_b = Class.new do
        def initialize(app); @app = app; end
        def call(e); @app.call(e); end
      end

      middleware.use(mw_a)
      middleware.insert_after(mw_a, mw_b)

      expect(middleware.stack[0][:klass]).to eq(mw_a)
      expect(middleware.stack[1][:klass]).to eq(mw_b)
    end
  end

  describe '#remove' do
    it 'removes middleware from the stack' do
      middleware.use(simple_mw)
      middleware.remove(simple_mw)
      expect(middleware.stack).to be_empty
    end
  end
end
