package com.ylmz.demo.event;

import com.ylmz.framework.annotations.*;
import com.ylmz.framework.event.ApplicationEvent;

/**
 * 自定义事件
 */
class ServerStartedEvent extends ApplicationEvent {
    public ServerStartedEvent(Object source) {
        super(source);
    }
}

@Component
public class CustomEventListener {

    @EventListener
    public void onServerStarted(ServerStartedEvent event) {
        System.out.println("[demo] 收到事件: ServerStarted at " + event.getTimestamp());
    }
}
