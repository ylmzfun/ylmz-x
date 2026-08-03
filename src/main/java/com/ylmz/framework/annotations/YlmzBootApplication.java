package com.ylmz.framework.annotations;

import java.lang.annotation.*;

/**
 * 组合注解 —— 标识启动类，聚合 @Configuration + @ComponentScan
 */
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@Documented
@Inherited
public @interface YlmzBootApplication {
}
