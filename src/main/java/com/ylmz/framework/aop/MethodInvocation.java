package com.ylmz.framework.aop;

import java.lang.reflect.Method;

/**
 * 方法调用上下文
 */
public class MethodInvocation {
    private final Object target;
    private final Method method;
    private final Object[] args;

    public MethodInvocation(Object target, Method method, Object[] args) {
        this.target = target;
        this.method = method;
        this.args = args;
    }

    public Object getTarget() { return target; }
    public Method getMethod() { return method; }
    public Object[] getArgs() { return args; }

    public Object proceed() throws Throwable {
        return method.invoke(target, args);
    }
}
