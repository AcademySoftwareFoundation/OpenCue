
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

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

import org.junit.Before;
import org.junit.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.InOrder;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchJob;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.ResourceUsage;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.dispatcher.DispatchSupportService;
import com.imageworks.spcue.dispatcher.QueuedFrameCompletion;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.report.FrameCompleteReport;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.when;

/**
 * The usage counters of one scoop reach the database aggregated per key: one row per show, job and
 * layer with the frame count and the summed times, the highest clock time per job and layer, the
 * lowest per layer. Five hundred completions of one show are one write on its stats row, never five
 * hundred, and no frame is lost in the aggregation.
 */
public class DispatchSupportServiceCountersTests {

    private static final int FRAMES = 500;

    private DispatchSupportService service;
    private ShowDao showDao;
    private JobDao jobDao;
    private LayerDao layerDao;
    // consumed by scoop(): the usage the mocked read returns per frame id
    private final Map<String, ResourceUsage> usageByFrame = new HashMap<>();

    @Before
    public void setup() {
        service = new DispatchSupportService();
        FrameDao frameDao = mock(FrameDao.class);
        showDao = mock(ShowDao.class);
        jobDao = mock(JobDao.class);
        layerDao = mock(LayerDao.class);
        when(frameDao.getResourceUsage(any()))
                .thenAnswer(i -> usageByFrame.get(((DispatchFrame) i.getArgument(0)).id));
        service.setFrameDao(frameDao);
        service.setShowDao(showDao);
        service.setJobDao(jobDao);
        service.setLayerDao(layerDao);
    }

    /**
     * One show, two jobs (frames 0..299 on j1, the rest on j2), three layers (frame i on layer i
     * mod 3). Every fifth frame failed with a positive status, every seventh with a signal. Frame i
     * ran i + 1 seconds on 200 to 400 core points with one or two gpus, so a row's core, gpu and
     * clock sums and its count are four distinct numbers and a swapped parameter shows.
     */
    private List<QueuedFrameCompletion> scoop() {
        List<QueuedFrameCompletion> scoop = new ArrayList<>();
        for (int i = 0; i < FRAMES; i++) {
            int status = i % 5 == 0 ? 1 : (i % 7 == 0 ? -9 : 0);
            scoop.add(completion("f" + i, i < 300 ? "j1" : "j2", "l" + (i % 3), status,
                    new ResourceUsage(i + 1, 200 + 100 * (i % 3), 1 + (i % 2))));
        }
        return scoop;
    }

    private QueuedFrameCompletion completion(String frameId, String jobId, String layerId,
            int status, ResourceUsage usage) {
        DispatchFrame frame = new DispatchFrame();
        frame.id = frameId;
        frame.showId = "show";
        frame.jobId = jobId;
        frame.layerId = layerId;
        usageByFrame.put(frame.id, usage);
        return new QueuedFrameCompletion(FrameCompleteReport.getDefaultInstance(),
                new VirtualProc(), new DispatchJob(), new LayerDetail(), new FrameDetail(), frame,
                status == 0 ? FrameState.SUCCEEDED : FrameState.DEAD, status);
    }

    /** {successes, core, gpu, clock, failures, failCore, failClock, high, low} per key. */
    private Map<String, long[]> expected(List<QueuedFrameCompletion> scoop) {
        Map<String, long[]> exp = new TreeMap<>();
        for (QueuedFrameCompletion c : scoop) {
            ResourceUsage u = usageByFrame.get(c.frame.id);
            for (String key : new String[] {c.frame.showId, c.frame.jobId, c.frame.layerId}) {
                long[] t = exp.computeIfAbsent(key,
                        k -> new long[] {0, 0, 0, 0, 0, 0, 0, 0, Long.MAX_VALUE});
                if (c.exitStatus == 0) {
                    t[0]++;
                    t[1] += u.getCoreTimeSeconds();
                    t[2] += u.getGpuTimeSeconds();
                    t[3] += u.getClockTimeSeconds();
                    t[7] = Math.max(t[7], u.getClockTimeSeconds());
                    t[8] = Math.min(t[8], u.getClockTimeSeconds());
                } else {
                    t[4]++;
                    t[5] += u.getCoreTimeSeconds();
                    t[6] += u.getClockTimeSeconds();
                }
            }
        }
        return exp;
    }

    private static long count(List<Object[]> rows, int countIndex) {
        long n = 0;
        for (Object[] r : rows)
            n += ((Number) r[countIndex]).longValue();
        return n;
    }

    /** The row carrying the key, the row's last element. */
    private static Object[] row(List<Object[]> rows, String key) {
        for (Object[] r : rows)
            if (key.equals(r[r.length - 1]))
                return r;
        throw new AssertionError("no row for " + key + " in " + rows.size() + " rows");
    }

