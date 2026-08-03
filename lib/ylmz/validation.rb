# frozen_string_literal: true

module Ylmz
  class Validation
    attr_reader :errors, :data

    def initialize(data)
      @data = (data || {}).each_with_object({}) { |(k, v), h| h[k.to_s] = v }
      @errors = {}
    end

    # --- Built-in Rules ---

    def required(key, message: nil)
      value = @data[key.to_s]
      if value.nil? || (value.is_a?(String) && value.strip.empty?)
        @errors[key.to_s] = message || "#{key} is required"
      end
      self
    end

    def string(key, message: nil)
      value = @data[key.to_s]
      return self if value.nil?

      @errors[key.to_s] = message || "#{key} must be a string" unless value.is_a?(String)
      self
    end

    def integer(key, message: nil)
      value = @data[key.to_s]
      return self if value.nil?

      int_val = value.is_a?(Integer) ? value : (Integer(value.to_s) rescue nil)
      @errors[key.to_s] = message || "#{key} must be an integer" if int_val.nil?
      self
    end

    def numeric(key, message: nil)
      value = @data[key.to_s]
      return self if value.nil?

      num_val = value.is_a?(Numeric) ? value : (Float(value.to_s) rescue nil)
      @errors[key.to_s] = message || "#{key} must be a number" if num_val.nil?
      self
    end

    def boolean(key, message: nil)
      value = @data[key.to_s]
      return self if value.nil?

      bool_val = truthy?(value)
      @errors[key.to_s] = message || "#{key} must be a boolean" unless [true, false].include?(bool_val)
      self
    end

    def email(key, message: nil)
      value = @data[key.to_s]
      return self if value.nil?

      valid = value.to_s.match?(/\A[^@\s]+@[^@\s]+\.[^@\s]+\z/)
      @errors[key.to_s] = message || "#{key} must be a valid email address" unless valid
      self
    end

    def min(key, length, message: nil)
      value = @data[key.to_s]
      return self if value.nil?

      if value.respond_to?(:length) && value.length < length
        @errors[key.to_s] = message || "#{key} must be at least #{length} characters"
      end
      self
    end

    def max(key, length, message: nil)
      value = @data[key.to_s]
      return self if value.nil?

      if value.respond_to?(:length) && value.length > length
        @errors[key.to_s] = message || "#{key} must be at most #{length} characters"
      end
      self
    end

    def in_range(key, range, message: nil)
      value = @data[key.to_s]
      return self if value.nil?

      unless range.include?(value.to_s)
        @errors[key.to_s] = message || "#{key} must be one of: #{range.to_a.join(', ')}"
      end
      self
    end

    def url(key, message: nil)
      value = @data[key.to_s]
      return self if value.nil?

      valid = value.to_s.match?(%r{\Ahttps?://[^\s/$.?#].[^\s]*\z})
      @errors[key.to_s] = message || "#{key} must be a valid URL" unless valid
      self
    end

    # Add a custom error.
    def add(key, message)
      (@errors[key.to_s] ||= []) << message
      self
    end

    # Check if validation passed.
    def valid?
      @errors.empty?
    end

    # Raise if invalid, otherwise return true.
    def validate!
      raise ValidationError, @errors.to_json unless valid?

      true
    end

    # Get validated-only data.
    def validated(*keys)
      return @data if keys.empty?

      @data.select { |k, _| keys.map(&:to_s).include?(k) }
    end

    # Create a new validation and run the block.
    def self.check(data, &block)
      v = new(data)
      v.instance_eval(&block) if block
      v
    end

    private

    def truthy?(value)
      return true if [true, 'true', '1', 1, 'yes', 'on'].include?(value)
      return false if [false, 'false', '0', 0, 'no', 'off'].include?(value)

      !!value
    end
  end
end
