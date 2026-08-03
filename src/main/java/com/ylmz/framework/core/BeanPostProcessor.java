package com.ylmz.framework.core;

/**
 * Bean 后置处理器 —— 模板方法模式的扩展点
 */
public interface BeanPostProcessor {

    default Object postProcessBeforeInitialization(Object bean, String beanName) {
        return bean;
    }

    default Object postProcessAfterInitialization(Object bean, String beanName) {
        return bean;
    }
}