    private static long[] values(Object[] row, int... at) {
        long[] out = new long[at.length];
        for (int i = 0; i < at.length; i++)
            out[i] = ((Number) row[at[i]]).longValue();
        return out;
    }

    @SuppressWarnings("unchecked")
    private static ArgumentCaptor<List<Object[]>> rows() {
        return ArgumentCaptor.forClass(List.class);
    }

    @Test
    public void aScoopWritesOneRowPerKey() {
        List<QueuedFrameCompletion> scoop = scoop();
        Map<String, long[]> exp = expected(scoop);
        service.updateUsageCountersBatch(scoop);
        ArgumentCaptor<List<Object[]>> show = rows();
        verify(showDao).updateFrameCountersBatch(show.capture());
        assertEquals("one row for the one show", 1, show.getValue().size());
        assertArrayEquals("show row {successes, failures}",
                new long[] {exp.get("show")[0], exp.get("show")[4]},
                values(row(show.getValue(), "show"), 0, 1));
        ArgumentCaptor<List<Object[]>> job = rows();
        verify(jobDao).updateUsageBatch(job.capture());
        assertEquals("one row per job", 2, job.getValue().size());
        for (String j : new String[] {"j1", "j2"}) {
            long[] e = exp.get(j);
            assertArrayEquals(
                    j + " row {core, gpu, clock, successes, failCore, failClock, failures, high}",
                    new long[] {e[1], e[2], e[3], e[0], e[5], e[6], e[4], e[7]},
                    values(row(job.getValue(), j), 0, 1, 2, 3, 4, 5, 6, 7));
        }
        ArgumentCaptor<List<Object[]>> layer = rows();
        verify(layerDao).updateUsageBatch(layer.capture());
        assertEquals("one row per layer", 3, layer.getValue().size());
        for (String l : new String[] {"l0", "l1", "l2"}) {
            long[] e = exp.get(l);
            assertArrayEquals(
                    l + " row {core, gpu, clock, successes, failCore, failClock,"
                            + " failures, high, successes, low}",
                    new long[] {e[1], e[2], e[3], e[0], e[5], e[6], e[4], e[7], e[0], e[8]},
                    values(row(layer.getValue(), l), 0, 1, 2, 3, 4, 5, 6, 7, 8, 9));
        }
        assertEquals("no frame is lost across the show row", (long) FRAMES,
                count(show.getValue(), 0) + count(show.getValue(), 1));
        assertEquals("no frame is lost across the job rows", (long) FRAMES,
                count(job.getValue(), 3) + count(job.getValue(), 6));
        assertEquals("no frame is lost across the layer rows", (long) FRAMES,
                count(layer.getValue(), 3) + count(layer.getValue(), 6));
    }

    @Test
    public void aKeyWithoutASuccessPassesZeroExtremes() {
        // A failure-only row must not move a high or a low: it passes 0 for the
        // high, which never raises the column, and 0 successes, the low's guard.
        List<QueuedFrameCompletion> scoop = new ArrayList<>();
        scoop.add(completion("a", "j1", "l0", 1, new ResourceUsage(7, 100, 0)));
        service.updateUsageCountersBatch(scoop);
        ArgumentCaptor<List<Object[]>> layer = rows();
        verify(layerDao).updateUsageBatch(layer.capture());
        assertArrayEquals(new long[] {0, 1, 0, 0, 0},
                values(row(layer.getValue(), "l0"), 3, 6, 7, 8, 9));
    }

    @Test
    public void theTablesAndTheirRowsComeInOneOrder() {
        // The frames arrive with the jobs in the order j2, j1; the show, job
        // and layer tables each take one statement, in that order, with the
        // rows in key order: two workers holding the same rows lock them in
        // one order, inside a statement and across the tables.
        List<QueuedFrameCompletion> scoop = new ArrayList<>();
        scoop.add(completion("a", "j2", "l1", 0, new ResourceUsage(1, 100, 0)));
        scoop.add(completion("b", "j1", "l0", 1, new ResourceUsage(1, 100, 0)));
        service.updateUsageCountersBatch(scoop);
        InOrder tables = inOrder(showDao, jobDao, layerDao);
        ArgumentCaptor<List<Object[]>> job = rows(), layer = rows();
        tables.verify(showDao, times(1)).updateFrameCountersBatch(any());
        tables.verify(jobDao, times(1)).updateUsageBatch(job.capture());
        tables.verify(layerDao, times(1)).updateUsageBatch(layer.capture());
        assertEquals("j1", job.getValue().get(0)[8]);
        assertEquals("j2", job.getValue().get(1)[8]);
        assertEquals("l0", layer.getValue().get(0)[10]);
        assertEquals("l1", layer.getValue().get(1)[10]);
    }
}
