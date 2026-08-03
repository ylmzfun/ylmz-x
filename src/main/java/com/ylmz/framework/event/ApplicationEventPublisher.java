package com.ylmz.framework.event;

import java.lang.reflect.Method;
import java.lang.reflect.ParameterizedType;
import java.lang.reflect.Type;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * 事件发布器 —— 观察者模式核心
 */
public class ApplicationEventPublisher {
    private final Map<Class<?>, List<ListenerAdapter>> listenerMap = new ConcurrentHashMap<>();

    public void registerListener(Object bean, Method method) {
        Class<?> eventType = resolveEventType(method);
        if (eventType != null) {
            listenerMap.computeIfAbsent(eventType, k -> new CopyOnWriteArrayList<>())
                .add(new ListenerAdapter(bean, method));
        }
    }

    public void publishEvent(Object event) {
        if (event == null) return;
        Class<?> eventType = event.getClass();
        // 遍历类型层级，支持父类事件
        while (eventType != null && eventType != Object.class) {
            List<ListenerAdapter> listeners = listenerMap.get(eventType);
            if (listeners != null) {
                for (ListenerAdapter adapter : listeners) {
                    adapter.invoke(event);
                }
            }
            eventType = eventType.getSuperclass();
        }
    }

    private Class<?> resolveEventType(Method method) {
        Type[] paramTypes = method.getGenericParameterTypes();
        if (paramTypes.length != 1) return null;
        return (Class<?>) paramTypes[0];
    }

    private static class ListenerAdapter {
        private final Object target;
        private final Method method;

        ListenerAdapter(Object target, Method method) {
            this.target = target;
            this.method = method;
            method.setAccessible(true);
        }

        void invoke(Object event) {
            try {
                method.invoke(target, event);
            } catch (Exception e) {
                throw new RuntimeException("事件调用失败: " + method.getName(), e);
            }
        }
    }
}
