
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

import com.google.common.cache.Cache;
import com.google.common.cache.CacheBuilder;
import com.imageworks.spcue.dispatcher.commands.KeyRunnable;

import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.LogManager;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;

public class BookingQueue implements QueueHealthCheck {

    private final int healthThreshold;
    private final int minUnhealthyPeriodMin;
    private final int queueCapacity;
    private final int corePoolSize;
    private final int maxPoolSize;
    // Base value for calculating the job sleep time
    // this is used to slow down the booking queue to avoid racing conditions
    private static final int BASE_SLEEP_TIME_MILLIS = 300;

    private static final Logger logger = LogManager.getLogger("HEALTH");
    private HealthyThreadPool healthyThreadPool;

    public BookingQueue(int healthThreshold, int minUnhealthyPeriodMin, int queueCapacity,
            int corePoolSize, int maxPoolSize) {
        this.healthThreshold = healthThreshold;
        this.minUnhealthyPeriodMin = minUnhealthyPeriodMin;
        this.queueCapacity = queueCapacity;
        this.corePoolSize = corePoolSize;
        this.maxPoolSize = maxPoolSize;
        initThreadPool();
    }

    public void initThreadPool() {
        healthyThreadPool =
                new HealthyThreadPool("BookingQueue", healthThreshold, minUnhealthyPeriodMin,
                        queueCapacity, corePoolSize, maxPoolSize, BASE_SLEEP_TIME_MILLIS);
    }

    public void shutdownUnhealthy() {
        try {
            if (!healthyThreadPool.shutdownUnhealthy()) {
                logger.warn("BookingQueue: Unhealthy queue terminated, starting a new one");
                initThreadPool();
            }
        } catch (InterruptedException e) {
            // TODO: evaluate crashing the whole springbook context here
            // to force a container restart cycle
            logger.error("Failed to restart BookingThreadPool", e);
        }
    }

    public boolean isHealthy() {
        return healthyThreadPool.healthCheck();
    }

    public void execute(KeyRunnable r) {
        healthyThreadPool.execute(r);
    }

    public long getRejectedTaskCount() {
        return healthyThreadPool.getRejectedTaskCount();
    }

    public int getQueueCapacity() {
        return queueCapacity;
    }

    public void shutdown() {
        healthyThreadPool.shutdown();
    }

    public int getSize() {
        return healthyThreadPool.getQueue().size();
    }

    public int getRemainingCapacity() {
        return healthyThreadPool.getQueue().remainingCapacity();
    }

    public int getActiveCount() {
        return healthyThreadPool.getActiveCount();
    }

    public long getCompletedTaskCount() {
        return healthyThreadPool.getCompletedTaskCount();
    }

    public long getCorePoolSize() {
        return corePoolSize;
    }

    public long getMaximumPoolSize() {
        return maxPoolSize;
    }

}
