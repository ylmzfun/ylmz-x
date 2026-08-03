package com.ylmz.demo.controller;

import com.ylmz.framework.annotations.*;
import com.ylmz.demo.service.HelloService;

@Controller
@RequestMapping("/api")
public class HelloController {

    private final HelloService helloService;

    @Autowired
    public HelloController(HelloService helloService) {
        this.helloService = helloService;
    }

    @RequestMapping(value = "/hello", method = RequestMethod.GET)
    public String hello(@Value("${app.name:ylmz-framework}") String appName) {
        return helloService.hello("World");
    }

    @RequestMapping(value = "/hello/{name}", method = RequestMethod.GET)
    public String helloName(String name) {
        return helloService.hello(name);
    }

    @RequestMapping(value = "/info", method = RequestMethod.GET)
    public java.util.Map<String, Object> info() {
        java.util.Map<String, Object> result = new java.util.LinkedHashMap<>();
        result.put("framework", "ylmz-java");
        result.put("version", "1.0.0");
        result.put("designPatterns", java.util.List.of(
            "IoC / DI", "Singleton", "Factory", "Builder",
            "Strategy", "TemplateMethod", "Observer",
            "Proxy", "Adapter", "ChainOfResponsibility",
            "Facade", "FrontController"
        ));
        return result;
    }
}
