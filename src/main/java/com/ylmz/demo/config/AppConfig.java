package com.ylmz.demo.config;

import com.ylmz.framework.annotations.*;
import com.ylmz.framework.core.InitializingBean;

@Configuration
public class AppConfig implements InitializingBean {

    @Value("${app.version:1.0.0}")
    private String appVersion;

    @Override
    public void afterPropertiesSet() {
        System.out.println("[demo] AppConfig 初始化完成: version=" + appVersion);
    }

    @Bean
    public String appInfo() {
        return "ylmz-java v" + appVersion;
    }
}
