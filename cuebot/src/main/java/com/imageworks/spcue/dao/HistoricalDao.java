
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

package com.imageworks.spcue.dao;

import java.util.List;

import com.imageworks.spcue.JobInterface;

public interface HistoricalDao {

    /**
     * Return all jobs that have been finished longer than the specified cut off in hours.
     *
     * @param cutoffHours
     * @return
     */
    List<JobInterface> getFinishedJobs(int cutoffHours);

    /**
     * Transfer a job from the live tables to the historical tables.
     *
     * @param job
     */
    void transferJob(JobInterface job);

    /**
     * Apply up to {@code limit} queued frame history events to frame_history, oldest first, and
     * remove them from the queue. Returns an empty result without draining when another session
     * holds the drain lock.
     *
     * @param limit maximum number of events to drain
     * @param safe apply each event in its own subtransaction and drop the ones that fail
     * @return the drain outcome
     */
    FrameHistoryDrain drainFrameHistory(int limit, boolean safe);

    /**
     * Return the approximate size and age of the frame history queue.
     *
     * @return the queue backlog
     */
    FrameHistoryBacklog getFrameHistoryBacklog();

    /** Outcome of one {@link #drainFrameHistory} call. */
    final class FrameHistoryDrain {
        /** Events removed from the queue. */
        public final int drained;
        /** Events removed without being applied (orphaned or, in safe mode, failed). */
        public final int skipped;
        /** Runs whose start and end were written to frame_history as a single row. */
        public final int merged;

        public FrameHistoryDrain(int drained, int skipped, int merged) {
            this.drained = drained;
            this.skipped = skipped;
            this.merged = merged;
        }
    }

    /** Snapshot of the frame history queue backlog. */
    final class FrameHistoryBacklog {
        /** Upper bound on queued events (id span, so rolled-back ids count too). */
        public final long depth;
        /** Age in seconds of the oldest queued event, 0 when the queue is empty. */
        public final long oldestAgeSeconds;

        public FrameHistoryBacklog(long depth, long oldestAgeSeconds) {
            this.depth = depth;
            this.oldestAgeSeconds = oldestAgeSeconds;
        }
    }
}
