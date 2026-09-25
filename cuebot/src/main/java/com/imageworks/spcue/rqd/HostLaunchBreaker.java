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

package com.imageworks.spcue.rqd;

import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.LongSupplier;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

/**
 * Per-host circuit breaker for frame launches.
 *
 * A launch whose RPC ends with an unknown outcome (deadline expired, connection dropped) costs a
 * dispatcher thread the full RPC deadline and leaves a booking to be confirmed. A host that keeps
 * answering that way is not going to take the next launch either, yet every host report it sends
 * re-queues it for booking. Once a host accumulates {@code failureThreshold} consecutive
 * unknown-outcome launches the breaker opens for {@code cooldownMs}: the dispatchers skip the host
 * without booking anything on it. After the cooldown the next launch goes through as a probe; a
 * success closes the breaker, another unknown outcome re-opens it for a further cooldown.
 *
 * Only launches feed the breaker. Kills and status polls keep going to the host regardless, since
 * they resolve bookings that already exist.
 *
 * State is approximate by design: concurrent launches may all probe a half-open host, and a success
 * landing after a failure may reset a count early. Neither can double-book; the breaker only
 * decides whether a host is offered new work.
 */
public final class HostLaunchBreaker {
    private static final Logger logger = LogManager.getLogger(HostLaunchBreaker.class);

    private static final class HostState {
        final AtomicInteger consecutiveFailures = new AtomicInteger();
        volatile long openUntil = 0;
    }

    private final int failureThreshold;
    private final long cooldownMs;
    private final LongSupplier clock;
    private final ConcurrentHashMap<String, HostState> hosts = new ConcurrentHashMap<>();

    /**
     * @param failureThreshold consecutive unknown-outcome launches that open the breaker; zero or
     *        negative disables it
     * @param cooldownMs how long an open breaker skips the host; zero or negative disables it
     */
    public HostLaunchBreaker(int failureThreshold, long cooldownMs) {
        this(failureThreshold, cooldownMs, System::currentTimeMillis);
    }

    /** Test hook: same as above with an injectable clock (milliseconds). */
    public HostLaunchBreaker(int failureThreshold, long cooldownMs, LongSupplier clock) {
        this.failureThreshold = failureThreshold;
        this.cooldownMs = cooldownMs;
        this.clock = clock;
    }

    public boolean isEnabled() {
        return failureThreshold > 0 && cooldownMs > 0;
    }

    /** True while launches to this host should be skipped. */
    public boolean isOpen(String host) {
        if (!isEnabled()) {
            return false;
        }
        HostState state = hosts.get(host);
        return state != null && clock.getAsLong() < state.openUntil;
    }

    /** The host answered a launch (accepted or refused it): close the breaker. */
    public void recordAnswered(String host) {
        HostState state = hosts.remove(host);
        if (state != null && state.consecutiveFailures.get() >= failureThreshold) {
            logger.warn("launch breaker closed for " + host + "; launches resumed");
        }
    }

    /** A launch to the host ended without an answer. */
    public void recordUnknownOutcome(String host, Exception cause) {
        if (!isEnabled()) {
            return;
        }
        HostState state = hosts.computeIfAbsent(host, h -> new HostState());
        int failures = state.consecutiveFailures.incrementAndGet();
        if (failures < failureThreshold) {
            return;
        }
        long now = clock.getAsLong();
        boolean wasClosed = now >= state.openUntil;
        state.openUntil = now + cooldownMs;
        if (wasClosed) {
            logger.warn("launch breaker open for " + host + " after " + failures
                    + " consecutive launches with unknown outcome (last: " + cause
                    + "); skipping it for " + (cooldownMs / 1000) + "s");
        }
    }

    /** Number of hosts currently tracked (open or accumulating failures). */
    public int trackedHosts() {
        return hosts.size();
    }
}
