package com.ylmz.framework.web;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.util.Iterator;
import java.util.List;

/**
 * 过滤器链 —— 责任链模式
 */
public class FilterChain {
    private final Iterator<Filter> filters;
    private final ServletHandler handler;

    public FilterChain(List<Filter> filters, ServletHandler handler) {
        this.filters = filters.iterator();
        this.handler = handler;
    }

    public void doFilter(HttpServletRequest req, HttpServletResponse resp) throws Exception {
        if (filters.hasNext()) {
            filters.next().doFilter(req, resp, this);
        } else {
            handler.handle(req, resp);
        }
    }

    @FunctionalInterface
    public interface ServletHandler {
        void handle(HttpServletRequest req, HttpServletResponse resp) throws Exception;
    }
}
