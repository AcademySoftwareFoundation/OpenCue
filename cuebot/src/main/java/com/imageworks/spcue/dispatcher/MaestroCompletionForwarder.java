
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
import java.util.Collections;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;
import org.springframework.dao.EmptyResultDataAccessException;

import com.imageworks.spcue.PrometheusMetricsCollector;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.grpc.report.FrameCompleteReport;
import com.imageworks.spcue.grpc.report.RqdReportInterfaceGrpc;
import com.imageworks.spcue.grpc.report.RqdReportRunningFrameCompletionRequest;
import com.imageworks.spcue.service.HostManager;

/**
 * Config-gated relay that lets a legacy cuebot forward a scheduler-managed show's
 * {@link FrameCompleteReport}s to the isolated Maestro deployment, so Maestro's completion drain
 * earns production exposure before the facility flip while the legacy path stays the
 * always-available fallback.
 *
 * The forward is transparent to the receiver: the unmodified report enters the pair's
 * {@code RqdReportInterface.ReportRunningFrameCompletion} RPC exactly like a direct RQD report. One
 * attempt per report with a short deadline; any failure hands the report back to the legacy path on
 * this thread, and a forward failure is never surfaced to RQD (RQD already delivered its report
 * successfully; the failure is ours to absorb). A consecutive-failure breaker keeps a down leader
 * from adding the forward deadline to every managed-show completion: while open, reports take the
 * instant local fallback, and after the cooldown the next managed-show report is the probe.
 *
 * Rollout scaffolding, not a permanent feature: once no cuebot runs with Maestro off, the
 * forwarding hook in {@link FrameCompleteHandler} is never reached and this class is deleted.
 */
public class MaestroCompletionForwarder {

    private static final Logger logger = LogManager.getLogger(MaestroCompletionForwarder.class);

    /**
     * What became of one report offered to the forwarder: either it was forwarded (ACKed by the
     * isolated deployment, nothing left to do locally), or the legacy path must process it, handed
     * the proc the forwarder read when that snapshot is still fresh (null when the forwarder never
     * read it, or when a send attempt made the snapshot deadline-stale and the legacy path must
     * re-read).
     */
    public static final class Outcome {
        private static final Outcome FORWARDED = new Outcome(true, null);
        private static final Outcome NOT_ATTEMPTED = new Outcome(false, null);

        private final boolean forwarded;
        private final VirtualProc proc;

        private Outcome(boolean forwarded, VirtualProc proc) {
            this.forwarded = forwarded;
            this.proc = proc;
        }

        static Outcome notAttempted(VirtualProc proc) {
            return proc == null ? NOT_ATTEMPTED : new Outcome(false, proc);
        }

        /** True when the report was ACKed by the isolated deployment; nothing to do locally. */
        public boolean forwarded() {
            return forwarded;
        }

        /** The proc the forwarder read, for the legacy path to reuse; null = not read. */
        public VirtualProc proc() {
            return proc;
        }
    }

    private final List<String> targets;
    private final long deadlineMs;
    private final int breakerFailures;
    private final long breakerCooldownMs;

    private HostManager hostManager;
    private ShowDao showDao;
    private PrometheusMetricsCollector prometheusMetrics;

    private final ConcurrentHashMap<String, ManagedChannel> channels = new ConcurrentHashMap<>();

    /**
     * Breaker state, deliberately minimal and approximate: races between report threads can cost a
     * spurious open (in-flight failures landing after a successful probe) or an extra probe, never
     * a lost report (every non-forwarded report is processed locally). The half-open probe itself
     * is single-flight via {@code probeInFlight}.
     */
    private final AtomicInteger consecutiveFailures = new AtomicInteger();
    private final AtomicBoolean probeInFlight = new AtomicBoolean();
    private volatile long openUntil = 0;
    private volatile int targetIndex = 0;
    private volatile long lastWarnMs = 0;

    @Autowired
    public MaestroCompletionForwarder(Environment env) {
        List<String> parsed = new ArrayList<String>();
        for (String target : env.getProperty("maestro.forward_completions_to", "").split(",")) {
            if (!target.trim().isEmpty()) {
                parsed.add(target.trim());
            }
        }
        this.targets = Collections.unmodifiableList(parsed);
        this.deadlineMs = env.getProperty("maestro.forward_deadline_ms", Long.class, 1500L);
        this.breakerFailures =
                env.getProperty("maestro.forward_breaker_failures", Integer.class, 3);
        this.breakerCooldownMs =
                1000L * env.getProperty("maestro.forward_breaker_cooldown_s", Long.class, 30L);
        if (!targets.isEmpty()) {
            // WARN, not INFO: this changes where managed-show completions are
            // filed, and an operator reading the log must see it.
            logger.warn("Maestro completion forwarding enabled to " + targets + " (deadline "
                    + deadlineMs + "ms, breaker opens after " + breakerFailures
                    + " consecutive failures for " + (breakerCooldownMs / 1000) + "s)");
        }
    }

