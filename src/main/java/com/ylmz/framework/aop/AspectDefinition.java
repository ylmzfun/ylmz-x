package com.ylmz.framework.aop;

/**
 * 切面定义 —— 包含切入点表达式和通知类型
 */
public class AspectDefinition {
    private final Object aspectBean;
    private final String pointcut;
    private final MethodInterceptor interceptor;
    private final AdviceType type;

    public enum AdviceType { AROUND, BEFORE, AFTER }

    public AspectDefinition(Object aspectBean, String pointcut, MethodInterceptor interceptor, AdviceType type) {
        this.aspectBean = aspectBean;
        this.pointcut = pointcut;
        this.interceptor = interceptor;
        this.type = type;
    }

    public Object getAspectBean() { return aspectBean; }
    public String getPointcut() { return pointcut; }
    public MethodInterceptor getInterceptor() { return interceptor; }
    public AdviceType getType() { return type; }

    /**
     * 匹配方法名（支持 * 通配符）
     */
    public boolean matches(Class<?> targetClass, Method method) {
        String expression = pointcut;
        // 格式: execution(* com.example.Service.*(..)) 的简化版
        if (expression.startsWith("execution(")) {
            expression = expression.substring("execution(".length(), expression.length() - 1);
            expression = expression.replace("* ", "").trim();
        }
        // 支持: com.example.Service.methodName
        String fullMethodName = targetClass.getName() + "." + method.getName();
        return matchPattern(expression, fullMethodName);
    }

    private boolean matchPattern(String pattern, String target) {
        // 简化通配符匹配
        if (pattern.equals(target)) return true;
        if (pattern.endsWith(".*")) {
            String prefix = pattern.substring(0, pattern.length() - 2);
            return target.startsWith(prefix);
        }
        if (pattern.contains("*")) {
            String regex = pattern.replace(".", "\\.").replace("*", ".*");
            return target.matches(regex);
        }
        return false;
    }
}
