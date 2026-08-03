package com.ylmz.demo.web;

import com.ylmz.framework.annotations.Component;
import com.ylmz.framework.web.Filter;
import com.ylmz.framework.web.FilterChain;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

/**
 * 请求日志过滤器 —— 责任链模式
 */
@Component
public class LoggingFilter implements Filter {

    @Override
    public void doFilter(HttpServletRequest request, HttpServletResponse response,
                          FilterChain chain) throws Exception {
        System.out.println("[filter] >>> " + request.getMethod() + " " + request.getRequestURI());
        chain.doFilter(request, response);
        System.out.println("[filter] <<< " + response.getStatus());
    }
}
