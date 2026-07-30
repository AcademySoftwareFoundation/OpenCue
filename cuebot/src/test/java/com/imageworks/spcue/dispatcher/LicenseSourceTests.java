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

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collections;
import java.util.Map;
import java.util.Set;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.mockito.Mockito;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.mock.env.MockEnvironment;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/**
 * Unit tests for {@link LicenseSource}'s provider contract: timestamp validation (a sample without
 * a usable {@code queried_at} must be rejected, not treated as fresh), staleness, headroom,
 * counts-only seat capping, and the script provider's stderr handling (a chatty script must not
 * wedge on a full stderr pipe). No Spring context and no database: the JdbcTemplate is a mock whose
 * queries return nothing, so in-flight counts are zero. The test lives in the dispatcher package to
 * reach the package-private {@code poll()}.
 */
public class LicenseSourceTests {

    private Path dir;
    private Path json;
    private Path script;

    @Before
    public void setUp() throws IOException {
        dir = Files.createTempDirectory("licsrc");
        json = dir.resolve("resp.json");
    }

    @After
    public void tearDown() throws IOException {
        if (dir != null) {
            Files.walk(dir).sorted(java.util.Comparator.reverseOrder()).forEach(p -> {
                try {
                    Files.delete(p);
                } catch (IOException e) {
                    // best effort
                }
            });
        }
    }

    /** A LicenseSource reading the temp JSON file through the script provider. */
    private LicenseSource source(String... extraProps) {
        MockEnvironment env = new MockEnvironment();
        env.setProperty("scheduler.license.provider", "script:cat " + json);
        env.setProperty("scheduler.license.timeout_seconds", "5");
        env.setProperty("scheduler.license.stale_seconds", "300");
        for (int i = 0; i + 1 < extraProps.length; i += 2) {
            env.setProperty(extraProps[i], extraProps[i + 1]);
        }
        JdbcTemplate jdbc = Mockito.mock(JdbcTemplate.class);
        return new LicenseSource(env, jdbc);
    }

    private void writeJson(String body) throws IOException {
        Files.write(json, body.getBytes(StandardCharsets.UTF_8));
    }

    private static String mayaJson(long queriedAt, int total, int available) {
        String ts = (queriedAt == Long.MIN_VALUE) ? "" : "\"queried_at\": " + queriedAt + ", ";
        return "{" + ts + "\"licenses\": [{\"name\": \"maya\", \"total\": " + total
                + ", \"available\": " + available + "}]}";
    }

    private static long nowSec() {
        return System.currentTimeMillis() / 1000L;
    }

    private static final Set<String> MAYA = Collections.singleton("maya");

    // ---- queried_at validation --------------------------------------------

    @Test
    public void validTimestampAccepted() throws IOException {
        writeJson(mayaJson(nowSec(), 10, 5));
        LicenseSource ls = source();
        ls.poll();
        LicenseSource.LicenseBudget b = ls.snapshotBudgets(MAYA).get("maya");
        assertFalse("fresh sample must not be stale", b.stale);
        assertEquals(5, b.usable);
    }

    @Test
    public void missingTimestampRejected() throws IOException {
        writeJson(mayaJson(Long.MIN_VALUE, 10, 5));
        LicenseSource ls = source();
        ls.poll();
        assertTrue("sample without queried_at must be held",
                ls.snapshotBudgets(MAYA).get("maya").stale);
    }

    @Test
    public void zeroTimestampRejected() throws IOException {
        writeJson(mayaJson(0, 10, 5));
        LicenseSource ls = source();
        ls.poll();
        assertTrue(ls.snapshotBudgets(MAYA).get("maya").stale);
    }

    @Test
    public void negativeTimestampRejected() throws IOException {
        writeJson(mayaJson(-42, 10, 5));
        LicenseSource ls = source();
        ls.poll();
        assertTrue(ls.snapshotBudgets(MAYA).get("maya").stale);
    }

    @Test
    public void futureTimestampClampedToFresh() throws IOException {
        writeJson(mayaJson(nowSec() + 120, 10, 5));
        LicenseSource ls = source();
        ls.poll();
        assertFalse("a provider clock running ahead is clamped, not rejected",
                ls.snapshotBudgets(MAYA).get("maya").stale);
    }

    @Test
    public void oldTimestampIsStaleOnArrival() throws IOException {
        writeJson(mayaJson(nowSec() - 400, 10, 5));
        LicenseSource ls = source(); // stale_seconds=300
        ls.poll();
        assertTrue("lagging sample must arrive already stale",
                ls.snapshotBudgets(MAYA).get("maya").stale);
    }

