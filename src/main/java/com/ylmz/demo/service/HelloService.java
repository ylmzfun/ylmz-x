package com.ylmz.demo.service;

import com.ylmz.framework.annotations.*;

@Service
public class HelloService {

    @Value("${app.name:ylmz-framework}")
    private String appName;

    private final GreetingService greetingService;

    @Autowired
    public HelloService(GreetingService greetingService) {
        this.greetingService = greetingService;
    }

    @PostConstruct
    public void init() {
        System.out.println("[demo] HelloService 初始化: appName=" + appName);
    }

    public String hello(String name) {
        return greetingService.greet(appName) + ", " + name + "!";
    }

    @PreDestroy
    public void destroy() {
        System.out.println("[demo] HelloService 销毁");
    }
}
