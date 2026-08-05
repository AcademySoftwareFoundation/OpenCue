
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

import io.grpc.Status;
import io.grpc.StatusRuntimeException;
import io.grpc.stub.StreamObserver;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowCallbackHandler;
import org.springframework.mock.env.MockEnvironment;

import com.imageworks.spcue.servant.ManageLicense;

import com.imageworks.spcue.grpc.license.License;
import com.imageworks.spcue.grpc.license.LicenseFindRequest;
import com.imageworks.spcue.grpc.license.LicenseFindResponse;
import com.imageworks.spcue.grpc.license.LicenseGetAllRequest;
import com.imageworks.spcue.grpc.license.LicenseGetAllResponse;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * Unit tests for the read-only {@link ManageLicense} servant: proto conversion of the
 * {@link LicenseSource#describe} view, the unconfigured empty response, and Find's case
 * normalization and NOT_FOUND path. No Spring and no database, matching the other licensing tests:
 * the servant is driven directly with a recording observer.
 */
public class ManageLicenseTests {

    /** Captures the single response the servant emits. */
    private static final class RecordingObserver<T> implements StreamObserver<T> {
        T value;
        Throwable error;
        boolean completed;

        @Override
        public void onNext(T v) {
            value = v;
        }

        @Override
        public void onError(Throwable t) {
            error = t;
        }

        @Override
        public void onCompleted() {
            completed = true;
        }
    }

    private Path dir;
    private Path json;

    @Before
    public void setUp() throws IOException {
        dir = Files.createTempDirectory("licservant");
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

    /** A servant over a polled source: hengine host-based, maya floating with headroom 2. */
    private ManageLicense polledServant() throws IOException {
        Files.write(json,
                ("{\"queried_at\": " + System.currentTimeMillis() / 1000L + ", \"licenses\": ["
                        + "{\"name\": \"hengine\", \"feature\": \"Houdini Engine\", \"total\": 8, "
                        + "\"available\": 2, \"host_based\": true, "
                        + "\"hosts\": [{\"host\": \"ws1\", \"count\": 1}]},"
                        + "{\"name\": \"maya\", \"total\": 10, \"available\": 5}]}")
                                .getBytes(StandardCharsets.UTF_8));
        MockEnvironment env = new MockEnvironment();
        env.setProperty("scheduler.license.provider", "script:cat " + json);
        env.setProperty("scheduler.license.timeout_seconds", "5");
        env.setProperty("scheduler.license.headroom.maya", "2");
        LicenseSource source = new LicenseSource(env,
                jdbcReturning(new Object[][] {{"maya", "h1", null}, {"maya", "h2", null},}));
        source.poll();
        ManageLicense servant = new ManageLicense();
        servant.setLicenseSource(source);
        return servant;
    }

    @Test
    public void getAllConvertsTheViewToProtos() throws IOException {
        ManageLicense servant = polledServant();
        RecordingObserver<LicenseGetAllResponse> observer = new RecordingObserver<>();
        servant.getAll(LicenseGetAllRequest.newBuilder().build(), observer);

        assertTrue(observer.completed);
        assertNotNull(observer.value);
        assertTrue(observer.value.getSource().getConfigured());
        assertTrue(observer.value.getSource().getHasSample());
        assertFalse(observer.value.getSource().getStale());
        assertEquals("CUE_LICENSES", observer.value.getSource().getEnvKey());
        assertEquals(2, observer.value.getLicensesCount());

        License hengine = observer.value.getLicenses(0);
        assertEquals("hengine", hengine.getName());
        assertEquals("Houdini Engine", hengine.getFeature());
        assertEquals(8, hengine.getTotal());
        assertEquals(2, hengine.getAvailable());
        assertTrue(hengine.getHostBased());
        assertEquals(1, hengine.getProviderHostCount());
        assertEquals(0, hengine.getRunningFrames());

        License maya = observer.value.getLicenses(1);
        assertEquals("maya", maya.getName());
        assertEquals(2, maya.getHeadroom());
        assertEquals(2, maya.getRunningFrames());
        assertEquals(2, maya.getRunningHosts());
    }

    @Test
    public void getAllWithoutProviderReturnsUnconfiguredStatus() {
        ManageLicense servant = new ManageLicense();
        servant.setLicenseSource(
                new LicenseSource(new MockEnvironment(), mock(JdbcTemplate.class)));
        RecordingObserver<LicenseGetAllResponse> observer = new RecordingObserver<>();
        servant.getAll(LicenseGetAllRequest.newBuilder().build(), observer);

        assertTrue(observer.completed);
        assertFalse(observer.value.getSource().getConfigured());
        assertTrue(observer.value.getSource().getStale());
        assertEquals(0, observer.value.getLicensesCount());
    }

    @Test
    public void findNormalizesCaseAndFinds() throws IOException {
        ManageLicense servant = polledServant();
        RecordingObserver<LicenseFindResponse> observer = new RecordingObserver<>();
        servant.find(LicenseFindRequest.newBuilder().setName("  Maya ").build(), observer);

        assertTrue(observer.completed);
        assertEquals("maya", observer.value.getLicense().getName());
        assertEquals(10, observer.value.getLicense().getTotal());
    }

    @Test
    public void findUnknownLicenseIsNotFound() throws IOException {
        ManageLicense servant = polledServant();
        RecordingObserver<LicenseFindResponse> observer = new RecordingObserver<>();
        servant.find(LicenseFindRequest.newBuilder().setName("katana").build(), observer);

        assertFalse(observer.completed);
        assertNotNull(observer.error);
        assertEquals(Status.Code.NOT_FOUND,
                ((StatusRuntimeException) observer.error).getStatus().getCode());
    }
}
