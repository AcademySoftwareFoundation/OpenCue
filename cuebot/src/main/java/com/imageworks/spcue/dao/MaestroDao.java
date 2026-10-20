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

import java.sql.Connection;
import java.sql.SQLException;
import java.util.List;
import java.util.Map;
import java.util.Set;

import com.imageworks.spcue.dispatcher.Maestro;

/**
 * The database reads and writes of the Maestro scheduler: the per-tick farm snapshot, the candidate
 * read, limit budgets, the batched resource-counter mirrors and the planning-leadership lock.
 *
 * Every read here is a point-in-time snapshot. Maestro plans against it in memory and the commit's
 * frame-version guard settles any race, so none of these methods needs to lock what it reads.
 */
public interface MaestroDao {

    /**
     * Every host Maestro may place frames on: UP and OPEN, busy or idle. Each host carries its
     * total and idle capacity, so the caller can group and fit without a second lookup.
     */
    List<Maestro.BookableHost> getSchedulableHosts();

    /**
     * Cores and frames held by live procs, per show, for the shows Maestro plans: every show when
     * {@code facilityMode}, otherwise only the scheduler-managed ones.
     */
    List<ShowUsage> getLiveShowUsage(boolean facilityMode);

    /**
     * Every dispatchable layer of the shows Maestro plans (all of them when {@code facilityMode},
     * otherwise the scheduler-managed ones), with the job fields groups are cut on. Nothing in it
     * depends on a host group: the subscription figures on each candidate are zero, to be filled in
     * per group from {@link #getSubscriptions}.
     */
    List<Maestro.CandidateRow> getCandidateRows(boolean facilityMode);

    /** Every subscription's cores in use, burst and size. */
    List<SubscriptionUsage> getSubscriptions();

    /** How many frames each layer runs on each host right now. Procs with no layer are ignored. */
    List<HostLayerFrames> getRunningFramesByHostLayer();

    /**
     * Diagnostics: the highest-priority pending layers, each with every candidate-read predicate
     * evaluated as a separate flag against one host group, so the gate that excluded a layer can be
     * named. Read-only and bounded; meant for DEBUG logging only.
     */
    List<GroupExclusion> explainGroupExclusions(String groupTags, String groupOs, String facilityId,
            boolean allThreadMode, int maxCoresTotal, boolean facilityMode, String allocId);

    /**
     * Usage and thresholds of every limit that gates booking right now, counted the same way as the
     * legacy dispatcher's limit gate. ADVISORY and DISABLED limits, and limits whose external
     * report has gone stale, are absent.
     */
    List<LimitUsage> getGatingLimitUsage();

    /**
     * The short host names holding each HOST-type limit, keyed by limit id: hosts the license
     * server reports, plus every host running a frame of a layer bound to the limit. The returned
     * sets are mutable and owned by the caller.
     */
    Map<String, Set<String>> getHostLimitHolders();

    /**
     * The procs running on the given hosts, each with how long it has run and its layer's average
     * successful runtime (-1 when the layer has no successful frame yet).
     */
    List<RunningProcEstimate> getRunningProcEstimates(List<String> hostIds);

    /**
     * Add booked cores and gpus to the subscription mirrors. Must run inside the transaction that
     * created the procs, so the mirror and the procs land together. Never rejected for crossing a
     * subscription's burst: burst is enforced at plan time, the mirror records reality.
     */
    void addSubscriptionUsage(List<SubscriptionDelta> deltas);

    /**
     * Add booked cores and gpus to the layer mirrors. Same transaction rule as
     * {@link #addSubscriptionUsage}. A layer deleted meanwhile updates nothing.
     */
    void addLayerUsage(List<ResourceDelta> deltas);

    /**
     * Add booked cores and gpus to the job, folder and point mirrors of each job. Same transaction
     * rule as {@link #addSubscriptionUsage}; never rejected for crossing a job's max cores, which
     * is enforced at plan time. A job deleted meanwhile updates nothing.
     */
    void addJobUsage(List<ResourceDelta> deltas);

