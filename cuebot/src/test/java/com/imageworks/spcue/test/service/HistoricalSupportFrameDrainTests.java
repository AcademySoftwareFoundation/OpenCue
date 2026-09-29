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

package com.imageworks.spcue.test.service;

import org.junit.Before;
import org.junit.Test;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.dao.QueryTimeoutException;

import com.imageworks.spcue.PrometheusMetricsCollector;
import com.imageworks.spcue.dao.HistoricalDao.FrameHistoryBacklog;
import com.imageworks.spcue.dao.HistoricalDao.FrameHistoryDrain;
import com.imageworks.spcue.service.HistoricalManager;
import com.imageworks.spcue.service.HistoricalSupport;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.anyDouble;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Unit tests for the batching loop in {@link HistoricalSupport#drainFrameHistory()}. Pure Mockito;
 * the SQL side is covered by FrameHistoryQueueTests.
 */
public class HistoricalSupportFrameDrainTests {

    private static final int BATCH = 10;

    private HistoricalSupport support;
    private HistoricalManager manager;
    private PrometheusMetricsCollector metrics;
    private FrameHistoryBacklog backlog;

    @Before
    public void setup() {
        manager = mock(HistoricalManager.class);
        metrics = mock(PrometheusMetricsCollector.class);
        backlog = new FrameHistoryBacklog(0, 0);
        when(manager.getFrameHistoryBacklog()).thenReturn(backlog);

        support = new HistoricalSupport();
        support.setHistoricalManager(manager);
        support.setPrometheusMetrics(metrics);
        support.setFrameDrainBatchSize(BATCH);
    }

    @Test
    public void stopsWhenABatchComesBackShort() {
        when(manager.drainFrameHistory(BATCH, false)).thenReturn(new FrameHistoryDrain(BATCH, 0, 0),
                new FrameHistoryDrain(4, 1, 0));

        support.drainFrameHistory();

        verify(manager, times(2)).drainFrameHistory(BATCH, false);
        verify(metrics).recordFrameHistoryDrain(eq(13), eq(1), eq(0), anyDouble(), eq(backlog));
    }

    @Test
    public void keepsDrainingWhileBatchesComeBackFull() {
        FrameHistoryDrain full = new FrameHistoryDrain(BATCH, 0, 0);
        when(manager.drainFrameHistory(BATCH, false)).thenReturn(full, full, full, full, full,
                new FrameHistoryDrain(0, 0, 0));

        support.drainFrameHistory();

        verify(manager, times(6)).drainFrameHistory(BATCH, false);
        verify(metrics).recordFrameHistoryDrain(eq(50), eq(0), eq(0), anyDouble(), eq(backlog));
    }

    @Test
    public void sumsMergedRunsAcrossBatches() {
        when(manager.drainFrameHistory(BATCH, false)).thenReturn(new FrameHistoryDrain(BATCH, 0, 4),
                new FrameHistoryDrain(6, 0, 3));

        support.drainFrameHistory();

        verify(metrics).recordFrameHistoryDrain(eq(16), eq(0), eq(7), anyDouble(), eq(backlog));
    }

    @Test
    public void emptyDrainWhenAnotherCuebotHoldsTheLock() {
        when(manager.drainFrameHistory(BATCH, false)).thenReturn(new FrameHistoryDrain(0, 0, 0));

        support.drainFrameHistory();

        verify(manager, times(1)).drainFrameHistory(anyInt(), anyBoolean());
        verify(metrics).recordFrameHistoryDrain(eq(0), eq(0), eq(0), anyDouble(), eq(backlog));
    }

    @Test
    public void retriesFailedBatchInSafeMode() {
        when(manager.drainFrameHistory(BATCH, false))
                .thenThrow(new DataIntegrityViolationException("value too long"))
                .thenReturn(new FrameHistoryDrain(2, 0, 0));
        when(manager.drainFrameHistory(BATCH, true)).thenReturn(new FrameHistoryDrain(BATCH, 1, 0));

        support.drainFrameHistory();

        verify(manager, times(1)).drainFrameHistory(BATCH, true);
        verify(manager, times(2)).drainFrameHistory(BATCH, false);
        verify(metrics).recordFrameHistoryDrain(eq(11), eq(1), eq(0), anyDouble(), eq(backlog));
    }

    @Test
    public void swallowsFailuresAndStillRecordsMetrics() {
        when(manager.drainFrameHistory(anyInt(), anyBoolean()))
                .thenThrow(new QueryTimeoutException("db down"));
        when(manager.getFrameHistoryBacklog()).thenThrow(new QueryTimeoutException("db down"));

        support.drainFrameHistory();

        verify(manager, times(1)).drainFrameHistory(BATCH, true);
        verify(metrics).recordFrameHistoryDrain(eq(0), eq(0), eq(0), anyDouble(), isNull());
        verify(metrics, never()).recordFrameHistoryDrain(anyInt(), anyInt(), anyInt(), anyDouble(),
                any(FrameHistoryBacklog.class));
    }
}
