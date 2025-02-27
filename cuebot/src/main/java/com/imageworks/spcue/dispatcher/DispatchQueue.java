
/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */

package com.imageworks.spcue.dispatcher;

import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;

import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.LogManager;
import com.imageworks.spcue.dispatcher.commands.KeyRunnable;

public class DispatchQueue implements QueueHealthCheck {

    private int healthThreshold;
    private int minUnhealthyPeriodMin;
    private int queueCapacity;
    private int corePoolSize;
    private int maxPoolSize;

    private static final Logger logger = LogManager.getLogger("HEALTH");
    private String name = "Default";
    private HealthyThreadPool healthyDispatchPool;

    public DispatchQueue(String name, int healthThreshold, int minUnhealthyPeriodMin,
            int queueCapacity, int corePoolSize, int maxPoolSize) {
        this.name = name;
        this.healthThreshold = healthThreshold;
        this.minUnhealthyPeriodMin = minUnhealthyPeriodMin;
        this.queueCapacity = queueCapacity;
        this.corePoolSize = corePoolSize;
        this.maxPoolSize = maxPoolSize;
        initThreadPool();
    }

    public void initThreadPool() {
        healthyDispatchPool = new HealthyThreadPool(name, healthThreshold, minUnhealthyPeriodMin,
                queueCapacity, corePoolSize, maxPoolSize);
    }

    public void shutdownUnhealthy() {
        try {
            if (!healthyDispatchPool.shutdownUnhealthy()) {
                logger.warn("DispatchQueue_" + name
                        + ": Unhealthy queue terminated, starting a new one");
                initThreadPool();
            }
        } catch (InterruptedException e) {
            // TODO: evaluate crashing the whole springbook context here
            // to force a container restart cycle
            logger.error("DispatchQueue_" + name + ":Failed to restart DispatchThreadPool", e);
        }
    }

    public boolean isHealthy() {
        return healthyDispatchPool.healthCheck();
    }

    public void execute(KeyRunnable r) {
        healthyDispatchPool.execute(r);
    }

    public long getRejectedTaskCount() {
        return healthyDispatchPool.getRejectedTaskCount();
    }

    public void shutdown() {
        healthyDispatchPool.shutdown();
    }

    public int getSize() {
        return healthyDispatchPool.getQueue().size();
    }

    public int getRemainingCapacity() {
        return healthyDispatchPool.getQueue().remainingCapacity();
    }

    public int getActiveCount() {
        return healthyDispatchPool.getActiveCount();
    }

    public long getCompletedTaskCount() {
        return healthyDispatchPool.getCompletedTaskCount();
    }

}
