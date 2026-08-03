# frozen_string_literal: true

require_relative 'spec_helper'
require 'logger'

RSpec.describe Ylmz::Container do
  subject(:container) { described_class.new }

  describe '#bind and #make' do
    it 'binds and resolves a class' do
      container.bind(:logger, Logger, Logger::WARN)
      expect(container.make(:logger)).to be_a(Logger)
    end

    it 'binds and resolves a proc' do
      container.bind(:hello, -> { 'world' })
      expect(container.make(:hello)).to eq('world')
    end

    it 'binds and resolves a block' do
      container.bind(:greeting) { 'hi' }
      expect(container.make(:greeting)).to eq('hi')
    end

    it 'injects container into block when arity > 0' do
      container.bind(:config) { |c| c }
      result = container.make(:config)
      expect(result).to be_a(described_class)
    end
  end

  describe '#singleton' do
    it 'resolves the same instance' do
      container.singleton(:logger, Logger, Logger::WARN)
      first = container.make(:logger)
      second = container.make(:logger)
      expect(first).to be(second)
    end
  end

  describe '#alias' do
    it 'resolves via alias' do
      container.bind(:logger, Logger, Logger::WARN)
      container.alias(:log, :logger)
      expect(container.make(:log)).to be_a(Logger)
    end
  end

  describe '#bound?' do
    it 'returns true for bound services' do
      container.bind(:db, -> { 'connected' })
      expect(container.bound?(:db)).to be true
    end

    it 'returns false for unbound services' do
      expect(container.bound?(:unknown)).to be false
    end
  end

  describe '#forget' do
    it 'removes a binding' do
      container.bind(:temp, -> { 'gone' })
      container.forget(:temp)
      expect(container.bound?(:temp)).to be false
    end
  end

  describe '#flush!' do
    it 'clears all bindings' do
      container.bind(:a, -> { 1 })
      container.bind(:b, -> { 2 })
      container.flush!
      expect(container.bound?(:a)).to be false
      expect(container.bound?(:b)).to be false
    end
  end
end
