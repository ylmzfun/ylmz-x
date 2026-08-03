package com.ylmz.framework.annotations;

import java.lang.annotation.*;

/**
 * 构造器/字段注入
 */
@Target({ElementType.CONSTRUCTOR, ElementType.FIELD})
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface Autowired {
}
