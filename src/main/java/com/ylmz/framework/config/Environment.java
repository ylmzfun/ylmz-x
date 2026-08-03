package com.ylmz.framework.config;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 环境配置 —— 组合模式管理多 PropertySource，支持 ${} 占位符解析
 */
public class Environment {
    private static final Pattern PLACEHOLDER = Pattern.compile("\\$\\{([^}:]+)(?::([^}]*))?}");

    private final List<PropertySource> sources = new ArrayList<>();
    private final String[] activeProfiles;

    public Environment(String... activeProfiles) {
        this.activeProfiles = activeProfiles;
    }

    public void addSource(PropertySource source) {
        sources.add(source);
    }

    public String getProperty(String key) {
        for (PropertySource source : sources) {
            String value = source.get(key);
            if (value != null) return resolvePlaceholders(value);
        }
        return null;
    }

    public String getProperty(String key, String defaultValue) {
        String value = getProperty(key);
        return value != null ? value : defaultValue;
    }

    public <T> T getProperty(String key, Class<T> targetType, T defaultValue) {
        String value = getProperty(key);
        if (value == null) return defaultValue;
        return convert(value, targetType);
    }

    public String resolvePlaceholders(String text) {
        if (text == null) return null;
        Matcher matcher = PLACEHOLDER.matcher(text);
        StringBuilder sb = new StringBuilder();
        while (matcher.find()) {
            String key = matcher.group(1);
            String def = matcher.group(2);
            String resolved = getProperty(key);
            matcher.appendReplacement(sb, Matcher.quoteReplacement(resolved != null ? resolved : (def != null ? def : matcher.group(0))));
        }
        matcher.appendTail(sb);
        return sb.toString();
    }

    public String[] getActiveProfiles() { return activeProfiles; }

    public boolean acceptsProfile(String profile) {
        if (profile == null || profile.isEmpty()) return true;
        for (String active : activeProfiles) {
            if (active.equals(profile)) return true;
        }
        return false;
    }

    @SuppressWarnings("unchecked")
    private <T> T convert(String value, Class<T> targetType) {
        if (targetType == String.class) return (T) value;
        if (targetType == int.class || targetType == Integer.class) return (T) Integer.valueOf(value);
        if (targetType == long.class || targetType == Long.class) return (T) Long.valueOf(value);
        if (targetType == boolean.class || targetType == Boolean.class) return (T) Boolean.valueOf(value);
        if (targetType == double.class || targetType == Double.class) return (T) Double.valueOf(value);
        throw new IllegalArgumentException("不支持的类型: " + targetType);
    }
}
