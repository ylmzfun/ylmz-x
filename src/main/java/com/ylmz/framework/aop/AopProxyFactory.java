package com.ylmz.framework.aop;

import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.util.*;

/**
 * AOP 代理工厂 —— 代理模式
 * 优先使用 JDK 动态代理，如果目标类没有接口则用 CGLIB
 */
public class AopProxyFactory {
    private final List<AspectDefinition> aspects = new ArrayList<>();

    public void addAspect(AspectDefinition aspect) {
        aspects.add(aspect);
    }

    /**
     * 为目标 bean 创建代理（如果匹配切面）
     */
    public Object createProxy(Object target, String beanName, Class<?> targetClass) {
        Map<Method, List<AspectDefinition>> methodAspects = new LinkedHashMap<>();

        for (Method method : targetClass.getMethods()) {
            if (method.getDeclaringClass() == Object.class) continue;
            for (AspectDefinition aspect : aspects) {
                if (aspect.matches(targetClass, method)) {
                    methodAspects.computeIfAbsent(method, k -> new ArrayList<>()).add(aspect);
                }
            }
        }

        if (methodAspects.isEmpty()) return target;

        // 尝试 JDK 动态代理
        Class<?>[] interfaces = targetClass.getInterfaces();
        if (interfaces.length > 0) {
            return Proxy.newProxyInstance(
                targetClass.getClassLoader(),
                interfaces,
                new AopInvocationHandler(target, methodAspects)
            );
        }

        // 回退：创建 CGLIB 代理
        return createCglibProxy(target, targetClass, methodAspects);
    }

    private Object createCglibProxy(Object target, Class<?> targetClass,
                                     Map<Method, List<AspectDefinition>> methodAspects) {
        net.sf.cglib.proxy.Enhancer enhancer = new net.sf.cglib.proxy.Enhancer();
        enhancer.setSuperclass(targetClass);
        enhancer.setCallback(new net.sf.cglib.proxy.MethodInterceptor() {
            @Override
            public Object intercept(Object obj, Method method, Object[] args,
                                    net.sf.cglib.proxy.MethodProxy proxy) throws Throwable {
                List<AspectDefinition> matched = methodAspects.get(method);
                if (matched == null || matched.isEmpty()) {
                    return method.invoke(target, args);
                }
                return applyAdvice(target, method, args, matched);
            }
        });
        return enhancer.create();
    }

    private static class AopInvocationHandler implements InvocationHandler {
        private final Object target;
        private final Map<Method, List<AspectDefinition>> methodAspects;

        AopInvocationHandler(Object target, Map<Method, List<AspectDefinition>> methodAspects) {
            this.target = target;
            this.methodAspects = methodAspects;
        }

        @Override
        public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
            List<AspectDefinition> matched = methodAspects.get(method);
            if (matched == null || matched.isEmpty()) {
                return method.invoke(target, args);
            }
            return applyAdvice(target, method, args, matched);
        }
    }

    private static Object applyAdvice(Object target, Method method, Object[] args,
                                       List<AspectDefinition> aspects) throws Throwable {
        MethodInvocation invocation = new MethodInvocation(target, method, args);

        // 执行 BEFORE 通知
        for (AspectDefinition aspect : aspects) {
            if (aspect.getType() == AspectDefinition.AdviceType.BEFORE) {
                aspect.getInterceptor().intercept(invocation);
            }
        }

        Object result;
        try {
            // 执行 AROUND 通知链
            result = invokeAround(invocation, aspects, 0);
        } catch (Throwable t) {
            throw t;
        }

        // 执行 AFTER 通知
        for (AspectDefinition aspect : aspects) {
            if (aspect.getType() == AspectDefinition.AdviceType.AFTER) {
                aspect.getInterceptor().intercept(invocation);
            }
        }

        return result;
    }

    private static Object invokeAround(MethodInvocation invocation,
                                        List<AspectDefinition> aspects,
                                        int index) throws Throwable {
        if (index >= aspects.size()) {
            return invocation.proceed();
        }
        AspectDefinition aspect = aspects.get(index);
        if (aspect.getType() == AspectDefinition.AdviceType.AROUND) {
            return aspect.getInterceptor().intercept(() -> invokeAround(invocation, aspects, index + 1));
        }
        return invokeAround(invocation, aspects, index + 1);
    }
}
