package com.ylmz.demo.service;

import com.ylmz.framework.annotations.Service;

@Service
public class GreetingService {

    public String greet(String appName) {
        return "Hello from " + appName;
    }
}
