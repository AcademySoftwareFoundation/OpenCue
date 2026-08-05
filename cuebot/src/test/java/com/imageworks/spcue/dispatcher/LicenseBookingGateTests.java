
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
import java.sql.ResultSet;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.mockito.Mockito;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowCallbackHandler;
import org.springframework.mock.env.MockEnvironment;

import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.grpc.report.RunningFrameInfo;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * Unit tests for {@link LicenseBookingGate}: the per-pass booking session (floating seats consumed
 * per frame, host-based seats free on seated hosts and capped on fresh ones, fail closed on
 * stale/unknown/no-provider) and the packing helpers. No Spring context and no database: the
 * LicenseSource reads a temp JSON file through the script provider (as in
 * {@link LicenseSourceTests}) and layer license declarations are stubbed.
 */
public class LicenseBookingGateTests {

    private Path dir;
    private Path json;

    @Before
    public void setUp() throws IOException {
        dir = Files.createTempDirectory("licgate");
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

    private void writeJson(String body) throws IOException {
        Files.write(json, body.getBytes(StandardCharsets.UTF_8));
    }

    private static long nowSec() {
        return System.currentTimeMillis() / 1000L;
    }

    /** A polled LicenseSource reading the temp JSON file through the script provider. */
    private LicenseSource polledSource() {
        MockEnvironment env = new MockEnvironment();
        env.setProperty("scheduler.license.provider", "script:cat " + json);
        env.setProperty("scheduler.license.timeout_seconds", "5");
        env.setProperty("scheduler.license.stale_seconds", "300");
        LicenseSource ls = new LicenseSource(env, Mockito.mock(JdbcTemplate.class));
        ls.poll();
        return ls;
    }

    /** A LicenseSource with no provider configured at all. */
    private LicenseSource noProviderSource() {
        MockEnvironment env = new MockEnvironment();
        env.setProperty("scheduler.license.provider", "");
        return new LicenseSource(env, Mockito.mock(JdbcTemplate.class));
    }

    /** A gate whose layer license declarations come from a map instead of the database. */
    private static final class TestGate extends LicenseBookingGate {
        private final Map<String, List<String>> layers;

        TestGate(LicenseSource licenseSource, Map<String, List<String>> layers) {
            super(Mockito.mock(JdbcTemplate.class), licenseSource);
            this.layers = layers;
        }

        @Override
        public List<String> licensesForLayer(String layerId) {
            return layers.getOrDefault(layerId, Collections.emptyList());
        }
    }

    private static Map<String, List<String>> layers(Object... pairs) {
        Map<String, List<String>> out = new HashMap<>();
        for (int i = 0; i + 1 < pairs.length; i += 2) {
            @SuppressWarnings("unchecked")
            List<String> names = (List<String>) pairs[i + 1];
            out.put((String) pairs[i], names);
        }
        return out;
    }

    // ---- session: floating ------------------------------------------------

    @Test
    public void unlicensedLayerAlwaysBookable() {
        TestGate gate = new TestGate(noProviderSource(), layers());
        assertTrue(gate.newSession("host1").canBook("layer-plain"));
    }

    @Test
    public void licensedLayerHeldWithoutProvider() {
        TestGate gate = new TestGate(noProviderSource(), layers("l1", Arrays.asList("maya")));
        assertFalse(gate.newSession("host1").canBook("l1"));
    }

    @Test
    public void floatingSeatsConsumedPerBookedFrame() throws IOException {
        writeJson("{\"queried_at\": " + nowSec() + ", \"licenses\": ["
                + "{\"name\": \"maya\", \"total\": 10, \"available\": 2}]}");
        TestGate gate = new TestGate(polledSource(), layers("l1", Arrays.asList("maya")));
        LicenseBookingGate.Session session = gate.newSession("host1");
        assertTrue(session.canBook("l1"));
        session.booked("l1");
        assertTrue(session.canBook("l1"));
        session.booked("l1");
        assertFalse("both free seats are spent within the pass", session.canBook("l1"));
    }

    @Test
    public void multiPoolLayerNeedsEveryPool() throws IOException {
        writeJson("{\"queried_at\": " + nowSec() + ", \"licenses\": ["
                + "{\"name\": \"maya\", \"total\": 10, \"available\": 5}, "
                + "{\"name\": \"katana\", \"total\": 10, \"available\": 0}]}");
        TestGate gate = new TestGate(polledSource(), layers("both", Arrays.asList("maya", "katana"),
                "just-maya", Arrays.asList("maya")));
        LicenseBookingGate.Session session = gate.newSession("host1");
        assertFalse("one empty pool holds the layer", session.canBook("both"));
        assertTrue(session.canBook("just-maya"));
    }

    @Test
    public void unknownLicenseHeld() throws IOException {
        writeJson("{\"queried_at\": " + nowSec() + ", \"licenses\": ["
                + "{\"name\": \"maya\", \"total\": 10, \"available\": 5}]}");
        TestGate gate = new TestGate(polledSource(), layers("l1", Arrays.asList("katana")));
        assertFalse(gate.newSession("host1").canBook("l1"));
    }

    @Test
    public void staleSampleHolds() throws IOException {
        writeJson("{\"queried_at\": " + (nowSec() - 400) + ", \"licenses\": ["
                + "{\"name\": \"maya\", \"total\": 10, \"available\": 5}]}");
        TestGate gate = new TestGate(polledSource(), layers("l1", Arrays.asList("maya")));
        assertFalse(gate.newSession("host1").canBook("l1"));
    }

    // ---- session: host-based ----------------------------------------------

    @Test
    public void hostBasedFreeOnSeatedHost() throws IOException {
        // No seats available, but wolf1018 already holds one: frames there are free.
        writeJson("{\"queried_at\": " + nowSec() + ", \"licenses\": ["
                + "{\"name\": \"hengine\", \"total\": 8, \"available\": 0, "
                + "\"host_based\": true, \"hosts\": [{\"host\": \"wolf1018\", \"count\": 1}]}]}");
        TestGate gate = new TestGate(polledSource(), layers("l1", Arrays.asList("hengine")));
        assertTrue(gate.newSession("wolf1018").canBook("l1"));
        assertTrue("host name comparison must be case insensitive",
                gate.newSession("WOLF1018").canBook("l1"));
        assertFalse("a fresh host would need a seat that does not exist",
                gate.newSession("wolf2000").canBook("l1"));
    }

    @Test
    public void hostBasedNewSeatAllowedWithinCap() throws IOException {
        writeJson("{\"queried_at\": " + nowSec() + ", \"licenses\": ["
                + "{\"name\": \"hengine\", \"total\": 8, \"available\": 1, "
                + "\"host_based\": true, \"hosts\": [{\"host\": \"h1\", \"count\": 1}]}]}");
        TestGate gate = new TestGate(polledSource(), layers("l1", Arrays.asList("hengine")));
        LicenseBookingGate.Session session = gate.newSession("h2");
        assertTrue("one seat is free, h2 may take it", session.canBook("l1"));
        session.booked("l1");
        assertTrue("h2 is now seated, further frames are free", session.canBook("l1"));
    }

    @Test
    public void hostBasedSeatCapExhausted() throws IOException {
        writeJson("{\"queried_at\": " + nowSec() + ", \"licenses\": ["
                + "{\"name\": \"hengine\", \"total\": 2, \"available\": 0, "
                + "\"host_based\": true, \"hosts\": ["
                + "{\"host\": \"h1\", \"count\": 1}, {\"host\": \"h2\", \"count\": 1}]}]}");
        TestGate gate = new TestGate(polledSource(), layers("l1", Arrays.asList("hengine")));
        assertFalse(gate.newSession("h3").canBook("l1"));
        assertTrue(gate.newSession("h1").canBook("l1"));
    }

    // ---- packing helpers ----------------------------------------------------

    @Test
    public void hostBasedLicensesRunningPicksOnlyHostBased() throws IOException {
        writeJson("{\"queried_at\": " + nowSec() + ", \"licenses\": ["
                + "{\"name\": \"hengine\", \"total\": 8, \"available\": 2, \"host_based\": true}, "
                + "{\"name\": \"maya\", \"total\": 10, \"available\": 5}]}");
        TestGate gate = new TestGate(polledSource(),
                layers("l-hengine", Arrays.asList("hengine"), "l-maya", Arrays.asList("maya")));
        List<RunningFrameInfo> running =
                Arrays.asList(RunningFrameInfo.newBuilder().setLayerId("l-hengine").build(),
                        RunningFrameInfo.newBuilder().setLayerId("l-maya").build(),
                        RunningFrameInfo.newBuilder().setLayerId("l-plain").build());
        assertEquals(Collections.singleton("hengine"), gate.hostBasedLicensesRunning(running));
    }

    @Test
    public void hostBasedLicensesRunningEmptyWithoutProvider() {
        TestGate gate = new TestGate(noProviderSource(), layers("l1", Arrays.asList("hengine")));
        assertTrue(gate
                .hostBasedLicensesRunning(
                        Arrays.asList(RunningFrameInfo.newBuilder().setLayerId("l1").build()))
                .isEmpty());
    }

    @Test
    public void hostBasedLicensesRunningEmptyForUnlicensedFrames() throws IOException {
        writeJson("{\"queried_at\": " + nowSec() + ", \"licenses\": ["
                + "{\"name\": \"hengine\", \"total\": 8, \"available\": 2, \"host_based\": true}]}");
        TestGate gate = new TestGate(polledSource(), layers());
        assertTrue(gate
                .hostBasedLicensesRunning(
                        Arrays.asList(RunningFrameInfo.newBuilder().setLayerId("l-plain").build()))
                .isEmpty());
    }

    @Test
    public void findPackableJobsFiltersOsAndLicenseAndDedupes() throws Exception {
        // Rows the packing query would return, highest priority first.
        Object[][] rows = {
                // matches: wants hengine, no os restriction
                {"job1", "", "hengine,katana"},
                // skipped: wrong os
                {"job2", "Windows", "hengine"},
                // skipped: needs a license this host does not hold
                {"job3", "linux", "maya"},
                // duplicate of job1 via a second licensed layer
                {"job1", "", "hengine"},
                // matches: os fits, case-insensitive license match
                {"job4", "linux", "HEngine"},};

        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        doAnswer(invocation -> {
            RowCallbackHandler handler = invocation.getArgument(1);
            for (Object[] row : rows) {
                ResultSet rs = mock(ResultSet.class);
                when(rs.getString("pk_job")).thenReturn((String) row[0]);
                when(rs.getString("str_os")).thenReturn((String) row[1]);
                when(rs.getString("str_value")).thenReturn((String) row[2]);
                handler.processRow(rs);
            }
            return null;
        }).when(jdbc).query(anyString(), any(RowCallbackHandler.class), any(), any());

        LicenseBookingGate gate = new LicenseBookingGate(jdbc, noProviderSource());
        DispatchHost host = new DispatchHost();
        host.facilityId = "facility1";
        host.setOs("linux");

        Set<String> licenses = new HashSet<>(Arrays.asList("hengine"));
        assertEquals(Arrays.asList("job1", "job4"), gate.findPackableJobs(licenses, host, 5));
        assertEquals("the limit must cap the result", Arrays.asList("job1"),
                gate.findPackableJobs(licenses, host, 1));
    }
}
