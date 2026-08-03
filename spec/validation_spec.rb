# frozen_string_literal: true

require_relative 'spec_helper'

RSpec.describe Ylmz::Validation do
  describe '.check' do
    it 'returns a validation instance' do
      v = described_class.check({ name: 'John' }) { required :name }
      expect(v).to be_valid
    end
  end

  describe '#required' do
    it 'fails when key is missing' do
      v = described_class.check({}) { required :name }
      expect(v).not_to be_valid
      expect(v.errors['name']).to match(/required/)
    end

    it 'fails when value is blank string' do
      v = described_class.check({ name: '  ' }) { required :name }
      expect(v).not_to be_valid
    end

    it 'passes when value is present' do
      v = described_class.check({ name: 'John' }) { required :name }
      expect(v).to be_valid
    end
  end

  describe '#string' do
    it 'fails for non-string values' do
      v = described_class.check({ name: 123 }) { string :name }
      expect(v).not_to be_valid
    end

    it 'passes for strings' do
      v = described_class.check({ name: 'John' }) { string :name }
      expect(v).to be_valid
    end
  end

  describe '#integer' do
    it 'passes for integers' do
      v = described_class.check({ age: 30 }) { integer :age }
      expect(v).to be_valid
    end

    it 'fails for non-integer strings' do
      v = described_class.check({ age: 'hello' }) { integer :age }
      expect(v).not_to be_valid
    end

    it 'passes for string integers' do
      v = described_class.check({ age: '30' }) { integer :age }
      expect(v).to be_valid
    end
  end

  describe '#email' do
    it 'validates email format' do
      v = described_class.check({ email: 'test@example.com' }) { email :email }
      expect(v).to be_valid
    end

    it 'rejects invalid email' do
      v = described_class.check({ email: 'not-an-email' }) { email :email }
      expect(v).not_to be_valid
    end
  end

  describe '#min and #max' do
    it 'validates minimum length' do
      v = described_class.check({ password: '123' }) { min :password, 6 }
      expect(v).not_to be_valid
    end

    it 'validates maximum length' do
      v = described_class.check({ name: 'very-long-name' }) { max :name, 5 }
      expect(v).not_to be_valid
    end
  end

  describe '#in_range' do
    it 'validates inclusion in a range' do
      v = described_class.check({ status: 'active' }) { in_range :status, %w[active inactive] }
      expect(v).to be_valid
    end

    it 'fails when value not in range' do
      v = described_class.check({ status: 'deleted' }) { in_range :status, %w[active inactive] }
      expect(v).not_to be_valid
    end
  end

  describe '#url' do
    it 'validates URL format' do
      v = described_class.check({ website: 'https://example.com' }) { url :website }
      expect(v).to be_valid
    end

    it 'rejects invalid URL' do
      v = described_class.check({ website: 'not-a-url' }) { url :website }
      expect(v).not_to be_valid
    end
  end

  describe '#validate!' do
    it 'raises ValidationError when invalid' do
      expect do
        described_class.check({}) do
          required :name
        end.validate!
      end.to raise_error(Ylmz::ValidationError)
    end

    it 'returns true when valid' do
      result = described_class.check({ name: 'John' }) do
        required :name
      end.validate!
      expect(result).to be true
    end
  end

  describe '#validated' do
    it 'returns only validated keys' do
      v = described_class.check({ name: 'John', age: 30, extra: 'x' })
      expect(v.validated(:name, :age)).to eq('name' => 'John', 'age' => 30)
    end
  end

  describe 'chaining' do
    it 'supports multiple rules on one key' do
      v = described_class.check({ name: 'A' }) do
        required :name
        min :name, 3
      end
      expect(v).not_to be_valid
    end
  end
end