    /**
     * Offer one report to the forward relay. Returns a forwarded outcome when the isolated
     * deployment ACKed it; otherwise the caller processes the report through the legacy path,
     * reusing the returned proc when one was read. Never throws: every failure here degrades to the
     * legacy path.
     */
    public Outcome forwardIfManaged(FrameCompleteReport report) {
        if (targets.isEmpty()) {
            return Outcome.notAttempted(null);
        }

        // The proc is read here only to learn the show; on every outcome decided WITHOUT a wire
        // wait it is handed to the legacy path, so those paths never read it twice. An outcome
        // decided after a send attempt deliberately does NOT reuse it: the attempt can last the
        // whole deadline, and the run-ownership fence in processReportNow must judge a fresh
        // snapshot, not one from before the wait (a frame freed and rebooked inside that window
        // would slip past a stale fence and re-open the free-then-rebook cascade).
        VirtualProc proc;
        try {
            proc = hostManager.getVirtualProc(report.getFrame().getResourceId());
        } catch (EmptyResultDataAccessException e) {
            // Unknown proc: the legacy path finalizes the orphan, as it does in every mode.
            return Outcome.notAttempted(null);
        } catch (Exception e) {
            warnRateLimited("reading the report's proc failed; processing locally: " + e);
            return Outcome.notAttempted(null);
        }

        boolean managed;
        try {
            managed = showDao.isSchedulerManaged(proc.getShowId());
        } catch (Exception e) {
            warnRateLimited("reading the show's scheduler flag failed; processing locally: " + e);
            managed = false;
        }
        if (!managed) {
            return Outcome.notAttempted(proc);
        }

        if (System.currentTimeMillis() < openUntil) {
            count("fallback_breaker");
            return Outcome.notAttempted(proc);
        }

        // Half-open: after the cooldown exactly ONE report probes; the rest keep the instant
        // fallback until the probe settles, so a still-down leader never stalls a herd of report
        // threads for a deadline each at every cooldown expiry.
        boolean probing = consecutiveFailures.get() >= breakerFailures;
        if (probing && !probeInFlight.compareAndSet(false, true)) {
            count("fallback_breaker");
            return Outcome.notAttempted(proc);
        }

        // One attempt per report: retrying is the breaker's job across reports, not this report's
        // job. The report must never wait longer than one deadline before its guaranteed local
        // fallback.
        int idx = targetIndex;
        String target = targets.get(idx % targets.size());
        try {
            if (probing) {
                // The outage grew gRPC's exponential connect backoff; without this reset the
                // probe fails instantly against TRANSIENT_FAILURE and actual resumption waits
                // on the backoff (up to minutes), not the configured cooldown.
                ManagedChannel channel = channels.get(target);
                if (channel != null) {
                    channel.resetConnectBackoff();
                }
            }
            send(target, RqdReportRunningFrameCompletionRequest.newBuilder()
                    .setFrameCompleteReport(report).build());
            onForwardSuccess();
            count("forwarded");
            logger.debug("forwarded completion of " + report.getFrame().getFrameName() + " to "
                    + target);
            return Outcome.FORWARDED;
        } catch (Exception e) {
            targetIndex = (idx + 1) % targets.size();
            onForwardFailure(target, e);
            count("fallback_error");
            return Outcome.notAttempted(null);
        } finally {
            if (probing) {
                probeInFlight.set(false);
            }
        }
    }

    /** One forward attempt over gRPC; overridable so tests can stand in for the wire. */
    protected void send(String target, RqdReportRunningFrameCompletionRequest request) {
        RqdReportInterfaceGrpc.newBlockingStub(channel(target))
                .withDeadlineAfter(deadlineMs, TimeUnit.MILLISECONDS)
                .reportRunningFrameCompletion(request);
    }

    private ManagedChannel channel(String target) {
        return channels.computeIfAbsent(target,
                t -> ManagedChannelBuilder.forTarget(t).usePlaintext().build());
    }

    private void onForwardSuccess() {
        if (consecutiveFailures.getAndSet(0) >= breakerFailures) {
            logger.warn("Maestro completion forward breaker closed; forwarding resumed");
        }
        openUntil = 0;
    }

    private void onForwardFailure(String target, Exception e) {
        logger.debug("completion forward to " + target + " failed: " + e);
        int failures = consecutiveFailures.incrementAndGet();
        if (failures >= breakerFailures) {
            boolean wasClosed = System.currentTimeMillis() >= openUntil;
            openUntil = System.currentTimeMillis() + breakerCooldownMs;
            if (wasClosed) {
                logger.warn("Maestro completion forward breaker open after " + failures
                        + " consecutive failures (last target " + target + ": " + e
                        + "); managed-show completions take the local fallback for "
                        + (breakerCooldownMs / 1000) + "s");
            }
        }
    }

    private void count(String outcome) {
        if (prometheusMetrics != null) {
            prometheusMetrics.incrementCompletionForward(outcome);
        }
    }

    /**
     * WARN at most once a minute: these read failures repeat once per report when persistent, and a
     * silent catch would make the relay silently inert with no line explaining why.
     */
    private void warnRateLimited(String message) {
        long now = System.currentTimeMillis();
        if (now - lastWarnMs >= 60_000) {
            lastWarnMs = now;
            logger.warn("Maestro completion forward: " + message);
        } else {
            logger.debug("Maestro completion forward: " + message);
        }
    }

    /** Shut down the per-target channels; called by Spring on context destroy. */
    public void shutdown() {
        for (ManagedChannel channel : channels.values()) {
            channel.shutdown();
        }
    }

    public HostManager getHostManager() {
        return hostManager;
    }

    public void setHostManager(HostManager hostManager) {
        this.hostManager = hostManager;
    }

    public ShowDao getShowDao() {
        return showDao;
    }

    public void setShowDao(ShowDao showDao) {
        this.showDao = showDao;
    }

    public PrometheusMetricsCollector getPrometheusMetrics() {
        return prometheusMetrics;
    }

    public void setPrometheusMetrics(PrometheusMetricsCollector prometheusMetrics) {
        this.prometheusMetrics = prometheusMetrics;
    }
}
