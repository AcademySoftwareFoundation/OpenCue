
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

import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;

import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.LogManager;
import org.springframework.core.task.TaskExecutor;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

public class DispatchQueue {

    private TaskExecutor dispatchPool;
    private ThreadPoolTaskExecutor _dispatchPool;
    private String name = "Default";
    private AtomicBoolean isShutdown = new AtomicBoolean(false);

    private final AtomicLong tasksRun = new AtomicLong(0);
    private final AtomicLong tasksRejected = new AtomicLong(0);

    private static final Logger logger = LogManager.getLogger(DispatchQueue.class);

    public DispatchQueue() {}

    public DispatchQueue(String name) {
        this.name = name;
    }

    public void execute(Runnable r) {
        try {
            if (!isShutdown.get()) {
                this.dispatchPool.execute(r);
                tasksRun.addAndGet(1);
            }
        } catch (Exception e) {
            long rejection = tasksRejected.addAndGet(1);
            logger.warn("Warning, dispatch queue - [" + name + "] rejected,  " + e);
            throw new DispatchQueueTaskRejectionException(
                    "Warning, dispatch queue [" + name + " rejected task #"
                            + rejection);
        }
    }

    public int getMaxPoolSize() {
        return _dispatchPool.getMaxPoolSize();
    }

    public int getActiveThreadCount() {
        return _dispatchPool.getActiveCount();
    }

    public int getWaitingCount() {
        return _dispatchPool.getThreadPoolExecutor().getQueue().size();
    }

    public int getRemainingCapacity() {
        return _dispatchPool.getThreadPoolExecutor().getQueue().remainingCapacity();
    }

    public long getTotalDispatched() {
        return tasksRun.get();
    }

    public long getTotalRejected() {
        return tasksRejected.get();
    }

    public TaskExecutor getDispatchPool() {
        return dispatchPool;
    }

    public void setDispatchPool(TaskExecutor dispatchPool) {
        this.dispatchPool = dispatchPool;
        this._dispatchPool = (ThreadPoolTaskExecutor) dispatchPool;
    }

    public void shutdown() {
        if (!isShutdown.getAndSet(true)) {
            logger.info("Shutting down thread pool " + name + ", currently "
                    + getActiveThreadCount() + " active threads.");
            final long startTime = System.currentTimeMillis();
            while (getWaitingCount() != 0 && getActiveThreadCount() != 0) {
                try {
                    if (System.currentTimeMillis() - startTime > 10000) {
                        throw new InterruptedException(name
                                + " thread pool failed to shutdown properly");
                    }
                    Thread.sleep(250);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                }
            }
        }
    }
}

