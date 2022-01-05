
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

import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

import com.google.common.cache.Cache;
import com.google.common.cache.CacheBuilder;
import com.imageworks.spcue.dispatcher.commands.DispatchBookHost;
import com.imageworks.spcue.util.CueUtil;

import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.LogManager;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;

public class BookingQueue extends ThreadPoolExecutor {

    private static final Logger logger = LogManager.getLogger(BookingQueue.class);

    private static final int THREADS_KEEP_ALIVE_SECONDS = 10;

    private int queueCapacity;
    private int baseSleepTimeMillis = 400;
    private AtomicBoolean isShutdown = new AtomicBoolean(false);

    private QueueRejectCounter rejectCounter = new QueueRejectCounter();

    private Cache<String, DispatchBookHost> bookingCache = CacheBuilder.newBuilder()
            .expireAfterWrite(3, TimeUnit.MINUTES)
            // Invalidate entries that got executed by the threadpool and lost their reference
            .weakValues()
            .build();

    private BookingQueue(int corePoolSize, int maxPoolSize, int queueCapacity, int sleepTimeMs) {
        super(corePoolSize, maxPoolSize, THREADS_KEEP_ALIVE_SECONDS,
                TimeUnit.SECONDS, new LinkedBlockingQueue<Runnable>(queueCapacity));
        this.queueCapacity = queueCapacity;
        this.baseSleepTimeMillis = sleepTimeMs;
        this.setRejectedExecutionHandler(rejectCounter);
        logger.info("BookingQueue" +
                    " core:" + getCorePoolSize() +
                    " max:" + getMaximumPoolSize() +
                    " capacity:" + queueCapacity +
                    " sleepTimeMs:" + sleepTimeMs);
    }

    @Autowired
    public BookingQueue(Environment env, String propertyKeyPrefix, int sleepTimeMs) {
        this(CueUtil.getIntProperty(env, propertyKeyPrefix, "core_pool_size"),
             CueUtil.getIntProperty(env, propertyKeyPrefix, "max_pool_size"),
             CueUtil.getIntProperty(env, propertyKeyPrefix, "queue_capacity"),
             sleepTimeMs);
    }

    public void execute(DispatchBookHost r) {
        if (isShutdown.get()) {
            return;
        }
        if (bookingCache.getIfPresent(r.getKey()) == null){
            bookingCache.put(r.getKey(), r);
            super.execute(r);
        }
    }

    public long getRejectedTaskCount() {
        return rejectCounter.getRejectCount();
    }

    public int getQueueCapacity() {
        return queueCapacity;
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
                    (float) queueCapacity) * baseSleepTimeMillis)) * 2);
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
                Thread.currentThread().interrupt();
            }
        }
    }

    protected void afterExecute(Runnable r, Throwable t) {
        super.afterExecute(r, t);

        // Invalidate cache to avoid having to wait for GC to mark processed entries collectible
        DispatchBookHost h = (DispatchBookHost)r;
        bookingCache.invalidate(h.getKey());

        if (sleepTime() < 100) {
            logger.info("BookingQueue cleanup executed.");
            getQueue().clear();
        }
    }
}

