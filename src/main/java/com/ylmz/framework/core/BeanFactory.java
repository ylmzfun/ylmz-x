package com.ylmz.framework.core;

/**
 * BeanFactory 接口 —— 工厂模式 + 门面模式
 */
public interface BeanFactory {

    Object getBean(String name);

    <T> T getBean(Class<T> requiredType);

    <T> T getBean(String name, Class<T> requiredType);

    boolean containsBean(String name);

    Class<?> getType(String name);

    boolean isSingleton(String name);
}
