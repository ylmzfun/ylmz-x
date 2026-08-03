package com.ylmz.framework.core;

import com.ylmz.framework.annotations.*;
import com.ylmz.framework.aop.AopProxyFactory;
import com.ylmz.framework.aop.AspectDefinition;
import com.ylmz.framework.aop.MethodInterceptor;
import com.ylmz.framework.condition.Condition;
import com.ylmz.framework.condition.ConditionContext;
import com.ylmz.framework.config.Environment;
import com.ylmz.framework.config.PropertySource;
import com.ylmz.framework.config.YamlPropertySourceLoader;
import com.ylmz.framework.event.ApplicationEventPublisher;
import com.ylmz.framework.server.EmbeddedServletContext;
import com.ylmz.framework.server.HttpServer;
import com.ylmz.framework.server.JettyServer;
import com.ylmz.framework.web.DispatcherServlet;
import com.ylmz.framework.web.Filter;
import com.ylmz.framework.web.HandlerAdapter;
import com.ylmz.framework.web.HandlerMapping;

import java.io.InputStream;
import java.lang.reflect.*;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * DefaultApplicationContext —— IoC 容器核心实现（单例模式 + 门面模式）
 *
 * 职责：
 *   1. 类路径扫描 → 注册 BeanDefinition
 *   2. 依赖注入（构造器 + 字段）
 *   3. Bean 后置处理（生命周期模板方法）
 *   4. AOP 代理织入
 *   5. 事件监听注册
 *   6. 内嵌服务器启停
 */
public class DefaultApplicationContext implements ApplicationContext {

    // ---- 单例容器 ----
    private final Map<String, BeanDefinition> beanDefinitions = new LinkedHashMap<>();
    private final Map<String, Object> singletonObjects = new ConcurrentHashMap<>();
    private final List<BeanPostProcessor> beanPostProcessors = new CopyOnWriteArrayList<>();
    private final List<Filter> filters = new CopyOnWriteArrayList<>();

    // ---- 子系统 ----
    private final ComponentScanner scanner = new ComponentScanner();
    private final HandlerMapping handlerMapping = new HandlerMapping();
    private final HandlerAdapter handlerAdapter = new HandlerAdapter();
    private final AopProxyFactory aopProxyFactory = new AopProxyFactory();
    private final ApplicationEventPublisher eventPublisher = new ApplicationEventPublisher();
    private final Environment environment;

    // ---- 元数据 ----
    private final String applicationName;
    private final Class<?> mainClass;
    private final String basePackage;
    private HttpServer httpServer;
    private int serverPort = 8080;
    private boolean running;

    // ---- 构造器（包级可见，由 YlmzApplication 创建） ----
    DefaultApplicationContext(Class<?> mainClass, String basePackage, String... profiles) {
        this.mainClass = mainClass;
        this.basePackage = basePackage;
        this.applicationName = mainClass.getSimpleName();
        this.environment = new Environment(profiles);
        loadProperties();
    }

    // ===================== 启动生命周期 =====================

    void run() {
        System.out.println("[ylmz] 启动 " + applicationName + " ...");

        // 1. 扫描并注册 BeanDefinition
        List<BeanDefinition> scanned = scanner.scan(basePackage);
        for (BeanDefinition bd : scanned) {
            if (passesCondition(bd.getBeanClass())) {
                beanDefinitions.put(bd.getBeanName(), bd);
            }
        }

        // 2. 注册内置 BeanPostProcessor（自动发现 AOP 切面）
        registerInternalPostProcessors();

        // 3. 实例化所有单例 Bean（依赖注入 + 生命周期）
        for (String name : beanDefinitions.keySet()) {
            getBean(name);
        }

        // 4. 注册事件监听器
        registerEventListeners();

        // 5. 初始化 Web 层（注册 Controller → DispatcherServlet）
        initWebLayer();

        // 6. 启动内嵌服务器
        startServer();

        running = true;
        System.out.println("[ylmz] " + applicationName + " 启动完成 ✓");
    }

