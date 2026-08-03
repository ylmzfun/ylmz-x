# ylmz-java

精简干练的 Java 框架内核，涵盖 Spring Boot 所有核心设计模式。

## 设计模式

| 模式 | 应用位置 |
|------|---------|
| **Singleton** | `DefaultApplicationContext` 默认 Bean 作用域 |
| **Factory** | `BeanFactory` + `@Bean` 工厂方法 |
| **Builder** | `YlmzApplication.builder().port().profiles().run()` |
| **Strategy** | `HttpServer` 多实现、`Condition` 条件判断、`HandlerMapping` 路由 |
| **Template Method** | `BeanPostProcessor` + `InitializingBean` 生命周期 |
| **Observer** | `ApplicationEventPublisher` + `@EventListener` |
| **Proxy** | `AopProxyFactory` JDK / CGLIB 动态代理 |
| **Adapter** | `JettyServer` 适配 Jetty、`HandlerAdapter` 参数适配 |
| **Chain of Responsibility** | `FilterChain` 过滤器链 |
| **Facade** | `ApplicationContext` + `YlmzApplication` 统一入口 |
| **Front Controller** | `DispatcherServlet` 请求分发 |
| **Prototype** | `BeanDefinition.copy()` 原型复制 |

## 项目结构

```
ylmz-java/
└── src/main/java/com/ylmz/
    ├── framework/           # 框架内核
    │   ├── YlmzApplication.java
    │   ├── annotations/     # 注解体系 (18 个)
    │   ├── core/            # IoC 容器
    │   ├── web/             # MVC 层
    │   ├── server/          # 嵌入式服务器
    │   ├── aop/             # AOP 代理
    │   ├── event/           # 事件系统
    │   ├── config/          # 配置 / 属性
    │   └── condition/       # 条件装配
    └── demo/                # Demo 应用
```

## 快速启动

```bash
mvn clean package
java -jar target/ylmz-java-1.0.0.jar
```

## Demo API

```
GET  http://localhost:8080/api/hello
GET  http://localhost:8080/api/hello/{name}
GET  http://localhost:8080/api/info
```

## 依赖

- JDK 17+
- Jetty 11（嵌入式）
- Gson
- CGLIB
- SnakeYAML
