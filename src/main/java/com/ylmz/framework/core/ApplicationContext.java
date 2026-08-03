package com.ylmz.framework.core;

/**
 * ApplicationContext —— 门面模式，统一对外接口
 */
public interface ApplicationContext extends BeanFactory {

    String getApplicationName();

    Class<?> getMainApplicationClass();

    String[] getActiveProfiles();

    String getProperty(String key);

    String getProperty(String key, String defaultValue);

    void publishEvent(Object event);

    void close();
}