    // ===================== BeanFactory 实现 =====================

    @Override
    public Object getBean(String name) {
        BeanDefinition bd = beanDefinitions.get(name);
        if (bd == null) throw new RuntimeException("未找到 Bean: " + name);

        if (bd.isSingleton()) {
            return singletonObjects.computeIfAbsent(name, k -> createBean(bd));
        }
        return createBean(bd);
    }

    @Override
    @SuppressWarnings("unchecked")
    public <T> T getBean(Class<T> requiredType) {
        List<String> candidates = new ArrayList<>();
        for (Map.Entry<String, BeanDefinition> entry : beanDefinitions.entrySet()) {
            if (requiredType.isAssignableFrom(entry.getValue().getBeanClass())) {
                candidates.add(entry.getKey());
            }
        }
        if (candidates.isEmpty()) throw new RuntimeException("未找到类型为 " + requiredType.getName() + " 的 Bean");
        if (candidates.size() > 1) {
            // 优先选择主 Bean（未被 @Conditional 过滤的）
            return (T) getBean(candidates.get(0));
        }
        return (T) getBean(candidates.get(0));
    }

    @Override
    @SuppressWarnings("unchecked")
    public <T> T getBean(String name, Class<T> requiredType) {
        Object bean = getBean(name);
        if (!requiredType.isInstance(bean)) {
            throw new RuntimeException("Bean '" + name + "' 类型不匹配: 期望 " + requiredType.getName()
                + ", 实际 " + bean.getClass().getName());
        }
        return (T) bean;
    }

    @Override
    public boolean containsBean(String name) {
        return beanDefinitions.containsKey(name);
    }

    @Override
    public Class<?> getType(String name) {
        BeanDefinition bd = beanDefinitions.get(name);
        return bd != null ? bd.getBeanClass() : null;
    }

    @Override
    public boolean isSingleton(String name) {
        BeanDefinition bd = beanDefinitions.get(name);
        return bd != null && bd.isSingleton();
    }

    // ===================== ApplicationContext 实现 =====================

    @Override
    public String getApplicationName() { return applicationName; }

    @Override
    public Class<?> getMainApplicationClass() { return mainClass; }

    @Override
    public String[] getActiveProfiles() { return environment.getActiveProfiles(); }

    @Override
    public String getProperty(String key) { return environment.getProperty(key); }

    @Override
    public String getProperty(String key, String defaultValue) {
        return environment.getProperty(key, defaultValue);
    }

    @Override
    public void publishEvent(Object event) {
        eventPublisher.publishEvent(event);
    }

    @Override
    public void close() {
        if (!running) return;
        running = false;
        if (httpServer != null) httpServer.stop();

        // 调用 @PreDestroy
        for (Map.Entry<String, Object> entry : singletonObjects.entrySet()) {
            BeanDefinition bd = beanDefinitions.get(entry.getKey());
            if (bd == null) continue;
            Method preDestroy = ComponentScanner.findLifecycleMethod(bd.getBeanClass(), PreDestroy.class);
            if (preDestroy != null) {
                try { preDestroy.invoke(entry.getValue()); } catch (Exception ignored) {}
            }
        }
        singletonObjects.clear();
        System.out.println("[ylmz] " + applicationName + " 已关闭");
    }

    // ---- 对外配置 ----

    public void setServerPort(int port) { this.serverPort = port; }

    public DefaultApplicationContext addFilter(Filter filter) {
        filters.add(filter);
        return this;
    }

    // ===================== 内部实现 =====================

    @SuppressWarnings("unchecked")
    private Object createBean(BeanDefinition bd) {
        Object instance = instantiate(bd);
        instance = applyBeanPostProcessorsBefore(instance, bd.getBeanName());
        populateBean(instance, bd);
        invokeInitMethod(instance, bd);
        instance = applyBeanPostProcessorsAfter(instance, bd.getBeanName());
        instance = aopProxyFactory.createProxy(instance, bd.getBeanName(), bd.getBeanClass());
        return instance;
    }

