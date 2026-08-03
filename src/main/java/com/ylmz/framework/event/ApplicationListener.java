package com.ylmz.framework.event;

/**
 * 事件监听器 —— 观察者模式
 */
@FunctionalInterface
public interface ApplicationListener<E> {
    void onApplicationEvent(E event);
}
