package com.ylmz.framework.web;

import com.ylmz.framework.annotations.RequestMapping;
import com.ylmz.framework.annotations.RequestMethod;
import java.lang.reflect.Method;
import java.util.*;

/**
 * 处理器映射 —— 策略模式，URL → Handler 匹配
 */
public class HandlerMapping {
    private final List<HandlerMethod> handlers = new ArrayList<>();

    public void register(String path, Object bean, Method method) {
        RequestMapping mapping = method.getAnnotation(RequestMapping.class);
        RequestMethod[] methods = mapping != null ? mapping.method() : new RequestMethod[0];
        handlers.add(new HandlerMethod(path, bean, method, methods));
    }

    public void register(String path, Object bean, Method method, RequestMethod... httpMethods) {
        handlers.add(new HandlerMethod(path, bean, method, httpMethods));
    }

    public HandlerMethod resolve(String requestUri, String httpMethod) {
        for (HandlerMethod hm : handlers) {
            if (matchPath(hm.path, requestUri) && matchMethod(hm.httpMethods, httpMethod)) {
                return hm;
            }
        }
        return null;
    }

    private boolean matchPath(String pattern, String uri) {
        // 支持精确匹配和路径变量匹配 /user/{id}
        if (pattern.equals(uri)) return true;
        String[] patternParts = pattern.split("/");
        String[] uriParts = uri.split("/");
        if (patternParts.length != uriParts.length) return false;
        for (int i = 0; i < patternParts.length; i++) {
            String pp = patternParts[i];
            String up = uriParts[i];
            if (pp.startsWith("{") && pp.endsWith("}")) continue;
            if (!pp.equals(up)) return false;
        }
        return true;
    }

    private boolean matchMethod(RequestMethod[] methods, String httpMethod) {
        if (methods == null || methods.length == 0) return true;
        for (RequestMethod m : methods) {
            if (m.name().equalsIgnoreCase(httpMethod)) return true;
        }
        return false;
    }

    /**
     * 提取路径变量
     */
    public Map<String, String> extractPathVariables(String pattern, String uri) {
        Map<String, String> vars = new LinkedHashMap<>();
        String[] pp = pattern.split("/");
        String[] up = uri.split("/");
        for (int i = 0; i < pp.length && i < up.length; i++) {
            if (pp[i].startsWith("{") && pp[i].endsWith("}")) {
                vars.put(pp[i].substring(1, pp[i].length() - 1), up[i]);
            }
        }
        return vars;
    }

    public static class HandlerMethod {
        public final String path;
        public final Object bean;
        public final Method method;
        public final RequestMethod[] httpMethods;

        HandlerMethod(String path, Object bean, Method method, RequestMethod[] httpMethods) {
            this.path = path;
            this.bean = bean;
            this.method = method;
            this.httpMethods = httpMethods;
        }
    }
}
