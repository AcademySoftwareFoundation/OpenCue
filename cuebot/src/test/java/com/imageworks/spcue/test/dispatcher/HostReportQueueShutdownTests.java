
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

package com.imageworks.spcue.test.dispatcher;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

import org.junit.Test;

import com.imageworks.spcue.dispatcher.HostReportQueue;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

/**
 * Unit tests for {@link HostReportQueue} shutdown behavior. Submits via the inherited
 * {@code ThreadPoolExecutor.execute(Runnable)} to avoid building real protobuf reports — shutdown
 * semantics depend only on the underlying executor, not the report type.
 */
public class HostReportQueueShutdownTests {

    @Test
    public void shutdown_drainsRunningTask() throws InterruptedException {
        HostReportQueue pool = new HostReportQueue(2, 4, 100);
        pool.setShutdownDrainMs(5000);

        AtomicInteger ran = new AtomicInteger();
        CountDownLatch started = new CountDownLatch(1);
        CountDownLatch release = new CountDownLatch(1);

        pool.execute((Runnable) () -> {
            started.countDown();
            try {
                release.await();
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
            ran.incrementAndGet();
        });

        assertTrue("task did not start", started.await(2, TimeUnit.SECONDS));

        Thread shutdownThread = new Thread(pool::shutdown);
        shutdownThread.start();
        Thread.sleep(200);

        release.countDown();
        shutdownThread.join(7000);

        assertEquals(1, ran.get());
        assertTrue("pool should be terminated", pool.isTerminated());
    }

    @Test
    public void shutdown_waitsForBusyWorkerEvenWhenQueueEmpty() throws InterruptedException {
        // Verifies the && -> || fix in HostReportQueue.shutdown().
        HostReportQueue pool = new HostReportQueue(1, 1, 100);
        pool.setShutdownDrainMs(5000);

        AtomicBoolean done = new AtomicBoolean();

        pool.execute((Runnable) () -> {
            try {
                Thread.sleep(800);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
            done.set(true);
        });

        Thread.sleep(150);

        long t0 = System.currentTimeMillis();
        pool.shutdown();
        long elapsed = System.currentTimeMillis() - t0;

        assertTrue("expected shutdown to block on busy worker, elapsed=" + elapsed + "ms",
                elapsed >= 500);
        assertTrue("task did not finish before shutdown returned", done.get());
        assertTrue("pool should be terminated", pool.isTerminated());
    }

    @Test
    public void shutdown_drainsQueueBacklog() throws InterruptedException {
        // Submit several quick tasks so some are queued; verify all complete.
        HostReportQueue pool = new HostReportQueue(1, 1, 100);
        pool.setShutdownDrainMs(5000);

        AtomicInteger ran = new AtomicInteger();
        for (int i = 0; i < 5; i++) {
            pool.execute((Runnable) () -> {
                try {
                    Thread.sleep(100);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
                ran.incrementAndGet();
            });
        }

        pool.shutdown();

        assertEquals("all queued tasks should have run before shutdown returned", 5, ran.get());
        assertTrue("pool should be terminated", pool.isTerminated());
    }
}
