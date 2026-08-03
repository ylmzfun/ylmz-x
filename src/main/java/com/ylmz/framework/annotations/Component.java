package com.ylmz.framework.annotations;

import java.lang.annotation.*;

/**
 * 组件标记 —— IoC 容器托管
 */
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface Component {
    String value() default "";
}
