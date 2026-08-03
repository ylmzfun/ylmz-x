package com.ylmz.framework.web;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

/**
 * 过滤器 —— 责任链模式
 */
public interface Filter {
    void doFilter(HttpServletRequest request, HttpServletResponse response, FilterChain chain) throws Exception;
}
