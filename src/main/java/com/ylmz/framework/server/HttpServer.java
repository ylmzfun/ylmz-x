package com.ylmz.framework.server;

/**
 * HTTP Server 接口 —— 策略模式 + 适配器模式
 */
public interface HttpServer {

    void start(int port);

    void stop();

    boolean isRunning();
}
