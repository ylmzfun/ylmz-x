package com.ylmz.framework.web;

import com.google.gson.Gson;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.lang.reflect.Method;
import java.lang.reflect.Parameter;
import java.util.Map;

/**
 * 处理器适配器 —— 适配器模式
 * 负责参数解析和方法调用
 */
public class HandlerAdapter {
    private final Gson gson = new Gson();

    public void handle(HandlerMapping.HandlerMethod handlerMethod,
                        HttpServletRequest req, HttpServletResponse resp,
                        Map<String, String> pathVars) throws Exception {
        Method method = handlerMethod.method;
        Object[] args = resolveArgs(method, req, resp, pathVars);
        Object result = method.invoke(handlerMethod.bean, args);
        writeResponse(result, resp);
    }

    private Object[] resolveArgs(Method method, HttpServletRequest req,
                                  HttpServletResponse resp, Map<String, String> pathVars) {
        Parameter[] params = method.getParameters();
        Object[] args = new Object[params.length];
        for (int i = 0; i < params.length; i++) {
            args[i] = resolveArg(params[i], req, resp, pathVars);
        }
        return args;
    }

    private Object resolveArg(Parameter param, HttpServletRequest req,
                               HttpServletResponse resp, Map<String, String> pathVars) {
        Class<?> type = param.getType();

        if (type == HttpServletRequest.class) return req;
        if (type == HttpServletResponse.class) return resp;
        if (type == Map.class) return pathVars;

        // 先查路径变量
        String pathValue = pathVars.get(param.getName());
        if (pathValue != null) return convert(pathValue, type);

        // 查请求参数
        String paramValue = req.getParameter(param.getName());
        if (paramValue != null) return convert(paramValue, type);

        // 尝试从 Body 解析 JSON
        if (type != String.class && !type.isPrimitive() && type.getPackageName().startsWith("com.ylmz")) {
            try {
                String body = new String(req.getInputStream().readAllBytes());
                if (!body.isEmpty()) return gson.fromJson(body, type);
            } catch (IOException ignored) {}
        }

        return null;
    }

    private void writeResponse(Object result, HttpServletResponse resp) throws IOException {
        if (result == null) {
            resp.setStatus(200);
            return;
        }
        resp.setContentType("application/json;charset=UTF-8");
        resp.setCharacterEncoding("UTF-8");
        resp.getWriter().write(result instanceof String ? (String) result : gson.toJson(result));
    }

    @SuppressWarnings("unchecked")
    private <T> T convert(String value, Class<T> type) {
        if (type == String.class) return (T) value;
        if (type == int.class || type == Integer.class) return (T) Integer.valueOf(value);
        if (type == long.class || type == Long.class) return (T) Long.valueOf(value);
        if (type == boolean.class || type == Boolean.class) return (T) Boolean.valueOf(value);
        return (T) value;
    }
}
