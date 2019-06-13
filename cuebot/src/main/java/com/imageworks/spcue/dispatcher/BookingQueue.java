
/*
 * Copyright (c) 2018 Sony Pictures Imageworks Inc.
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

import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

import org.apache.log4j.Logger;
import org.springframework.stereotype.Component;

@Component
public class BookingQueue extends ThreadPoolExecutor {

    private static final Logger logger = Logger.getLogger(BookingQueue.class);

    private static final int INITIAL_QUEUE_SIZE = 1000;

    private static final int THREADS_MINIMUM = 6;
    private static final int THREADS_MAXIMUM = 6;
    private static final int THREADS_KEEP_ALIVE_SECONDS = 10;

    private int baseSleepTimeMillis = 400;
    private AtomicBoolean isShutdown = new AtomicBoolean(false);

    private QueueRejectCounter rejectCounter = new QueueRejectCounter();

    public BookingQueue() {
        super(THREADS_MINIMUM, THREADS_MAXIMUM, THREADS_KEEP_ALIVE_SECONDS,
                TimeUnit.SECONDS, new LinkedBlockingQueue<Runnable>(INITIAL_QUEUE_SIZE));
    }

    public BookingQueue(int sleepTimeMs) {
        super(THREADS_MINIMUM, THREADS_MAXIMUM, THREADS_KEEP_ALIVE_SECONDS,
                TimeUnit.SECONDS, new LinkedBlockingQueue<Runnable>(INITIAL_QUEUE_SIZE));
        this.baseSleepTimeMillis = sleepTimeMs;
        this.setRejectedExecutionHandler(rejectCounter);
    }

    public void execute(Runnable r) {
        if (!isShutdown.get()) {
            super.execute(r);
        }
    }

    public long getRejectedTaskCount() {
        return rejectCounter.getRejectCount();
    }

    public void shutdown() {
        if (!isShutdown.getAndSet(true)) {
            logger.info("clearing out booking queue: " + this.getQueue().size());
            this.getQueue().clear();
        }

    }

    /**
     * Lowers the sleep time as the queue grows.
     *
     * @return
     */
    public int sleepTime() {
        if (!isShutdown.get()) {
            int sleep = (int) (baseSleepTimeMillis - (((this.getQueue().size () /
                    (float) INITIAL_QUEUE_SIZE) * baseSleepTimeMillis)) * 2);
            if (sleep < 0) {
                sleep = 0;
            }
            return sleep;
        } else {
            return 0;
        }
    }

    protected void beforeExecute(Thread t, Runnable r) {
        super.beforeExecute(t, r);
        if (isShutdown()) {
            this.remove(r);
        } else {
            try {
                Thread.sleep(sleepTime());
            } catch (InterruptedException e) {
                logger.info("booking queue was interrupted.");
            }
        }
    }

    protected void afterExecute(Runnable r, Throwable t) {
        super.afterExecute(r, t);
        if (sleepTime() < 100) {
            getQueue().clear();
        }
    }
}

