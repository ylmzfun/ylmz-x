package com.ylmz.framework.core;

/**
 * InitializingBean —— 初始化回调（模板方法模式）
 */
public interface InitializingBean {
    void afterPropertiesSet();
}