    @Test
    public void rejectedPollKeepsPreviousSample() throws IOException {
        writeJson(mayaJson(nowSec(), 10, 5));
        LicenseSource ls = source();
        ls.poll();
        // Provider degrades: same numbers, no timestamp. The poll is rejected
        // and the previous (still young) sample keeps serving.
        writeJson(mayaJson(Long.MIN_VALUE, 10, 1));
        ls.poll();
        LicenseSource.LicenseBudget b = ls.snapshotBudgets(MAYA).get("maya");
        assertFalse(b.stale);
        assertEquals("previous sample's numbers must survive the rejected poll", 5, b.usable);
    }

    // ---- budgets ----------------------------------------------------------

    @Test
    public void headroomSubtracted() throws IOException {
        writeJson(mayaJson(nowSec(), 10, 10));
        LicenseSource ls = source("scheduler.license.headroom.maya", "4");
        ls.poll();
        assertEquals(6, ls.snapshotBudgets(MAYA).get("maya").usable);
    }

    @Test
    public void unknownLicenseHeld() throws IOException {
        writeJson(mayaJson(nowSec(), 10, 5));
        LicenseSource ls = source();
        ls.poll();
        Map<String, LicenseSource.LicenseBudget> out =
                ls.snapshotBudgets(Collections.singleton("katana"));
        assertTrue("a license the provider does not report must be held", out.get("katana").stale);
    }

    @Test
    public void noProviderHoldsEverything() {
        MockEnvironment env = new MockEnvironment();
        env.setProperty("scheduler.license.provider", " ");
        LicenseSource ls = new LicenseSource(env, Mockito.mock(JdbcTemplate.class));
        assertFalse(ls.hasProvider());
        assertTrue(ls.snapshotBudgets(MAYA).get("maya").stale);
    }

    @Test
    public void countsOnlyHostBasedCapBoundedByAvailable() throws IOException {
        // host_based without a hosts list (the sesictrl case): the seat cap
        // must be bounded via `available`, never total - headroom.
        writeJson("{\"queried_at\": " + nowSec() + ", \"licenses\": [{\"name\": \"hengine\", "
                + "\"total\": 8, \"available\": 3, \"host_based\": true}]}");
        LicenseSource ls = source();
        ls.poll();
        LicenseSource.LicenseBudget b =
                ls.snapshotBudgets(Collections.singleton("hengine")).get("hengine");
        assertFalse(b.stale);
        assertTrue(b.hostBased);
        assertEquals("no seats reported, no in-flight: cap = available", 3, b.seatCap);
    }

    // ---- script provider robustness ---------------------------------------

    @Test
    public void chattyStderrDoesNotWedgeTheScript() throws IOException {
        // 200KB of stderr, far over the ~64KB pipe buffer: without a stderr
        // drain the script blocks mid-write and times out.
        writeJson(mayaJson(nowSec(), 10, 5));
        script = dir.resolve("chatty.sh");
        Files.write(script, ("#!/bin/sh\n" + "head -c 200000 /dev/zero | tr '\\0' 'e' 1>&2\n"
                + "cat " + json + "\n").getBytes(StandardCharsets.UTF_8));
        MockEnvironment env = new MockEnvironment();
        env.setProperty("scheduler.license.provider", "script:sh " + script);
        env.setProperty("scheduler.license.timeout_seconds", "5");
        LicenseSource ls = new LicenseSource(env, Mockito.mock(JdbcTemplate.class));
        ls.poll();
        assertFalse("valid stdout must win despite a flooded stderr",
                ls.snapshotBudgets(MAYA).get("maya").stale);
    }

    @Test
    public void failingScriptHoldsLicenses() throws IOException {
        script = dir.resolve("fail.sh");
        Files.write(script, ("#!/bin/sh\n" + "echo 'vendor said no' 1>&2\n" + "exit 3\n")
                .getBytes(StandardCharsets.UTF_8));
        MockEnvironment env = new MockEnvironment();
        env.setProperty("scheduler.license.provider", "script:sh " + script);
        env.setProperty("scheduler.license.timeout_seconds", "5");
        LicenseSource ls = new LicenseSource(env, Mockito.mock(JdbcTemplate.class));
        ls.poll();
        assertTrue(ls.snapshotBudgets(MAYA).get("maya").stale);
    }
}
