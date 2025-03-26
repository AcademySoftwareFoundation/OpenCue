
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

import java.lang.ref.WeakReference;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

import com.imageworks.spcue.grpc.report.HostReport;
import com.google.common.cache.Cache;
import com.google.common.cache.CacheBuilder;
import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.LogManager;

import com.imageworks.spcue.dispatcher.commands.DispatchHandleHostReport;
import com.imageworks.spcue.util.CueUtil;

public class HostReportQueue extends ThreadPoolExecutor {

    private static final Logger logger = LogManager.getLogger(HostReportQueue.class);
    private QueueRejectCounter rejectCounter = new QueueRejectCounter();
    private AtomicBoolean isShutdown = new AtomicBoolean(false);
    private int queueCapacity;

    private Cache<String, HostReportWrapper> hostMap =
            CacheBuilder.newBuilder().expireAfterWrite(1, TimeUnit.HOURS).build();

    /**
     * Wrapper around protobuf object HostReport to add reportTi
     */
    private class HostReportWrapper {
        private final HostReport hostReport;
        private final WeakReference<DispatchHandleHostReport> reportTaskRef;
        public long taskTime = System.currentTimeMillis();

        public HostReportWrapper(HostReport hostReport, DispatchHandleHostReport reportTask) {
            this.hostReport = hostReport;
            this.reportTaskRef = new WeakReference<>(reportTask);
        }

        public HostReport getHostReport() {
            return hostReport;
        }

        public DispatchHandleHostReport getReportTask() {
            return reportTaskRef.get();
        }

        public long getTaskTime() {
            return taskTime;
        }
    }

    public HostReportQueue(int threadPoolSizeInitial, int threadPoolSizeMax, int queueSize) {
        super(threadPoolSizeInitial, threadPoolSizeMax, 10, TimeUnit.SECONDS,
                new LinkedBlockingQueue<Runnable>(queueSize));
        this.setRejectedExecutionHandler(rejectCounter);
    }

    public void execute(DispatchHandleHostReport newReport) {
        if (isShutdown.get()) {
            return;
        }
        HostReportWrapper oldWrappedReport = hostMap.getIfPresent(newReport.getKey());
        // If hostReport exists on the cache and there's also a task waiting to be
        // executed
        // replace the old report by the new on, but refrain from creating another task
        if (oldWrappedReport != null) {
            DispatchHandleHostReport oldReport = oldWrappedReport.getReportTask();
            if (oldReport != null) {
                // Replace report, but keep the reference of the existing task
                hostMap.put(newReport.getKey(),
                        new HostReportWrapper(newReport.getHostReport(), oldReport));
                return;
            }
        }
        hostMap.put(newReport.getKey(),
                new HostReportWrapper(newReport.getHostReport(), newReport));
        super.execute(newReport);
    }

    public HostReport removePendingHostReport(String key) {
        if (key != null) {
            HostReportWrapper r = hostMap.getIfPresent(key);
            if (r != null) {
                hostMap.asMap().remove(key, r);
                return r.getHostReport();
            }
        }
        return null;
    }

    public long getRejectedTaskCount() {
        return rejectCounter.getRejectCount();
    }

    public int getQueueCapacity() {
        return queueCapacity;
    }

    public void shutdown() {
        if (!isShutdown.getAndSet(true)) {
            logger.info("Shutting down report pool, currently " + this.getActiveCount()
                    + " active threads.");

            final long startTime = System.currentTimeMillis();
            while (this.getQueue().size() != 0 && this.getActiveCount() != 0) {
                try {
                    logger.info("report pool is waiting for " + this.getQueue().size()
                            + " more units to complete");
                    if (System.currentTimeMillis() - startTime > 10000) {
                        throw new InterruptedException(
                                "report thread pool failed to shutdown properly");
                    }
                    Thread.sleep(250);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                }
            }
        }
    }

    public boolean isHealthy() {
        return getQueue().remainingCapacity() > 0;
    }
}
