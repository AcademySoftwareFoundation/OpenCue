package com.imageworks.spcue.dispatcher;

public interface QueueHealthCheck {
    boolean isHealthy();

    void shutdownUnhealthy();
}
