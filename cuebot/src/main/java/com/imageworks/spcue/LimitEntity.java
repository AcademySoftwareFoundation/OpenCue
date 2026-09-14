
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

package com.imageworks.spcue;

import com.imageworks.spcue.grpc.limit.Limit;
import com.imageworks.spcue.grpc.limit.LimitEnforcement;
import com.imageworks.spcue.grpc.limit.LimitType;

public class LimitEntity extends Entity implements LimitInterface {

    public int maxValue;
    public int currentRunning;

    public LimitType type = LimitType.FRAME;
    public LimitEnforcement enforcement = LimitEnforcement.ENFORCED;

    /** Usage above which only hosts already holding a token may book; -1 = same as maxValue. */
    public int softValue = -1;

    /** Usage reported by the license server as of reportedTime. */
    public int settledUsage;
    /** Usage booked since reportedTime and not yet visible to the server. */
    public int pendingUsage;
    /** Distinct hosts holding at least one token. */
    public int hostCount;

    /** Epoch millis of the last accepted report; 0 if never reported. */
    public long reportedTime;
    public String reportSource;
    /** Seconds after which a report is stale; 0 disables staleness. */
    public int reportTtl = 900;

    /** Frame exit status meaning "this license was unavailable"; null = no rule. */
    public Integer exitStatus;
    public int delayMinutes;
    public boolean autoTag = true;

    public int specLayerCount;
    public int autoLayerCount;

    public LimitEntity() {}

    public LimitEntity(Limit grpcLimit) {
        this.id = grpcLimit.getId();
        this.name = grpcLimit.getName();
        this.maxValue = grpcLimit.getMaxValue();
        this.currentRunning = grpcLimit.getCurrentRunning();
        this.type = grpcLimit.getType();
        this.enforcement = grpcLimit.getEnforcement();
        this.softValue = grpcLimit.getSoftValue();
        this.settledUsage = grpcLimit.getSettledUsage();
        this.pendingUsage = grpcLimit.getPendingUsage();
        this.hostCount = grpcLimit.getHostCount();
        this.reportedTime = grpcLimit.getLastReportTime() * 1000L;
        this.reportSource = grpcLimit.getReportSource();
        this.reportTtl = grpcLimit.getReportTtl();
        this.exitStatus = grpcLimit.getExitStatus() == 0 ? null : grpcLimit.getExitStatus();
        this.delayMinutes = grpcLimit.getDelayMinutes();
        this.autoTag = grpcLimit.getAutoTag();
        this.specLayerCount = grpcLimit.getSpecLayerCount();
        this.autoLayerCount = grpcLimit.getAutoLayerCount();
    }

    public String getLimitId() {
        return id;
    }

    /** Merged usage, settled + pending: what the dispatcher gates on. */
    public int getCurrentUsage() {
        return settledUsage + pendingUsage;
    }

    /**
     * Whether the last external report is older than the TTL. Limits that were never reported are
     * internal-only, not stale; a TTL of 0 disables staleness entirely.
     */
    public boolean isReportStale() {
        if (reportedTime == 0 || reportTtl <= 0) {
            return false;
        }
        return System.currentTimeMillis() - reportedTime > reportTtl * 1000L;
    }

    /**
     * Whether the limit currently gates booking. A stale limit behaves as advisory regardless of
     * its configured mode: the license server is still enforcing for real, so gating on data known
     * to be wrong only buys idle time.
     */
    public boolean isBlocking() {
        return enforcement == LimitEnforcement.ENFORCED && !isReportStale();
    }
}
