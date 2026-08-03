package com.ylmz.demo;

import com.ylmz.framework.YlmzApplication;

public class DemoApplication {
    public static void main(String[] args) {
        YlmzApplication.builder(DemoApplication.class)
            .port(8080)
            .profiles("dev")
            .run();
    }
}