    /**
     * Try to take the cluster-wide planning lock on {@code connection} without waiting. The lock is
     * session-scoped and re-entrant: it lives exactly as long as the connection, and every
     * successful call needs its own release.
     *
     * @return true when this connection now holds the lock
     */
    boolean tryAcquireSchedulerLock(Connection connection) throws SQLException;

    /** Release one hold of the planning lock taken on {@code connection}. */
    void releaseSchedulerLock(Connection connection) throws SQLException;

    /** Cores (core points) and frames held by one show's live procs. */
    final class ShowUsage {
        public final String showName;
        public final long corePoints;
        public final long frames;

        public ShowUsage(String showName, long corePoints, long frames) {
            this.showName = showName;
            this.corePoints = corePoints;
            this.frames = frames;
        }
    }

    /** One subscription's figures, in core points. */
    final class SubscriptionUsage {
        public final String showId;
        public final String allocId;
        public final long cores;
        public final long burst;
        public final long size;

        public SubscriptionUsage(String showId, String allocId, long cores, long burst, long size) {
            this.showId = showId;
            this.allocId = allocId;
            this.cores = cores;
            this.burst = burst;
            this.size = size;
        }
    }

    /** Frames one layer runs on one host. */
    final class HostLayerFrames {
        public final String hostId;
        public final String layerId;
        public final int frames;

        public HostLayerFrames(String hostId, String layerId, int frames) {
            this.hostId = hostId;
            this.layerId = layerId;
            this.frames = frames;
        }
    }

    /** One pending layer with each candidate-read predicate evaluated on its own. */
    final class GroupExclusion {
        public String jobName;
        public String layerName;
        public String layerTags;
        public int priority;
        public boolean tagOk;
        public boolean osOk;
        public boolean facilityOk;
        public boolean threadOk;
        public boolean hasSubscription;
        public boolean underBurst;
        public boolean underJobCap;
        public boolean fitsCores;
        public boolean hasWaiting;
        public boolean folderOk;
        public boolean managedOk;
    }

    /** One gating limit's thresholds and current usage; {@code type} is FRAME or HOST. */
    final class LimitUsage {
        public final String limitId;
        public final String name;
        public final String type;
        public final int softValue;
        public final int maxValue;
        public final int usage;

        public LimitUsage(String limitId, String name, String type, int softValue, int maxValue,
                int usage) {
            this.limitId = limitId;
            this.name = name;
            this.type = type;
            this.softValue = softValue;
            this.maxValue = maxValue;
            this.usage = usage;
        }
    }

    /** One running proc, for estimating when its host frees its cores. */
    final class RunningProcEstimate {
        public final String hostId;
        public final int coresReserved;
        public final int elapsedSeconds;
        public final int averageSeconds;

        public RunningProcEstimate(String hostId, int coresReserved, int elapsedSeconds,
                int averageSeconds) {
            this.hostId = hostId;
            this.coresReserved = coresReserved;
            this.elapsedSeconds = elapsedSeconds;
            this.averageSeconds = averageSeconds;
        }
    }

    /** Cores and gpus to add to one subscription's mirror. */
    final class SubscriptionDelta {
        public final String showId;
        public final String allocId;
        public final int cores;
        public final int gpus;

        public SubscriptionDelta(String showId, String allocId, int cores, int gpus) {
            this.showId = showId;
            this.allocId = allocId;
            this.cores = cores;
            this.gpus = gpus;
        }
    }

    /** Cores and gpus to add to the mirrors of one layer or job, identified by {@code id}. */
    final class ResourceDelta {
        public final String id;
        public final int cores;
        public final int gpus;

        public ResourceDelta(String id, int cores, int gpus) {
            this.id = id;
            this.cores = cores;
            this.gpus = gpus;
        }
    }
}
