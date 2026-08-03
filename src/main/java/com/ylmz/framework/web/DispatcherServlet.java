package com.ylmz.framework.web;

import com.ylmz.framework.annotations.Controller;
import com.ylmz.framework.annotations.RequestMapping;
import com.ylmz.framework.web.FilterChain.ServletHandler;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.lang.reflect.Method;
import java.util.*;

/**
 * 前端控制器 —— 前端控制器模式（Front Controller）
 * 分发请求到具体的 Handler
 */
public class DispatcherServlet extends HttpServlet {
    private final HandlerMapping handlerMapping;
    private final HandlerAdapter handlerAdapter;
    private final List<Filter> filters;

    public DispatcherServlet(HandlerMapping handlerMapping, HandlerAdapter handlerAdapter,
                              List<Filter> filters) {
        this.handlerMapping = handlerMapping;
        this.handlerAdapter = handlerAdapter;
        this.filters = filters;
    }

    /**
     * 注册 Controller 的所有 @RequestMapping 方法
     */
    public void registerController(Object bean) {
        Class<?> clazz = bean.getClass();
        if (!clazz.isAnnotationPresent(Controller.class)) return;

        RequestMapping classMapping = clazz.getAnnotation(RequestMapping.class);
        String basePath = classMapping != null ? classMapping.value() : "";

        for (Method method : clazz.getDeclaredMethods()) {
            RequestMapping methodMapping = method.getAnnotation(RequestMapping.class);
            if (methodMapping == null) continue;

            String fullPath = normalizePath(basePath, methodMapping.value());
            handlerMapping.register(fullPath, bean, method, methodMapping.method());
        }
    }

    @Override
    protected void service(HttpServletRequest req, HttpServletResponse resp) {
        try {
            String uri = req.getRequestURI();
            String method = req.getMethod();

            HandlerMapping.HandlerMethod hm = handlerMapping.resolve(uri, method);
            if (hm == null) {
                resp.setStatus(404);
                resp.getWriter().write("{\"error\":\"Not Found: " + uri + "\"}");
                return;
            }

            Map<String, String> pathVars = handlerMapping.extractPathVariables(hm.path, uri);
            ServletHandler servletHandler = (rq, rs) -> handlerAdapter.handle(hm, rq, rs, pathVars);
            new FilterChain(filters, servletHandler).doFilter(req, resp);

        } catch (Exception e) {
            try {
                resp.setStatus(500);
                resp.getWriter().write("{\"error\":\"" + e.getMessage() + "\"}");
            } catch (Exception ignored) {}
        }
    }

    private String normalizePath(String base, String method) {
        StringBuilder sb = new StringBuilder();
        if (!base.isEmpty()) sb.append(base.startsWith("/") ? base : "/" + base);
        if (!method.isEmpty()) sb.append(method.startsWith("/") ? method : "/" + method);
        return sb.length() == 0 ? "/" : sb.toString();
    }
}
