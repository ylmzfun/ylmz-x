package com.ylmz.framework.core;

import java.lang.reflect.Method;
import java.util.*;

/**
 * Bean 元数据 —— 描述一个 Bean 的完整信息（原型模式实现）
 */
public class BeanDefinition {
    private final String beanName;
    private final Class<?> beanClass;
    private Object instance;
    private boolean singleton = true;
    private boolean initialized;
    private Object factoryBean;
    private Method factoryMethod;
    private final Map<String, Object> propertyValues = new LinkedHashMap<>();
    private final List<BeanDefinition> dependsOn = new ArrayList<>();
    private String scope = "singleton";

    public BeanDefinition(String beanName, Class<?> beanClass) {
        this.beanName = beanName;
        this.beanClass = beanClass;
    }

    public BeanDefinition copy() {
        BeanDefinition copy = new BeanDefinition(beanName, beanClass);
        copy.singleton = this.singleton;
        copy.factoryBean = this.factoryBean;
        copy.factoryMethod = this.factoryMethod;
        copy.scope = this.scope;
        return copy;
    }

    public String getBeanName() { return beanName; }
    public Class<?> getBeanClass() { return beanClass; }

    public Object getInstance() { return instance; }
    public void setInstance(Object instance) { this.instance = instance; }

    public boolean isSingleton() { return singleton; }
    public void setSingleton(boolean singleton) { this.singleton = singleton; }

    public boolean isInitialized() { return initialized; }
    public void setInitialized(boolean initialized) { this.initialized = initialized; }

    public Object getFactoryBean() { return factoryBean; }
    public void setFactoryBean(Object factoryBean) { this.factoryBean = factoryBean; }

    public Method getFactoryMethod() { return factoryMethod; }
    public void setFactoryMethod(Method factoryMethod) { this.factoryMethod = factoryMethod; }

    public Map<String, Object> getPropertyValues() { return propertyValues; }

    public List<BeanDefinition> getDependsOn() { return dependsOn; }

    public String getScope() { return scope; }
    public void setScope(String scope) { this.scope = scope; }

    @Override
    public String toString() {
        return "BeanDefinition{name='" + beanName + "', class=" + beanClass.getName() + '}';
    }
}
