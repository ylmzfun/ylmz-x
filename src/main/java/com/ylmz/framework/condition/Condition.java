package com.ylmz.framework.condition;

/**
 * 条件接口 —— 策略模式，决定 Bean 是否注册
 */
@FunctionalInterface
public interface Condition {
    boolean matches(ConditionContext context);
}
