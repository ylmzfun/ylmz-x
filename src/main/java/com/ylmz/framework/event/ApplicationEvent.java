package com.ylmz.framework.event;

/**
 * 应用事件基类
 */
public class ApplicationEvent {
    private final Object source;
    private final long timestamp;

    public ApplicationEvent(Object source) {
        this.source = source;
        this.timestamp = System.currentTimeMillis();
    }

    public Object getSource() { return source; }
    public long getTimestamp() { return timestamp; }
}
