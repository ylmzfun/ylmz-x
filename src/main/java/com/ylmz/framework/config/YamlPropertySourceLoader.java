package com.ylmz.framework.config;

import java.util.Properties;

/**
 * YAML 属性源加载器
 */
public class YamlPropertySourceLoader {

    public static PropertySource load(String name, String yamlContent) {
        PropertySource source = new PropertySource(name);
        if (yamlContent == null || yamlContent.isBlank()) return source;

        String[] lines = yamlContent.split("\n");
        String prefix = "";
        for (String line : lines) {
            String trimmed = line.strip();
            if (trimmed.isEmpty() || trimmed.startsWith("#")) continue;

            int indent = line.indexOf(trimmed);
            int level = indent / 2;

            if (trimmed.endsWith(":")) {
                String key = trimmed.substring(0, trimmed.length() - 1).strip();
                if (level == 0) {
                    prefix = key;
                }
            } else {
                int colonIdx = trimmed.indexOf(':');
                if (colonIdx > 0) {
                    String key = trimmed.substring(0, colonIdx).strip();
                    String value = trimmed.substring(colonIdx + 1).strip();
                    String fullKey = prefix.isEmpty() ? key : prefix + "." + key;
                    source.add(fullKey, value);
                }
            }
        }
        return source;
    }

    public static PropertySource loadProperties(String name, Properties props) {
        PropertySource source = new PropertySource(name);
        for (String key : props.stringPropertyNames()) {
            source.add(key, props.getProperty(key));
        }
        return source;
    }
}
