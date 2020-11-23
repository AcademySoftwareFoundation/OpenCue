
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

import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

import com.imageworks.spcue.grpc.report.HostReport;
import org.apache.log4j.Logger;
import com.google.common.cache.Cache;
import com.google.common.cache.CacheBuilder;

import com.imageworks.spcue.dispatcher.commands.DispatchHandleHostReport;

public class HostReportQueue extends ThreadPoolExecutor {

    private static final Logger logger = Logger.getLogger(HostReportQueue.class);

    private static final int THREAD_POOL_SIZE_INITIAL = 8;
    private static final int THREAD_POOL_SIZE_MAX = 16;
    // The queue size should be higher then the expected amount of hosts
    private static final int QUEUE_SIZE = 5000;

    private QueueRejectCounter rejectCounter = new QueueRejectCounter();
    private AtomicBoolean isShutdown = new AtomicBoolean(false);

    private Cache<String, HostReport> hostMap = CacheBuilder.newBuilder()
            .expireAfterWrite(1, TimeUnit.HOURS)
            .build();

    public HostReportQueue() {
        super(THREAD_POOL_SIZE_INITIAL, THREAD_POOL_SIZE_MAX, 10 , TimeUnit.SECONDS,
                new LinkedBlockingQueue<Runnable>(QUEUE_SIZE));
        this.setRejectedExecutionHandler(rejectCounter);
    }

    public void execute(DispatchHandleHostReport newReport) {
        if (isShutdown.get()) {
            return;
        }
        // Replace pending reports if they exist, and just enqueue a new thread if
        // there is no report pending.
        HostReport oldReport = hostMap.getIfPresent(newReport.getKey());
        hostMap.put(newReport.getKey(), newReport.getHostReport());
        if (oldReport == null) {
            super.execute(newReport);
        }
    }

    public HostReport removePendingHostReport(String key) {
        if (key != null) {
            HostReport r = hostMap.getIfPresent(key);
            if (r != null) {
                hostMap.asMap().remove(key, r);
                return r;
            }
        }
        return null;
    }

    public long getRejectedTaskCount() {
        return rejectCounter.getRejectCount();
    }

    public void shutdown() {
        if (!isShutdown.getAndSet(true)) {
            logger.info("Shutting down report pool, currently " + this.getActiveCount() + " active threads.");

            final long startTime = System.currentTimeMillis();
            while (this.getQueue().size() != 0 && this.getActiveCount() != 0) {
                try {
                    logger.info("report pool is waiting for " + this.getQueue().size() + " more units to complete");
                    if (System.currentTimeMillis() - startTime > 10000) {
                        throw new InterruptedException("report thread pool failed to shutdown properly");
                    }
                    Thread.sleep(250);
                } catch (InterruptedException e) {
                    break;
                }
            }
        }
    }

    public ConcurrentMap<String, HostReport> getHostMap() {
        return hostMap.asMap();
    }

}

