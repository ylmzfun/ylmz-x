package com.ylmz.framework.server;

import com.ylmz.framework.web.DispatcherServlet;
import jakarta.servlet.Servlet;
import org.eclipse.jetty.server.Server;
import org.eclipse.jetty.servlet.ServletContextHandler;
import org.eclipse.jetty.servlet.ServletHolder;

/**
 * Jetty 适配器 —— 适配器模式，将 DispatcherServlet 嵌入到 Jetty
 */
public class JettyServer implements HttpServer {
    private Server server;

    @Override
    public void start(int port) {
        try {
            server = new Server(port);
            ServletContextHandler context = new ServletContextHandler(ServletContextHandler.SESSIONS);
            context.setContextPath("/");

            Servlet servlet = EmbeddedServletContext.getServlet();
            if (servlet == null) {
                throw new IllegalStateException("未设置 DispatcherServlet，请先调用 EmbeddedServletContext.setServlet()");
            }

            context.addServlet(new ServletHolder(servlet), "/*");
            server.setHandler(context);
            server.start();
            System.out.println("[ylmz] Jetty 服务器启动成功 → http://localhost:" + port);
        } catch (Exception e) {
            throw new RuntimeException("Jetty 启动失败", e);
        }
    }

    @Override
    public void stop() {
        try {
            if (server != null) server.stop();
        } catch (Exception e) {
            throw new RuntimeException("Jetty 关闭失败", e);
        }
    }

    @Override
    public boolean isRunning() {
        return server != null && server.isRunning();
    }
}
