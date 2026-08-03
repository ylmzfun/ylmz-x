package com.ylmz.framework.annotations;

import java.lang.annotation.*;

/**
 * 配置类
 */
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@Documented
@Component
public @interface Configuration {
    String value() default "";
}
