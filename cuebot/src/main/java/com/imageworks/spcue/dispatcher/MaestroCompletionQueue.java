
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

/**
 * The resolved completions waiting for Maestro's drain. A report thread resolves a report (pure
 * reads) and offers it here; the scheduler tick drains everything queued and applies the frame
 * stops in one batch, single-threaded and in arrival order, which ends the races of concurrent
 * per-report processing (see FrameCompleteHandler.handleFrameCompleteReport).
 *
 * Nothing is refused and nothing is dropped: the RQD channel makes at most four attempts per report
 * (rqd/rqd/rqnetwork.py) and postFrameAction deletes the frame before the send, so a report refused
 * past those attempts is lost for good. The queue is therefore unbounded; its depth is the
 * completion rate times the time the drain stands still, a few kilobytes per entry.
 *
 * The queue lives in memory only. A cuebot crash loses what it holds: those frames stay RUNNING
 * with procs that no RQD frame backs, until the maintenance orphan pass (a proc past its ping
 * deferral) kills on the host, finds nothing there, and stops the frame WAITING, so it runs again
 * rather than vanishes; a host that stays unreachable past the deferral parks it DEAD for a manual
 * retry. That is the recovery a crash between a report's acknowledgement and its processing always
 * relied on; the queue adds no new failure mode, only a wider window during a drain stall.
 */
public final class MaestroCompletionQueue {
    private static final ConcurrentLinkedQueue<QueuedFrameCompletion> QUEUE =
            new ConcurrentLinkedQueue<>();
    private static final AtomicInteger SIZE = new AtomicInteger(0);

    private MaestroCompletionQueue() {}

    /** Ack-path enqueue: never blocks, never throws, never refuses. */
    public static void offer(QueuedFrameCompletion completion) {
        QUEUE.offer(completion);
        SIZE.incrementAndGet();
    }

    /**
     * Drain-side take: everything queued right now, in arrival order. Completions arriving during
     * the drain wait for the next tick, so one drain is bounded by what arrived before it.
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
}
