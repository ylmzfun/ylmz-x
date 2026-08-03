package com.ylmz.framework.annotations;

import java.lang.annotation.*;

/**
 * 工厂方法 —— 声明 Bean
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface Bean {
    String value() default "";
}
