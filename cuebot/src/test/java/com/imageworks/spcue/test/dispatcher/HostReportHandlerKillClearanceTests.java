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

import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

import com.google.common.base.Ticker;
import com.google.common.cache.Cache;
import com.google.common.cache.CacheBuilder;
import org.junit.Before;
import org.junit.Test;
import org.springframework.core.env.Environment;
import org.springframework.test.util.ReflectionTestUtils;

import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.HostReportHandler;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * Unit tests for {@link HostReportHandler}'s kill-clearance counter.
 *
 * The counter bounds how many kill requests are sent for a host+frame pair before backing off. A
 * still-running (zombie) frame is re-detected on every host report, so a denied attempt must not
 * refresh the cache entry's expireAfterWrite clock: doing so would keep the entry alive forever and
 * permanently disable the kill after one exhausted burst, leaving a double-booked render running to
 * completion. These tests pin the cooldown behavior with a fake ticker.
 */
public class HostReportHandlerKillClearanceTests {

    private static final int RETRY_LIMIT = 3;
    private static final long EXPIRE_MINUTES = 3;

    private HostReportHandler handler;
    private AtomicLong fakeTimeNanos;

    private static class FakeTicker extends Ticker {
        private final AtomicLong nanos;

        FakeTicker(AtomicLong nanos) {
            this.nanos = nanos;
        }

        @Override
        public long read() {
            return nanos.get();
        }
    }

    @Before
    public void setup() {
        handler = new HostReportHandler();

        Environment env = mock(Environment.class);
        when(env.getRequiredProperty(eq("dispatcher.frame_kill_retry_limit"), eq(Integer.class)))
                .thenReturn(RETRY_LIMIT);
        ReflectionTestUtils.setField(handler, "env", env);

        // Test mode skips the prometheus/jobManager lookups on the give-up branch.
        Dispatcher dispatcher = mock(Dispatcher.class);
        when(dispatcher.isTestMode()).thenReturn(true);
        handler.setDispatcher(dispatcher);

        fakeTimeNanos = new AtomicLong(0);
        Cache<String, Long> cache =
                CacheBuilder.newBuilder().expireAfterWrite(EXPIRE_MINUTES, TimeUnit.MINUTES)
                        .ticker(new FakeTicker(fakeTimeNanos)).build();
        ReflectionTestUtils.setField(handler, "killRequestCounterCache", cache);
    }

    private boolean getKillClearance() {
        return ReflectionTestUtils.invokeMethod(handler, "getKillClearance", "host01",
                "00000000-0000-0000-0000-0000000000f1");
    }

    private void advanceMinutes(long minutes) {
        fakeTimeNanos.addAndGet(TimeUnit.MINUTES.toNanos(minutes));
    }

    @Test
    public void testClearanceGrantedUpToRetryLimit() {
        for (int i = 0; i < RETRY_LIMIT; i++) {
            assertTrue("attempt " + (i + 1) + " should be granted", getKillClearance());
        }
        assertFalse("attempt past the limit should be denied", getKillClearance());
    }

    @Test
    public void testDeniedAttemptsDoNotRefreshTheCooldown() {
        for (int i = 0; i < RETRY_LIMIT; i++) {
            assertTrue(getKillClearance());
        }

        // A zombie frame keeps being re-detected: repeated denied attempts inside the expiry
        // window must not push the entry's expiry forward.
        assertFalse(getKillClearance());
        advanceMinutes(EXPIRE_MINUTES - 1);
        assertFalse("still inside the cooldown", getKillClearance());

        // One more minute puts us past expiry measured from the LAST GRANTED attempt. If denied
        // attempts had refreshed the clock the entry would still be alive here and the kill
        // would stay disabled forever.
        advanceMinutes(1);
        assertTrue("cooldown elapsed, kills must resume", getKillClearance());
    }

    @Test
    public void testBudgetResetsAfterCooldown() {
        for (int i = 0; i < RETRY_LIMIT; i++) {
            assertTrue(getKillClearance());
        }
        assertFalse(getKillClearance());

        advanceMinutes(EXPIRE_MINUTES);

        // A full fresh budget is available after the cooldown.
        for (int i = 0; i < RETRY_LIMIT; i++) {
            assertTrue("post-cooldown attempt " + (i + 1) + " should be granted",
                    getKillClearance());
        }
        assertFalse(getKillClearance());
    }

    @Test
    public void testIndependentCountersPerHostFramePair() {
        for (int i = 0; i < RETRY_LIMIT; i++) {
            assertTrue(getKillClearance());
        }
        assertFalse(getKillClearance());

        // A different frame on the same host has its own budget.
        assertTrue((boolean) ReflectionTestUtils.invokeMethod(handler, "getKillClearance", "host01",
                "00000000-0000-0000-0000-0000000000f2"));
    }
}
