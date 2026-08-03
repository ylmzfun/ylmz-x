package com.ylmz.framework.server;

import com.ylmz.framework.web.DispatcherServlet;
import jakarta.servlet.Servlet;

/**
 * 嵌入式 Servlet 上下文 —— 用于在启动时注入 DispatcherServlet
 */
public final class EmbeddedServletContext {
    private static Servlet servlet;

    private EmbeddedServletContext() {}

    public static void setServlet(Servlet s) {
        servlet = s;
    }

    public static Servlet getServlet() {
        return servlet;
    }
}
