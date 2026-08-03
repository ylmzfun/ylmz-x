package com.ylmz.framework.core;

import com.ylmz.framework.annotations.*;
import java.io.File;
import java.lang.annotation.Annotation;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.net.URL;
import java.util.*;

/**
 * 组件扫描器 —— 策略模式：扫描 classpath 注册 BeanDefinition
 */
public class ComponentScanner {
    private static final Set<Class<? extends Annotation>> STEREOTYPE_ANNOTATIONS =
        Set.of(Component.class, Service.class, Controller.class, Repository.class, Configuration.class);

    public List<BeanDefinition> scan(String basePackage) {
        List<BeanDefinition> definitions = new ArrayList<>();
        try {
            String path = basePackage.replace('.', '/');
            Enumeration<URL> resources = Thread.currentThread().getContextClassLoader().getResources(path);
            while (resources.hasMoreElements()) {
                URL resource = resources.nextElement();
                File dir = new File(resource.toURI());
                scanDir(dir, basePackage, definitions);
            }
        } catch (Exception e) {
            throw new RuntimeException("扫描包失败: " + basePackage, e);
        }
        return definitions;
    }

    private void scanDir(File dir, String basePackage, List<BeanDefinition> definitions) {
        if (!dir.exists()) return;
        for (File file : dir.listFiles()) {
            String name = file.getName();
            if (file.isDirectory()) {
                scanDir(file, basePackage + "." + name, definitions);
            } else if (name.endsWith(".class")) {
                String className = basePackage + "." + name.substring(0, name.length() - 6);
                try {
                    Class<?> clazz = Class.forName(className);
                    resolveBeanDefinition(clazz, definitions);
                } catch (ClassNotFoundException | NoClassDefFoundError ignored) {
                }
            }
        }
    }

    private void resolveBeanDefinition(Class<?> clazz, List<BeanDefinition> definitions) {
        if (clazz.isAnnotation() || clazz.isInterface() || clazz.isEnum()) return;

        for (Class<? extends Annotation> annotationType : STEREOTYPE_ANNOTATIONS) {
            Annotation annotation = clazz.getAnnotation(annotationType);
            if (annotation != null) {
                String beanName = resolveBeanName(clazz, annotation);
                BeanDefinition bd = new BeanDefinition(beanName, clazz);
                definitions.add(bd);

                // 处理 @Configuration 的 @Bean 方法
                if (annotationType == Configuration.class) {
                    resolveBeanMethods(clazz, definitions);
                }
                break;
            }
        }
    }

    private String resolveBeanName(Class<?> clazz, Annotation annotation) {
        try {
            Method valueMethod = annotation.annotationType().getMethod("value");
            String value = (String) valueMethod.invoke(annotation);
            if (value != null && !value.isEmpty()) return value;
        } catch (Exception ignored) {}
        String simpleName = clazz.getSimpleName();
        return Character.toLowerCase(simpleName.charAt(0)) + simpleName.substring(1);
    }

    private void resolveBeanMethods(Class<?> configClass, List<BeanDefinition> definitions) {
        for (Method method : configClass.getDeclaredMethods()) {
            Bean bean = method.getAnnotation(Bean.class);
            if (bean == null) continue;

            String beanName = bean.value().isEmpty() ? method.getName() : bean.value();
            BeanDefinition bd = new BeanDefinition(beanName, method.getReturnType());
            bd.setSingleton(true);
            definitions.add(bd);
        }
    }

    /**
     * 判断类型是否是框架管理的组件
     */
    public static boolean isComponent(Class<?> clazz) {
        for (Class<? extends Annotation> ann : STEREOTYPE_ANNOTATIONS) {
            if (clazz.isAnnotationPresent(ann)) return true;
        }
        return false;
    }

    /**
     * 判断方法是否标注了 @Bean
     */
    public static boolean isBeanMethod(Method method) {
        return method.isAnnotationPresent(Bean.class);
    }

    /**
     * 反射：查找被 @Autowired 标记的构造器
     */
    public static java.lang.reflect.Constructor<?> findAutowiredConstructor(Class<?> clazz) {
        for (java.lang.reflect.Constructor<?> ctor : clazz.getDeclaredConstructors()) {
            if (ctor.isAnnotationPresent(Autowired.class)) {
                ctor.setAccessible(true);
                return ctor;
            }
        }
        return null;
    }

    /**
     * 获取 @Autowired 字段
     */
    public static List<Field> getAutowiredFields(Class<?> clazz) {
        List<Field> fields = new ArrayList<>();
        for (Field field : clazz.getDeclaredFields()) {
            if (field.isAnnotationPresent(Autowired.class)) {
                field.setAccessible(true);
                fields.add(field);
            }
        }
        return fields;
    }

    /**
     * 获取 @Value 字段
     */
    public static List<Field> getValueFields(Class<?> clazz) {
        List<Field> fields = new ArrayList<>();
        for (Field field : clazz.getDeclaredFields()) {
            Value v = field.getAnnotation(Value.class);
            if (v != null) {
                field.setAccessible(true);
                fields.add(field);
            }
        }
        return fields;
    }

    /**
     * 获取 @PostConstruct / @PreDestroy 方法
     */
    public static Method findLifecycleMethod(Class<?> clazz, Class<? extends Annotation> annType) {
        for (Method method : clazz.getDeclaredMethods()) {
            if (method.isAnnotationPresent(annType) && method.getParameterCount() == 0) {
                method.setAccessible(true);
                return method;
            }
        }
        return null;
    }
}
