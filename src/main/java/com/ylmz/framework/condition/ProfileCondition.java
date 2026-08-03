package com.ylmz.framework.condition;

import com.ylmz.framework.config.Environment;

/**
 * @Profile 条件实现
 */
public class ProfileCondition implements Condition {
    @Override
    public boolean matches(ConditionContext context) {
        return true;
    }
}
