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

package com.imageworks.spcue.test.rqd;

import java.util.concurrent.atomic.AtomicLong;

import org.junit.Test;

import com.imageworks.spcue.rqd.HostLaunchBreaker;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/**
 * Unit tests for {@link HostLaunchBreaker}: the per-host skip that keeps the dispatchers from
 * paying a full RPC deadline on every host report of a host whose launches keep timing out.
 */
public class HostLaunchBreakerTests {

    private final AtomicLong now = new AtomicLong(1_000_000L);
    private final RuntimeException cause = new RuntimeException("DEADLINE_EXCEEDED");

    private HostLaunchBreaker breaker(int failures, long cooldownMs) {
        return new HostLaunchBreaker(failures, cooldownMs, now::get);
    }

    @Test
    public void opensOnlyAfterTheConfiguredConsecutiveFailures() {
        HostLaunchBreaker breaker = breaker(2, 60_000);

        breaker.recordUnknownOutcome("host-a", cause);
        assertFalse("one failure is below the threshold", breaker.isOpen("host-a"));

        breaker.recordUnknownOutcome("host-a", cause);
        assertTrue(breaker.isOpen("host-a"));
        assertFalse("state is per host", breaker.isOpen("host-b"));
    }

    @Test
    public void anAnswerResetsTheCount() {
        HostLaunchBreaker breaker = breaker(2, 60_000);

        breaker.recordUnknownOutcome("host-a", cause);
        breaker.recordAnswered("host-a");
        breaker.recordUnknownOutcome("host-a", cause);

        assertFalse("failures were not consecutive", breaker.isOpen("host-a"));
        assertEquals(1, breaker.trackedHosts());
    }

    @Test
    public void closesAfterTheCooldownAndReopensOnTheNextUnknownOutcome() {
        HostLaunchBreaker breaker = breaker(1, 60_000);

        breaker.recordUnknownOutcome("host-a", cause);
        assertTrue(breaker.isOpen("host-a"));

        now.addAndGet(59_999);
        assertTrue(breaker.isOpen("host-a"));
        now.addAndGet(1);
        assertFalse("cooldown elapsed: the next launch probes the host", breaker.isOpen("host-a"));

        // The probe fails again: straight back to open for a full cooldown.
        breaker.recordUnknownOutcome("host-a", cause);
        assertTrue(breaker.isOpen("host-a"));
        now.addAndGet(59_999);
        assertTrue(breaker.isOpen("host-a"));

        // The probe succeeds: closed and forgotten.
        breaker.recordAnswered("host-a");
        assertFalse(breaker.isOpen("host-a"));
        assertEquals(0, breaker.trackedHosts());
    }

    @Test
    public void aFailureWhileOpenExtendsTheCooldown() {
        HostLaunchBreaker breaker = breaker(1, 60_000);

        breaker.recordUnknownOutcome("host-a", cause);
        now.addAndGet(30_000);
        breaker.recordUnknownOutcome("host-a", cause);
        now.addAndGet(30_001);

        assertTrue("open until 60s after the latest failure", breaker.isOpen("host-a"));
    }

    @Test
    public void zeroThresholdOrCooldownDisablesTheBreaker() {
        HostLaunchBreaker noThreshold = breaker(0, 60_000);
        noThreshold.recordUnknownOutcome("host-a", cause);
        assertFalse(noThreshold.isEnabled());
        assertFalse(noThreshold.isOpen("host-a"));
        assertEquals("a disabled breaker tracks nothing", 0, noThreshold.trackedHosts());

        HostLaunchBreaker noCooldown = breaker(1, 0);
        noCooldown.recordUnknownOutcome("host-a", cause);
        assertFalse(noCooldown.isEnabled());
        assertFalse(noCooldown.isOpen("host-a"));
    }
}
