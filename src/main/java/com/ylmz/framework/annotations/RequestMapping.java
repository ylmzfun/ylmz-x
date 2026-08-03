package com.ylmz.framework.annotations;

import java.lang.annotation.*;

/**
 * HTTP 路由映射
 */
@Target({ElementType.TYPE, ElementType.METHOD})
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface RequestMapping {
    String value() default "";
    RequestMethod[] method() default {};
}
