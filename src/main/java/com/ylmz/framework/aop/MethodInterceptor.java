package com.ylmz.framework.aop;

/**
 * 方法拦截器 —— 策略模式
 */
@FunctionalInterface
public interface MethodInterceptor {
    Object intercept(MethodInvocation invocation) throws Throwable;
}
