
/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */



package com.imageworks.spcue.dispatcher;

import java.util.concurrent.TimeUnit;

import com.google.common.cache.Cache;
import com.google.common.cache.CacheBuilder;
import com.imageworks.spcue.dispatcher.commands.KeyRunnable;
import org.apache.log4j.Logger;

public class BookingQueue {

    private static final int HEALTH_THRESHOLD = 10;
    private static final int MIN_UNHEALTHY_PERIOD_MIN = 3;
    private static final int QUEUE_SIZE = 2000;
    private static final int THREADS_MINIMUM = 10;
    private static final int THREADS_MAXIMUM = 14;

    private static final Logger logger = Logger.getLogger("BOOKING");
    private HealthyThreadPool healthyThreadPool;

    public BookingQueue() {
        initThreadPool();
    }

    public void initThreadPool() {
        healthyThreadPool = new HealthyThreadPool(
                "BookingQueue",
                HEALTH_THRESHOLD,
                MIN_UNHEALTHY_PERIOD_MIN,
                QUEUE_SIZE,
                THREADS_MINIMUM,
                THREADS_MAXIMUM);
    }

    public boolean isHealthy() {
        try {
            if (!healthyThreadPool.isHealthyOrShutdown()) {
                logger.warn("BookingQueue: Unhealthy queue terminated, starting a new one");
                initThreadPool();
            }
        } catch (InterruptedException e) {
            // TODO: evaluate crashing the whole springbook context here
            //  to force a container restart cycle
            logger.error("Failed to restart BookingThreadPool", e);
            return false;
        }

        return true;
    }

    public void execute(KeyRunnable r) {
        healthyThreadPool.execute(r);
    }


    public long getRejectedTaskCount() {
        return healthyThreadPool.getRejectedTaskCount();
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

}