    private Object instantiate(BeanDefinition bd) {
        Class<?> clazz = bd.getBeanClass();
        Constructor<?> autowiredCtor = ComponentScanner.findAutowiredConstructor(clazz);

        try {
            if (autowiredCtor != null) {
                return instantiateWithConstructor(autowiredCtor);
            }
            // 默认无参构造器
            Constructor<?> noArg = clazz.getDeclaredConstructor();
            noArg.setAccessible(true);
            return noArg.newInstance();
        } catch (Exception e) {
            throw new RuntimeException("实例化失败: " + clazz.getName(), e);
        }
    }

    private Object instantiateWithConstructor(Constructor<?> ctor) throws Exception {
        Class<?>[] paramTypes = ctor.getParameterTypes();
        Object[] args = new Object[paramTypes.length];
        for (int i = 0; i < paramTypes.length; i++) {
            args[i] = getBean(paramTypes[i]);
        }
        return ctor.newInstance(args);
    }

    private void populateBean(Object instance, BeanDefinition bd) {
        Class<?> clazz = bd.getBeanClass();

        // @Value 字段注入
        for (Field field : ComponentScanner.getValueFields(clazz)) {
            Value val = field.getAnnotation(Value.class);
            String resolved = environment.resolvePlaceholders(val.value());
            try {
                field.set(instance, convertValue(resolved, field.getType()));
            } catch (Exception e) {
                throw new RuntimeException("注入 @Value 失败: " + field.getName(), e);
            }
        }

        // @Autowired 字段注入
        for (Field field : ComponentScanner.getAutowiredFields(clazz)) {
            try {
                field.set(instance, getBean(field.getType()));
            } catch (Exception e) {
                throw new RuntimeException("注入 @Autowired 失败: " + field.getName(), e);
            }
        }
    }

    private void invokeInitMethod(Object instance, BeanDefinition bd) {
        // @PostConstruct
        Method postConstruct = ComponentScanner.findLifecycleMethod(bd.getBeanClass(), PostConstruct.class);
        if (postConstruct != null) {
            try { postConstruct.invoke(instance); } catch (Exception e) {
                throw new RuntimeException("@PostConstruct 失败: " + bd.getBeanName(), e);
            }
        }
        // InitializingBean 接口
        if (instance instanceof InitializingBean) {
            ((InitializingBean) instance).afterPropertiesSet();
        }
    }

    private Object applyBeanPostProcessorsBefore(Object bean, String name) {
        for (BeanPostProcessor processor : beanPostProcessors) {
            bean = processor.postProcessBeforeInitialization(bean, name);
        }
        return bean;
    }

    private Object applyBeanPostProcessorsAfter(Object bean, String name) {
        for (BeanPostProcessor processor : beanPostProcessors) {
            bean = processor.postProcessAfterInitialization(bean, name);
        }
        return bean;
    }

    // ---- 条件判断 ----

    private boolean passesCondition(Class<?> clazz) {
        Conditional conditional = clazz.getAnnotation(Conditional.class);
        if (conditional != null) {
            try {
                Condition cond = (Condition) conditional.value().getDeclaredConstructor().newInstance();
                if (!cond.matches(new ConditionContext(environment))) return false;
            } catch (Exception e) {
                return false;
            }
        }
        Profile profile = clazz.getAnnotation(Profile.class);
        if (profile != null && !environment.acceptsProfile(profile.value())) return false;
        return true;
    }

    // ---- 属性加载 ----

