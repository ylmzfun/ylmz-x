package com.ylmz.framework.condition;

import com.ylmz.framework.config.Environment;

/**
 * 条件上下文
 */
public class ConditionContext {
    private final Environment environment;

    public ConditionContext(Environment environment) {
        this.environment = environment;
    }

    public Environment getEnvironment() { return environment; }
}
