
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

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

/**
 * The completion inbox for the scheduler's tick-start drain (the same design Plow uses: consume the
 * completion queue first on every pass, accounting rolled into one transaction).
 *
 * Frame-complete reports used to be processed on the gRPC threads that received them: dozens of
 * concurrent writers racing each other and the planner over the same rows. Two duplicate reports
 * interleaving with a job shutdown could throw mid-processing and leave an ORPHANED proc behind
 * (its frame back to WAITING, the proc row never deleted), and one such orphan wedges the planner's
 * batch commit permanently. The fix is architectural: the report thread only ACKS, RESOLVES (pure
 * reads) AND ENQUEUES here, and the scheduler tick drains the queue single-threaded before
 * planning, so completion WRITES and planning are one writer, in one place, in tick order. The
 * queue holds resolved completions, not raw reports, so the tick spends no time on per-report
 * lookups; that read work stays spread across the report threads that always did it.
 *
 * Every Cuebot drains its OWN queue (leader and standby alike): reports land on whichever Cuebot
 * RQD dialed, the database is the shared truth, and nothing is forwarded anywhere.
 *
 * Crash semantics, decided deliberately: an acked-but-undrained report lost to a crash leaves its
 * frame RUNNING with no one to report it again; the existing host-report reconciliation orphans and
 * requeues it, and the frame is redone. A few seconds of redone work beats any at-least-once
 * machinery.
 *
 * Static singleton on purpose: the enqueue side (FrameCompleteHandler) and the drain side
 * (Scheduler) are wired in different Spring contexts of the same process, and this queue is
 * process-local state with no configuration, so Spring plumbing would add wiring for nothing.
 */
public final class SchedulerCompletionQueue {

    private static final Logger logger = LogManager.getLogger(SchedulerCompletionQueue.class);

    /**
     * Hard cap on queued completions. At the default 3s tick a full farm completes a few thousand
     * frames per tick at the extreme; 200k means minutes of total drain outage before anything is
     * dropped, and a dropped report self-heals like a crash (reconciliation requeues the frame).
     */
    private static final int MAX_QUEUED = 200_000;

    private static final ConcurrentLinkedQueue<QueuedFrameCompletion> QUEUE =
            new ConcurrentLinkedQueue<>();
    private static final AtomicInteger SIZE = new AtomicInteger(0);
    private static final AtomicLong DROPPED = new AtomicLong(0);

    private SchedulerCompletionQueue() {}

    /** Ack-path enqueue. Never blocks, never throws; over the cap the completion is dropped. */
    public static void offer(QueuedFrameCompletion completion) {
        if (SIZE.get() >= MAX_QUEUED) {
            long n = DROPPED.incrementAndGet();
            if (n % 1000 == 1) {
                logger.warn("SchedulerCompletionQueue full (" + MAX_QUEUED
                        + "); dropping completion for " + "frame " + completion.frame.getName()
                        + " (total dropped " + n + "); host-report reconciliation will requeue it");
            }
            return;
        }
        QUEUE.offer(completion);
        SIZE.incrementAndGet();
    }

    /**
     * Drain-side take: everything queued right now, in arrival order. Completions arriving during
     * the drain wait for the next tick, so one drain is always bounded.
     */
    public static List<QueuedFrameCompletion> drain() {
        int n = SIZE.get();
        if (n == 0) {
            return java.util.Collections.emptyList();
        }
        List<QueuedFrameCompletion> out = new ArrayList<>(n);
        QueuedFrameCompletion c;
        while (out.size() < n && (c = QUEUE.poll()) != null) {
            SIZE.decrementAndGet();
            out.add(c);
        }
        return out;
    }

    public static int size() {
        return SIZE.get();
    }

    public static long dropped() {
        return DROPPED.get();
    }
}