    private void loadProperties() {
        try {
            InputStream is = Thread.currentThread().getContextClassLoader()
                .getResourceAsStream("application.yml");
            if (is != null) {
                String yaml = new String(is.readAllBytes());
                environment.addSource(YamlPropertySourceLoader.load("application.yml", yaml));
            }
        } catch (Exception ignored) {}
        try {
            InputStream is = Thread.currentThread().getContextClassLoader()
                .getResourceAsStream("application.properties");
            if (is != null) {
                Properties props = new Properties();
                props.load(is);
                environment.addSource(YamlPropertySourceLoader.loadProperties("application.properties", props));
            }
        } catch (Exception ignored) {}
    }

    // ---- 内部后置处理器 ----

    private void registerInternalPostProcessors() {
        // 扫描 @Aspect 切面
        for (Map.Entry<String, BeanDefinition> entry : beanDefinitions.entrySet()) {
            Class<?> clazz = entry.getValue().getBeanClass();
            if (clazz.isAnnotationPresent(Aspect.class)) {
                Object aspectBean = getBean(entry.getKey());
                registerAspect(aspectBean, clazz);
            }
        }
    }

    private void registerAspect(Object aspectBean, Class<?> aspectClass) {
        for (Method method : aspectClass.getDeclaredMethods()) {
            Around around = method.getAnnotation(Around.class);
            if (around != null) {
                aopProxyFactory.addAspect(new AspectDefinition(
                    aspectBean, around.value(),
                    inv -> method.invoke(aspectBean, inv),
                    AspectDefinition.AdviceType.AROUND));
            }
            Before before = method.getAnnotation(Before.class);
            if (before != null) {
                aopProxyFactory.addAspect(new AspectDefinition(
                    aspectBean, before.value(),
                    inv -> { method.invoke(aspectBean, inv); return null; },
                    AspectDefinition.AdviceType.BEFORE));
            }
            After after = method.getAnnotation(After.class);
            if (after != null) {
                aopProxyFactory.addAspect(new AspectDefinition(
                    aspectBean, after.value(),
                    inv -> { method.invoke(aspectBean, inv); return null; },
                    AspectDefinition.AdviceType.AFTER));
            }
        }
    }

    // ---- 事件监听 ----

    private void registerEventListeners() {
        for (Map.Entry<String, Object> entry : singletonObjects.entrySet()) {
            for (Method method : entry.getValue().getClass().getDeclaredMethods()) {
                if (method.isAnnotationPresent(EventListener.class) && method.getParameterCount() == 1) {
                    eventPublisher.registerListener(entry.getValue(), method);
                }
            }
        }
    }

    // ---- Web 层初始化 ----

    private void initWebLayer() {
        // 自动发现 Filter 实现
        for (Object bean : singletonObjects.values()) {
            if (bean instanceof Filter && !filters.contains(bean)) {
                filters.add((Filter) bean);
            }
        }

        DispatcherServlet dispatcherServlet = new DispatcherServlet(
            handlerMapping, handlerAdapter, new ArrayList<>(filters));

        for (Object bean : singletonObjects.values()) {
            if (bean.getClass().isAnnotationPresent(Controller.class)) {
                dispatcherServlet.registerController(bean);
            }
        }
        EmbeddedServletContext.setServlet(dispatcherServlet);
    }

    // ---- 服务器 ----

    private void startServer() {
        httpServer = new JettyServer();
        String portProp = environment.getProperty("server.port");
        if (portProp != null) serverPort = Integer.parseInt(portProp);
        httpServer.start(serverPort);
    }

    // ---- 类型转换 ----

    @SuppressWarnings("unchecked")
    private <T> T convertValue(String value, Class<T> type) {
        if (type == String.class) return (T) value;
        if (type == int.class || type == Integer.class) return (T) Integer.valueOf(value);
        if (type == long.class || type == Long.class) return (T) Long.valueOf(value);
        if (type == boolean.class || type == Boolean.class) return (T) Boolean.valueOf(value);
        if (type == double.class || type == Double.class) return (T) Double.valueOf(value);
        return (T) value;
    }
}
