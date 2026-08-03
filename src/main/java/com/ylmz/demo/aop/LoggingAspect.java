package com.ylmz.demo.aop;

import com.ylmz.framework.annotations.*;
import com.ylmz.framework.aop.MethodInvocation;

/**
 * AOP 切面 —— 为 HelloService.* 方法添加日志
 */
@Aspect
@Component
public class LoggingAspect {

    @Around("execution(* com.ylmz.demo.service.HelloService.*(..))")
    public Object logAround(MethodInvocation invocation) throws Throwable {
        System.out.println("[aop] >>> 调用: " + invocation.getMethod().getName());
        long start = System.currentTimeMillis();
        Object result = invocation.proceed();
        long elapsed = System.currentTimeMillis() - start;
        System.out.println("[aop] <<< 返回: " + invocation.getMethod().getName()
            + " (耗时 " + elapsed + "ms)");
        return result;
    }
}
