
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

import java.util.Collections;

import org.junit.Before;
import org.junit.Test;
import org.springframework.core.env.Environment;
import org.springframework.test.util.ReflectionTestUtils;

import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.rqd.RqdClient;
import com.imageworks.spcue.rqd.RqdClientException;
import com.imageworks.spcue.service.MaintenanceManagerSupport;

import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Unit tests for the orphaned-frame clearing path in {@link MaintenanceManagerSupport}. These are
 * pure Mockito tests (no Spring context / DB) so they exercise the kill-then-confirm decision logic
 * directly.
 */
public class MaintenanceManagerOrphanFrameTests {

    private MaintenanceManagerSupport maintenanceManager;
    private FrameDao frameDao;
    private RqdClient rqdClient;
    private Environment env;

    @Before
    public void setup() {
        maintenanceManager = new MaintenanceManagerSupport();
        frameDao = mock(FrameDao.class);
        rqdClient = mock(RqdClient.class);
        env = mock(Environment.class);
        // Generous default budget; individual tests override when they need budget exhaustion.
        when(env.getProperty(eq("maintenance.orphaned_frame_kill_budget_ms"), eq(Long.class),
                anyLong())).thenReturn(5000L);
        maintenanceManager.setFrameDao(frameDao);
        maintenanceManager.setRqdClient(rqdClient);
        ReflectionTestUtils.setField(maintenanceManager, "env", env);
    }

    private FrameDetail orphanFrame(String id, String lastResource) {
        FrameDetail frame = new FrameDetail();
        frame.id = id;
        frame.name = "0001-render";
        frame.lastResource = lastResource;
        return frame;
    }

    @Test
    public void confirmedDeadResetsToWaiting() {
        FrameDetail frame = orphanFrame("frame-1", "host1/100/0");
        when(frameDao.getOrphanedFrames()).thenReturn(Collections.singletonList(frame));
        when(rqdClient.isFrameRunning("host1", "frame-1")).thenReturn(false);

        maintenanceManager.clearOrphanedFrames();

        verify(rqdClient).killFrame(eq("host1"), eq("frame-1"), anyString());
        verify(frameDao).updateFrameStopped(frame, FrameState.WAITING,
                Dispatcher.EXIT_STATUS_FRAME_ORPHAN);
        verify(frameDao, never()).updateFrameStopped(frame, FrameState.DEAD,
                Dispatcher.EXIT_STATUS_FRAME_ORPHAN);
    }

    @Test
    public void hostUnreachableMarksDead() {
        FrameDetail frame = orphanFrame("frame-2", "host2/100/0");
        when(frameDao.getOrphanedFrames()).thenReturn(Collections.singletonList(frame));
        when(rqdClient.isFrameRunning("host2", "frame-2"))
                .thenThrow(new RqdClientException("host unreachable"));

        maintenanceManager.clearOrphanedFrames();

        verify(rqdClient).killFrame(eq("host2"), eq("frame-2"), anyString());
        verify(frameDao).updateFrameStopped(frame, FrameState.DEAD,
                Dispatcher.EXIT_STATUS_FRAME_ORPHAN);
        verify(frameDao, never()).updateFrameStopped(frame, FrameState.WAITING,
                Dispatcher.EXIT_STATUS_FRAME_ORPHAN);
    }

    @Test
    public void budgetExhaustedSendsBestEffortKillThenMarksDead() {
        // Zero budget: the pass deadline is already reached, so death cannot be confirmed. A
        // best-effort, non-blocking kill is still sent so the render is asked to stop, but no
        // confirmation is polled and the frame is failed closed (DEAD).
        when(env.getProperty(eq("maintenance.orphaned_frame_kill_budget_ms"), eq(Long.class),
                anyLong())).thenReturn(0L);
        FrameDetail frame = orphanFrame("frame-3", "host3/100/0");
        when(frameDao.getOrphanedFrames()).thenReturn(Collections.singletonList(frame));

        maintenanceManager.clearOrphanedFrames();

        verify(rqdClient).killFrame(eq("host3"), eq("frame-3"), anyString());
        verify(rqdClient, never()).isFrameRunning(anyString(), anyString());
        verify(frameDao).updateFrameStopped(frame, FrameState.DEAD,
                Dispatcher.EXIT_STATUS_FRAME_ORPHAN);
    }

    @Test
    public void neverRanResetsToWaitingWithoutKill() {
        // Empty lastResource: the frame never ran, so there is no render to kill or confirm.
        FrameDetail frame = orphanFrame("frame-4", "");
        when(frameDao.getOrphanedFrames()).thenReturn(Collections.singletonList(frame));

        maintenanceManager.clearOrphanedFrames();

        verify(rqdClient, never()).killFrame(anyString(), anyString(), anyString());
        verify(frameDao).updateFrameStopped(frame, FrameState.WAITING,
                Dispatcher.EXIT_STATUS_FRAME_ORPHAN);
    }
}
