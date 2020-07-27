
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

import org.apache.log4j.Logger;

import com.imageworks.spcue.dispatcher.commands.DispatchHandleHostReport;

public class HostReportQueue extends ThreadPoolExecutor {

    private static final Logger logger = Logger.getLogger(HostReportQueue.class);

    private static final int THREAD_POOL_SIZE_INITIAL = 6;
    private static final int THREAD_POOL_SIZE_MAX = 8;
    private static final int QUEUE_SIZE_INITIAL = 1000;

    private QueueRejectCounter rejectCounter = new QueueRejectCounter();
    private AtomicBoolean isShutdown = new AtomicBoolean(false);

    public HostReportQueue() {
        super(THREAD_POOL_SIZE_INITIAL, THREAD_POOL_SIZE_MAX, 10 , TimeUnit.SECONDS,
                new LinkedBlockingQueue<Runnable>(QUEUE_SIZE_INITIAL));
        this.setRejectedExecutionHandler(rejectCounter);

    }

    public void execute(DispatchHandleHostReport r) {
        if (isShutdown.get()) {
            return;
        }
        if (getQueue().contains(r)) {
            getQueue().remove(r);
        }
        super.execute(r);
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
}

