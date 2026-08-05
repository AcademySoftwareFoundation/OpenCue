
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

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowCallbackHandler;
import org.springframework.mock.env.MockEnvironment;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * Unit tests for {@link LicenseSource#describe}, the read-only view behind the CueGUI Licenses
 * widget: poller state, the full cached sample sorted by name, per-license headroom resolution, and
 * this cluster's own running usage (all running licensed frames, not the in-flight window).
 *
 * Same harness as {@link LicenseSourceInFlightTests}: the provider sample comes from a temp JSON
 * file behind a script provider, the database rows from a stubbed JdbcTemplate.
 */
public class LicenseSourceDescribeTests {

    private Path dir;
    private Path json;

    @Before
    public void setUp() throws IOException {
        dir = Files.createTempDirectory("licdescribe");
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

    /**
     * Rows for the running-use query: {lic csv, host}. Replayed through the RowCallbackHandler
     * exactly as the database would.
     */
    private static JdbcTemplate jdbcReturning(Object[][] rows) {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        doAnswer(invocation -> {
            RowCallbackHandler handler = invocation.getArgument(1);
            for (Object[] row : rows) {
                ResultSet rs = mock(ResultSet.class);
                when(rs.getString("lic")).thenReturn((String) row[0]);
                when(rs.getString("host")).thenReturn((String) row[1]);
                handler.processRow(rs);
            }
            return null;
        }).when(jdbc).query(anyString(), any(RowCallbackHandler.class), any());
        return jdbc;
    }

    @Test
    public void unconfiguredSourceDescribesItselfHonestly() {
        MockEnvironment env = new MockEnvironment();
        LicenseSource ls = new LicenseSource(env, mock(JdbcTemplate.class));
        LicenseSource.SourceStatus status = ls.describe();
        assertFalse(status.configured);
        assertFalse(status.hasSample);
        assertTrue("no provider means nothing actionable", status.stale);
        assertEquals(0, status.ageSeconds);
        assertTrue(status.licenses.isEmpty());
        assertEquals("CUE_LICENSES", status.envKey);
    }

    @Test
    public void configuredButUnpolledReportsNoSample() {
        MockEnvironment env = new MockEnvironment();
        env.setProperty("scheduler.license.provider", "script:cat " + json);
        env.setProperty("scheduler.license.poll_seconds", "45");
        env.setProperty("scheduler.license.stale_seconds", "120");
        LicenseSource ls = new LicenseSource(env, mock(JdbcTemplate.class));
        LicenseSource.SourceStatus status = ls.describe();
        assertTrue(status.configured);
        assertEquals("script:cat " + json, status.provider);
        assertEquals(45, status.pollSeconds);
        assertEquals(120, status.staleSeconds);
        assertFalse(status.hasSample);
        assertTrue(status.stale);
        assertTrue(status.licenses.isEmpty());
    }

    @Test
    public void describeReportsSampleHeadroomAndRunningUsage() throws IOException {
        writeJson("{\"queried_at\": " + nowSec() + ", \"licenses\": ["
                + "{\"name\": \"Maya\", \"feature\": \"Maya Batch\", \"total\": 10, "
                + "\"available\": 5}," + "{\"name\": \"hengine\", \"total\": 8, \"available\": 2, "
                + "\"host_based\": true, \"hosts\": [{\"host\": \"WS9\", \"count\": 1}]}]}");
        MockEnvironment env = new MockEnvironment();
        env.setProperty("scheduler.license.provider", "script:cat " + json);
        env.setProperty("scheduler.license.timeout_seconds", "5");
        env.setProperty("scheduler.license.headroom.maya", "2");
        LicenseSource ls = new LicenseSource(env, jdbcReturning(new Object[][] {
                // Three maya frames on two hosts; host case must normalize.
                {"maya", "H1", null}, {"maya", "h1", null}, {"maya", "h2", null},
                // One hengine frame; csv declaration covers both pools.
                {"hengine,maya", "h3", null},
                // A license outside the sample must not invent a row.
                {"katana", "h4", null},}));
        ls.poll();

        LicenseSource.SourceStatus status = ls.describe();
        assertTrue(status.configured);
        assertTrue(status.hasSample);
        assertFalse(status.stale);
        assertTrue("fresh sample age", status.ageSeconds < 60);
        assertEquals("sorted by name", 2, status.licenses.size());

        LicenseSource.LicenseInfo hengine = status.licenses.get(0);
        assertEquals("hengine", hengine.state.name);
        assertEquals("feature falls back to the name", "hengine", hengine.state.feature);
        assertTrue(hengine.state.hostBased);
        assertEquals(8, hengine.state.total);
        assertEquals(2, hengine.state.available);
        assertEquals("provider host list is counted", 1, hengine.state.hosts.size());
        assertEquals("default headroom", 0, hengine.headroom);
        assertEquals(1, hengine.runningFrames);
        assertEquals(1, hengine.runningHosts);

        LicenseSource.LicenseInfo maya = status.licenses.get(1);
        assertEquals("maya", maya.state.name);
        assertEquals("Maya Batch", maya.state.feature);
        assertFalse(maya.state.hostBased);
        assertEquals("per-license headroom read from properties", 2, maya.headroom);
        assertEquals("three plain rows plus the csv row", 4, maya.runningFrames);
        assertEquals("H1/h1 collapse to one host; h2 and h3 add two", 3, maya.runningHosts);
    }

    @Test
    public void describeRedactsHttpCredentials() {
        MockEnvironment env = new MockEnvironment();
        env.setProperty("scheduler.license.provider",
                "http://svc:hunter2@lic-reporter:9101/licenses?token=abc&site=main");
        LicenseSource ls = new LicenseSource(env, mock(JdbcTemplate.class));
        assertEquals("userinfo and query values must not reach the wire",
                "http://lic-reporter:9101/licenses?token=****&site=****", ls.describe().provider);
    }

    @Test
    public void describeLeavesPlainProvidersAlone() {
        assertEquals("http://lic:9101/licenses",
                LicenseSource.redactProvider("http://lic:9101/licenses"));
        assertEquals("an @ past the path is not userinfo", "http://lic:9101/licenses/a@b",
                LicenseSource.redactProvider("http://lic:9101/licenses/a@b"));
        assertEquals("script command lines are shown as configured",
                "script:/site/bin/cue_licenses.sh --token abc",
                LicenseSource.redactProvider("script:/site/bin/cue_licenses.sh --token abc"));
    }

    @Test
    public void redactionSurvivesHostileUrlShapes() {
        assertEquals("a raw @ in the password must not leak its tail", "http://host/licenses",
                LicenseSource.redactProvider("http://user:p@ss@host/licenses"));
        assertEquals("an @ inside the query of a path-less URL is not userinfo",
                "http://host?email=****",
                LicenseSource.redactProvider("http://host?email=a@b.com"));
    }

    @Test
    public void staleSampleStillListsLicenses() throws IOException {
        // The whole point of the view is seeing what the poller knows, so a
        // stale sample keeps its licenses visible and only the flag flips --
        // an operator debugging a dead provider needs the last numbers, not
        // an empty table.
        writeJson("{\"queried_at\": " + (nowSec() - 1000) + ", \"licenses\": ["
                + "{\"name\": \"maya\", \"total\": 10, \"available\": 5}]}");
        MockEnvironment env = new MockEnvironment();
        env.setProperty("scheduler.license.provider", "script:cat " + json);
        env.setProperty("scheduler.license.timeout_seconds", "5");
        env.setProperty("scheduler.license.stale_seconds", "300");
        LicenseSource ls = new LicenseSource(env, jdbcReturning(new Object[][] {}));
        ls.poll();

        LicenseSource.SourceStatus status = ls.describe();
        assertTrue(status.hasSample);
        assertTrue("1000s old against a 300s threshold", status.stale);
        assertTrue(status.ageSeconds >= 1000);
        assertEquals(1, status.licenses.size());
        assertEquals("maya", status.licenses.get(0).state.name);
    }
}
