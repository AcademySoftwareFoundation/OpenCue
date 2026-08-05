
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
import java.util.Collections;

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
 * Unit tests for {@link LicenseSource}'s in-flight correction ({@code readInFlight}), exercised
 * through {@link LicenseSource#snapshotBudgets}: recently started licensed frames reduce a floating
 * budget, our running hosts join a host-based seat set, and recently seated hosts cancel out of the
 * seat cap so the sample's {@code available} is not double counted.
 *
 * The provider sample comes from a temp JSON file (script provider, as in
 * {@link LicenseSourceTests}); the database rows come from a stubbed JdbcTemplate driving the
 * RowCallbackHandler.
 */
public class LicenseSourceInFlightTests {

    private Path dir;
    private Path json;

    @Before
    public void setUp() throws IOException {
        dir = Files.createTempDirectory("licinflight");
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
     * Rows for the in-flight query: {lic csv, host, recent}. The stub replays them through the
     * RowCallbackHandler exactly as the database would.
     */
    private static JdbcTemplate jdbcReturning(Object[][] rows) {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        doAnswer(invocation -> {
            RowCallbackHandler handler = invocation.getArgument(1);
            for (Object[] row : rows) {
                ResultSet rs = mock(ResultSet.class);
                when(rs.getString("lic")).thenReturn((String) row[0]);
                when(rs.getString("host")).thenReturn((String) row[1]);
                when(rs.getBoolean("recent")).thenReturn((Boolean) row[2]);
                handler.processRow(rs);
            }
            return null;
        }).when(jdbc).query(anyString(), any(RowCallbackHandler.class), any(), any());
        return jdbc;
    }

    private LicenseSource polledSource(JdbcTemplate jdbc) {
        MockEnvironment env = new MockEnvironment();
        env.setProperty("scheduler.license.provider", "script:cat " + json);
        env.setProperty("scheduler.license.timeout_seconds", "5");
        env.setProperty("scheduler.license.stale_seconds", "300");
        LicenseSource ls = new LicenseSource(env, jdbc);
        ls.poll();
        return ls;
    }

    @Test
    public void recentFramesReduceFloatingBudget() throws IOException {
        writeJson("{\"queried_at\": " + nowSec() + ", \"licenses\": ["
                + "{\"name\": \"maya\", \"total\": 10, \"available\": 5}]}");
        LicenseSource ls = polledSource(jdbcReturning(
                new Object[][] {{"maya", "h1", Boolean.TRUE}, {"maya", "h2", Boolean.TRUE},
                        // Not recent: the license server has already netted this one out.
                        {"maya", "h3", Boolean.FALSE},
                        // Different license: must not touch maya's budget.
                        {"katana", "h4", Boolean.TRUE},}));
        LicenseSource.LicenseBudget budget =
                ls.snapshotBudgets(Collections.singleton("maya")).get("maya");
        assertFalse(budget.stale);
        assertEquals("5 available minus 2 in-flight", 3, budget.usable);
    }

    @Test
    public void runningHostsJoinHostBasedSeats() throws IOException {
        // Provider knows h1; we are running the license on h2 (not recent).
        // Seats = {h1, h2}; no recent seats, so cap = 2 + available.
        writeJson("{\"queried_at\": " + nowSec() + ", \"licenses\": ["
                + "{\"name\": \"hengine\", \"total\": 8, \"available\": 1, "
                + "\"host_based\": true, \"hosts\": [{\"host\": \"h1\", \"count\": 1}]}]}");
        LicenseSource ls =
                polledSource(jdbcReturning(new Object[][] {{"hengine", "H2", Boolean.FALSE},}));
        LicenseSource.LicenseBudget budget =
                ls.snapshotBudgets(Collections.singleton("hengine")).get("hengine");
        assertTrue(budget.hostBased);
        assertTrue("DB host must be lowercased into the seat set", budget.seats.contains("h2"));
        assertTrue(budget.seats.contains("h1"));
        assertEquals(2, budget.seats.size());
        assertEquals("cap = 2 seats + 1 still available", 3, budget.seatCap);
    }

    @Test
    public void recentlySeatedHostsCancelOutOfTheCap() throws IOException {
        // h2 was seated INSIDE the sample window: it is in the seat set but the
        // sample's `available` has not seen it, so it must be netted out of the
        // cap -- otherwise every host we seat would raise the cap by one and
        // immediately justify another.
        writeJson("{\"queried_at\": " + nowSec() + ", \"licenses\": ["
                + "{\"name\": \"hengine\", \"total\": 8, \"available\": 1, "
                + "\"host_based\": true, \"hosts\": [{\"host\": \"h1\", \"count\": 1}]}]}");
        LicenseSource ls =
                polledSource(jdbcReturning(new Object[][] {{"hengine", "h2", Boolean.TRUE},}));
        LicenseSource.LicenseBudget budget =
                ls.snapshotBudgets(Collections.singleton("hengine")).get("hengine");
        assertEquals(2, budget.seats.size());
        assertEquals("cap = 2 seats + max(0, 1 available - 1 recent seat)", 2, budget.seatCap);
    }
}
