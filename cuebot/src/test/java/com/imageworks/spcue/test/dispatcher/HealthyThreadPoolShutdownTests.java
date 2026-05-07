
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
import java.util.concurrent.atomic.AtomicReference;

import org.junit.Test;

import com.imageworks.spcue.dispatcher.HealthyThreadPool;
import com.imageworks.spcue.dispatcher.commands.KeyRunnable;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertTrue;

/**
 * Unit tests for {@link HealthyThreadPool} shutdown behavior. No Spring context required —
 * these test the executor semantics directly.
 */
public class HealthyThreadPoolShutdownTests {

    @Test
    public void shutdown_drainsRunningTask() throws InterruptedException {
        HealthyThreadPool pool = new HealthyThreadPool("t1", 6, 3, 100, 2, 4);
        pool.setShutdownDrainMs(5000);

        AtomicInteger ran = new AtomicInteger();
        CountDownLatch started = new CountDownLatch(1);
        CountDownLatch release = new CountDownLatch(1);

        pool.execute(new KeyRunnable("k1") {
            @Override
            public void run() {
                started.countDown();
                try {
                    release.await();
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
                ran.incrementAndGet();
            }
        });

        assertTrue("task did not start", started.await(2, TimeUnit.SECONDS));

        Thread shutdownThread = new Thread(pool::shutdown);
        shutdownThread.start();
        Thread.sleep(200);

        // Releasing the task must let shutdown() unblock and complete.
        release.countDown();
        shutdownThread.join(7000);

        assertEquals(1, ran.get());
        assertTrue("pool should be terminated", pool.isTerminated());
    }

    @Test
    public void shutdown_waitsForBusyWorkerEvenWhenQueueEmpty() throws InterruptedException {
        // Verifies the && -> || fix: with the old buggy condition, the loop exits the
        // moment the queue empties, before the running task finishes. With the fix,
        // shutdown() should block until the task completes.
        HealthyThreadPool pool = new HealthyThreadPool("t2", 6, 3, 100, 1, 1);
        pool.setShutdownDrainMs(5000);

        AtomicBoolean done = new AtomicBoolean();

        pool.execute(new KeyRunnable("k1") {
            @Override
            public void run() {
                try {
                    Thread.sleep(800);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
                done.set(true);
            }
        });

        // Give the worker time to dequeue and start running.
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
    public void execute_afterShutdown_runsSynchronouslyOnCallerThread() {
        HealthyThreadPool pool = new HealthyThreadPool("t3", 6, 3, 100, 1, 1);
        pool.setShutdownDrainMs(1000);
        pool.shutdown();

        AtomicInteger ran = new AtomicInteger();
        AtomicReference<Thread> ranOn = new AtomicReference<>();
        Thread caller = Thread.currentThread();

        pool.execute(new KeyRunnable("k") {
            @Override
            public void run() {
                ranOn.set(Thread.currentThread());
                ran.incrementAndGet();
            }
        });

        assertEquals("task must run exactly once", 1, ran.get());
        assertSame("task must run on caller thread", caller, ranOn.get());
    }
}
