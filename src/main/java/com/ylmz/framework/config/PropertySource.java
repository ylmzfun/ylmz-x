package com.ylmz.framework.config;

import java.util.*;

/**
 * 属性源
 */
public class PropertySource {
    private final String name;
    private final Map<String, String> properties = new LinkedHashMap<>();

    public PropertySource(String name) {
        this.name = name;
    }

    public String getName() { return name; }

    public PropertySource add(String key, String value) {
        properties.put(key, value);
        return this;
    }

    public String get(String key) {
        return properties.get(key);
    }

    public boolean contains(String key) {
        return properties.containsKey(key);
    }

    public Map<String, String> getAll() {
        return Collections.unmodifiableMap(properties);
    }
}
