package com.imageworks.spcue.dispatcher;

import java.lang.management.ManagementFactory;
import java.lang.management.ThreadInfo;
import java.lang.management.ThreadMXBean;
import java.util.Date;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.LinkedBlockingQueue;

import com.google.common.cache.Cache;
import com.google.common.cache.CacheBuilder;
import com.imageworks.spcue.dispatcher.commands.DispatchBookHost;
import com.imageworks.spcue.dispatcher.commands.KeyRunnable;
import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.LogManager;

/**
 * A ThreadPoolExecutor with two additional features: - Handles repeated tasks by always keeping the
 * latest version - With isHealthyOrShutdown, the threadpool will drain and clear resources when
 * unhealthy
 *
 */
public class HealthyThreadPool extends ThreadPoolExecutor {
    // The service need s to be unhealthy for this period of time to report
    private static final Logger logger = LogManager.getLogger("HEALTH");
    // Threshold to consider healthy or unhealthy
    private final int healthThreshold;
    private final int poolSize;
    private final int minUnhealthyPeriodMin;
    private final QueueRejectCounter rejectCounter = new QueueRejectCounter();
    private final Cache<String, KeyRunnable> taskCache;
    private final String name;
    private Date lastCheck = new Date();
    private boolean wasHealthy = true;
    protected final AtomicBoolean isShutdown = new AtomicBoolean(false);
    private final int baseSleepTimeMillis;

    /**
     * Start a thread pool
     *
     * @param name For logging purposes
     * @param healthThreshold Percentage that should be available to consider healthy
     * @param minUnhealthyPeriodMin Period in min to consider a queue unhealthy
     * @param poolSize how many jobs can be queued
     * @param threadsMinimum Minimum number of threads
     * @param threadsMaximum Maximum number of threads to grow to
     */
    public HealthyThreadPool(String name, int healthThreshold, int minUnhealthyPeriodMin,
            int poolSize, int threadsMinimum, int threadsMaximum) {
        this(name, healthThreshold, minUnhealthyPeriodMin, poolSize, threadsMinimum, threadsMaximum,
                0);
    }

    /**
     * Start a thread pool
     *
     * @param name For logging purposes
     * @param healthThreshold Percentage that should be available to consider healthy
     * @param minUnhealthyPeriodMin Period in min to consider a queue unhealthy
     * @param poolSize how many jobs can be queued
     * @param threadsMinimum Minimum number of threads
     * @param threadsMaximum Maximum number of threads to grow to
     * @param baseSleepTimeMillis Time a thread should sleep when the service is not under pressure
     */
    public HealthyThreadPool(String name, int healthThreshold, int minUnhealthyPeriodMin,
            int poolSize, int threadsMinimum, int threadsMaximum, int baseSleepTimeMillis) {
        super(threadsMinimum, threadsMaximum, 10, TimeUnit.SECONDS,
                new LinkedBlockingQueue<Runnable>(poolSize));

        logger.debug(name + ": Starting a new HealthyThreadPool");
        this.name = name;
        this.healthThreshold = healthThreshold;
        this.poolSize = poolSize;
        this.minUnhealthyPeriodMin = minUnhealthyPeriodMin;
        this.baseSleepTimeMillis = baseSleepTimeMillis;
        this.setRejectedExecutionHandler(rejectCounter);

        this.taskCache = CacheBuilder.newBuilder().expireAfterWrite(3, TimeUnit.MINUTES)
                // Invalidate entries that got executed by the threadPool and lost their
                // reference
                .weakValues().concurrencyLevel(threadsMaximum).build();
    }

    public void execute(KeyRunnable r) {
        if (isShutdown.get()) {
            logger.info(name + ": Task ignored, queue on hold or shutdown");
            return;
        }
        if (taskCache.getIfPresent(r.getKey()) == null) {
            taskCache.put(r.getKey(), r);
            super.execute(r);
        }
    }

    public long getRejectedTaskCount() {
        return rejectCounter.getRejectCount();
    }

    /**
     * Monitor if the queue is unhealthy for MIN_UNHEALTHY_PERIOD_MIN
     *
     * If unhealthy, the service will start the shutdown process and the caller is responsible for
     * starting a new instance after the lock on awaitTermination is released.
     */
    protected boolean shutdownUnhealthy() throws InterruptedException {
        Date now = new Date();
        if (diffInMinutes(lastCheck, now) > minUnhealthyPeriodMin) {
            this.wasHealthy = healthCheck();
            this.lastCheck = now;
        }

        if (healthCheck() || wasHealthy) {
            logger.debug(name + ": healthy (" + "Remaining Capacity: "
                    + this.getQueue().remainingCapacity() + ", Running: " + this.getActiveCount()
                    + ", Total Executed: " + this.getCompletedTaskCount() + ")");
            return true;
        } else if (isShutdown.get()) {
            logger.warn("Queue shutting down");
            return false;
        } else {
            logger.warn(name + ": unhealthy, starting shutdown)");
            threadDump();

            isShutdown.set(true);
            super.shutdownNow();
            logger.warn(name + ": Awaiting unhealthy queue termination");
            if (super.awaitTermination(1, TimeUnit.MINUTES)) {
                logger.info(name + ": Terminated successfully");
            } else {
                logger.warn(name + ": Failed to terminate");
            }
            // Threads will eventually terminate, proceed
            taskCache.invalidateAll();
            return false;
        }
    }

    private void threadDump() {
        ThreadMXBean mx = ManagementFactory.getThreadMXBean();
        for (ThreadInfo info : mx.dumpAllThreads(true, true)) {
            logger.debug(info.toString());
        }
    }

    private static long diffInMinutes(Date dateStart, Date dateEnd) {
        return TimeUnit.MINUTES.convert(dateEnd.getTime() - dateStart.getTime(),
                TimeUnit.MILLISECONDS);
    }

    /**
     * Lowers the sleep time as the queue grows.
     *
     * @return
     */
    public int sleepTime() {
        if (!isShutdown.get()) {
            int sleep = (int) (baseSleepTimeMillis
                    - (((this.getQueue().size() / (float) this.poolSize) * baseSleepTimeMillis))
                            * 2);
            if (sleep < 0) {
                sleep = 0;
            }
            return sleep;
        } else {
            return 0;
        }
    }

    @Override
    protected void beforeExecute(Thread t, Runnable r) {
        super.beforeExecute(t, r);
        if (isShutdown()) {
            this.remove(r);
        } else {
            if (baseSleepTimeMillis > 0) {
                try {
                    Thread.sleep(sleepTime());
                } catch (InterruptedException e) {
                    logger.info(name + ": booking queue was interrupted.");
                }
            }
        }
    }

    @Override
    protected void afterExecute(Runnable r, Throwable t) {
        super.afterExecute(r, t);

        // Invalidate cache to avoid having to wait for GC to mark processed entries
        // collectible
        KeyRunnable h = (KeyRunnable) r;
        taskCache.invalidate(h.getKey());
    }

    protected boolean healthCheck() {
        return (this.getQueue().remainingCapacity() > 0)
                || (getRejectedTaskCount() < this.poolSize / healthThreshold);
    }

    public void shutdown() {
        if (!isShutdown.getAndSet(true)) {
            logger.info("Shutting down thread pool " + name + ", currently " + getActiveCount()
                    + " active threads.");
            final long startTime = System.currentTimeMillis();
            while (this.getQueue().size() != 0 && this.getActiveCount() != 0) {
                try {
                    if (System.currentTimeMillis() - startTime > 10000) {
                        throw new InterruptedException(
                                name + " thread pool failed to shutdown properly");
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
