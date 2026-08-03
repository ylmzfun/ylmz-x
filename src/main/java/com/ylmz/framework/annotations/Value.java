package com.ylmz.framework.annotations;

import java.lang.annotation.*;

/**
 * 属性注入
 */
@Target({ElementType.FIELD, ElementType.PARAMETER})
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface Value {
    String value();
}
