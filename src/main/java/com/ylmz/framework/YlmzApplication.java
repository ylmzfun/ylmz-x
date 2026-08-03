package com.ylmz.framework;

import com.ylmz.framework.core.DefaultApplicationContext;
import com.ylmz.framework.web.Filter;

/**
 * YlmzApplication —— 框架启动器（Builder 模式 + 门面模式）
 *
 * 用法：
 * <pre>
 *   YlmzApplication.run(DemoApplication.class);
 *   // 或
 *   YlmzApplication.builder(DemoApplication.class)
 *       .port(9090)
 *       .profiles("dev")
 *       .addFilter(new LoggingFilter())
 *       .run();
 * </pre>
 */
public final class YlmzApplication {
    private final Class<?> mainClass;
    private final String basePackage;
    private int port = 8080;
    private String[] profiles = new String[0];
    private final java.util.List<Filter> filters = new java.util.ArrayList<>();
    private DefaultApplicationContext context;

    private YlmzApplication(Class<?> mainClass) {
        this.mainClass = mainClass;
        // 默认扫描主类所在包
        this.basePackage = mainClass.getPackageName();
    }

    // ---- Builder 方法 ----

    public YlmzApplication port(int port) {
        this.port = port;
        return this;
    }

    public YlmzApplication profiles(String... profiles) {
        this.profiles = profiles;
        return this;
    }

    public YlmzApplication addFilter(Filter filter) {
        this.filters.add(filter);
        return this;
    }

    // ---- 启动 ----

    public DefaultApplicationContext run() {
        context = new DefaultApplicationContext(mainClass, basePackage, profiles);
        context.setServerPort(port);
        for (Filter f : filters) {
            context.addFilter(f);
        }
        context.run();
        return context;
    }

    public DefaultApplicationContext getContext() {
        return context;
    }

    // ---- 静态快捷方法 ----

    public static YlmzApplication builder(Class<?> mainClass) {
        return new YlmzApplication(mainClass);
    }

    public static DefaultApplicationContext run(Class<?> mainClass, String... args) {
        return builder(mainClass).run();
    }
}
