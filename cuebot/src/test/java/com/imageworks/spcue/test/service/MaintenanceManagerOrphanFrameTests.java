
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

import java.sql.Timestamp;
import java.util.Arrays;
import java.util.Collections;

import org.junit.Before;
import org.junit.Test;
import org.springframework.core.env.Environment;
import org.springframework.test.util.ReflectionTestUtils;

import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.MaintenanceTask;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.MaintenanceDao;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.rqd.RqdClient;
import com.imageworks.spcue.rqd.RqdClientException;
import com.imageworks.spcue.service.MaintenanceManagerSupport;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.anyInt;
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

    private static final long HOUR_MS = 3600000L;

    private MaintenanceManagerSupport maintenanceManager;
    private FrameDao frameDao;
    private MaintenanceDao maintenanceDao;
    private RqdClient rqdClient;
    private Environment env;

    @Before
    public void setup() {
        maintenanceManager = new MaintenanceManagerSupport();
        frameDao = mock(FrameDao.class);
        maintenanceDao = mock(MaintenanceDao.class);
        rqdClient = mock(RqdClient.class);
        env = mock(Environment.class);
        // Behave like a real Environment with no overrides: return the caller's default. Individual
        // tests override specific properties by registering a more specific stub afterwards.
        when(env.getProperty(eq("maintenance.orphaned_frame_check_enabled"), eq(Boolean.class),
                anyBoolean())).thenAnswer(inv -> inv.getArgument(2));
        when(env.getProperty(eq("maintenance.orphaned_frame_kill_budget_ms"), eq(Long.class),
                anyLong())).thenAnswer(inv -> inv.getArgument(2));
        when(env.getProperty(eq("maintenance.orphaned_frame_confirm_timeout_ms"), eq(Long.class),
                anyLong())).thenAnswer(inv -> inv.getArgument(2));
        when(env.getProperty(eq("maintenance.orphaned_frame_max_defer_ms"), eq(Long.class),
                anyLong())).thenAnswer(inv -> inv.getArgument(2));
        when(env.getProperty(eq("maintenance.orphaned_frame_batch_size"), eq(Integer.class),
                anyInt())).thenAnswer(inv -> inv.getArgument(2));
        // The sweep is gated on a cluster-wide task lock; grant it by default.
        when(maintenanceDao.lockTask(MaintenanceTask.LOCK_ORPHANED_FRAME_CHECK)).thenReturn(true);
        // Each frame's orphanhood is re-checked right before it is acted on; hold it true by
        // default so tests exercise the kill/confirm paths. Individual tests override this to
        // simulate a frame that was concurrently finalized.
        when(frameDao.isOrphan(any(FrameDetail.class))).thenReturn(true);
        maintenanceManager.setFrameDao(frameDao);
        maintenanceManager.setMaintenanceDao(maintenanceDao);
        maintenanceManager.setRqdClient(rqdClient);
        ReflectionTestUtils.setField(maintenanceManager, "env", env);
    }

    private FrameDetail orphanFrame(String id, String lastResource) {
        FrameDetail frame = new FrameDetail();
        frame.id = id;
        frame.name = "0001-render";
        frame.lastResource = lastResource;
        // Recently updated so the frame is within the defer window unless a test ages it.
        frame.dateUpdated = new Timestamp(System.currentTimeMillis());
        return frame;
    }

    private void setBudgetMs(long ms) {
        when(env.getProperty(eq("maintenance.orphaned_frame_kill_budget_ms"), eq(Long.class),
                anyLong())).thenReturn(ms);
    }

    private void setConfirmTimeoutMs(long ms) {
        when(env.getProperty(eq("maintenance.orphaned_frame_confirm_timeout_ms"), eq(Long.class),
                anyLong())).thenReturn(ms);
    }

    private void setSingleOrphan(FrameDetail frame) {
        when(frameDao.getOrphanedFrames(anyInt())).thenReturn(Collections.singletonList(frame));
    }

    @Test
    public void confirmedDeadResetsToWaiting() {
        FrameDetail frame = orphanFrame("frame-1", "host1/100/0");
        setSingleOrphan(frame);
        when(rqdClient.isFrameRunning("host1", "frame-1")).thenReturn(false);

        maintenanceManager.clearOrphanedFrames();

        verify(rqdClient).killFrame(eq("host1"), eq("frame-1"), anyString());
        verify(frameDao).updateFrameStopped(frame, FrameState.WAITING,
                Dispatcher.EXIT_STATUS_FRAME_ORPHAN);
        verify(frameDao, never()).updateFrameStopped(frame, FrameState.DEAD,
                Dispatcher.EXIT_STATUS_FRAME_ORPHAN);
        verify(maintenanceDao).unlockTask(MaintenanceTask.LOCK_ORPHANED_FRAME_CHECK);
    }

    @Test
    public void hostUnreachableMarksDead() {
        FrameDetail frame = orphanFrame("frame-2", "host2/100/0");
        setSingleOrphan(frame);
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
    public void stillRunningReachableFrameIsDeferred() {
        // Reachable but still running, with a zero per-frame confirm timeout: one poll then the
        // per-frame deadline is hit, so the frame is deferred (left RUNNING) to the next pass.
        setConfirmTimeoutMs(0L);
        FrameDetail frame = orphanFrame("frame-3", "host3/100/0");
        setSingleOrphan(frame);
        when(rqdClient.isFrameRunning("host3", "frame-3")).thenReturn(true);

        maintenanceManager.clearOrphanedFrames();

        verify(rqdClient).killFrame(eq("host3"), eq("frame-3"), anyString());
        verify(rqdClient).isFrameRunning("host3", "frame-3");
        // Deferred means no state change at all: neither WAITING nor DEAD.
        verify(frameDao, never()).updateFrameStopped(eq(frame), any(FrameState.class), anyInt());
    }

    @Test
    public void stillRunningExpiredOrphanMarksDead() {
        // Reachable but still running, and orphaned longer than the max defer window: fail closed.
        setConfirmTimeoutMs(0L);
        FrameDetail frame = orphanFrame("frame-4", "host4/100/0");
        frame.dateUpdated = new Timestamp(System.currentTimeMillis() - 2 * HOUR_MS);
        setSingleOrphan(frame);
        when(rqdClient.isFrameRunning("host4", "frame-4")).thenReturn(true);

        maintenanceManager.clearOrphanedFrames();

        verify(frameDao).updateFrameStopped(frame, FrameState.DEAD,
                Dispatcher.EXIT_STATUS_FRAME_ORPHAN);
        verify(frameDao, never()).updateFrameStopped(frame, FrameState.WAITING,
                Dispatcher.EXIT_STATUS_FRAME_ORPHAN);
    }

    @Test
    public void budgetExhaustedSendsBestEffortKillThenDefers() {
        // Zero budget: no time to confirm death this pass. A best-effort, non-blocking kill is
        // still sent, but the frame is deferred (left RUNNING) rather than failed closed.
        setBudgetMs(0L);
        FrameDetail frame = orphanFrame("frame-5", "host5/100/0");
        setSingleOrphan(frame);

        maintenanceManager.clearOrphanedFrames();

        verify(rqdClient).killFrame(eq("host5"), eq("frame-5"), anyString());
        verify(rqdClient, never()).isFrameRunning(anyString(), anyString());
        verify(frameDao, never()).updateFrameStopped(eq(frame), any(FrameState.class), anyInt());
    }

    @Test
    public void budgetExhaustedExpiredOrphanMarksDead() {
        // Zero budget and orphaned longer than the max defer window: send a best-effort kill and
        // fail closed so the frame surfaces for a manual retry instead of lingering RUNNING.
        setBudgetMs(0L);
        FrameDetail frame = orphanFrame("frame-6", "host6/100/0");
        frame.dateUpdated = new Timestamp(System.currentTimeMillis() - 2 * HOUR_MS);
        setSingleOrphan(frame);

        maintenanceManager.clearOrphanedFrames();

        verify(rqdClient).killFrame(eq("host6"), eq("frame-6"), anyString());
        verify(rqdClient, never()).isFrameRunning(anyString(), anyString());
        verify(frameDao).updateFrameStopped(frame, FrameState.DEAD,
                Dispatcher.EXIT_STATUS_FRAME_ORPHAN);
    }

    @Test
    public void neverRanResetsToWaitingWithoutKill() {
        // Empty lastResource: the frame never ran, so there is no render to kill or confirm.
        FrameDetail frame = orphanFrame("frame-7", "");
        setSingleOrphan(frame);

        maintenanceManager.clearOrphanedFrames();

        verify(rqdClient, never()).killFrame(anyString(), anyString(), anyString());
        verify(frameDao).updateFrameStopped(frame, FrameState.WAITING,
                Dispatcher.EXIT_STATUS_FRAME_ORPHAN);
    }

    @Test
    public void budgetExhaustedNeverRanFrameStaysRetryable() {
        // Zero budget and empty lastResource: no render can exist, so even without time to confirm
        // anything the frame must stay retryable (WAITING), not be deferred or failed closed.
        setBudgetMs(0L);
        FrameDetail frame = orphanFrame("frame-8", "");
        setSingleOrphan(frame);

        maintenanceManager.clearOrphanedFrames();

        verify(rqdClient, never()).killFrame(anyString(), anyString(), anyString());
        verify(frameDao).updateFrameStopped(frame, FrameState.WAITING,
                Dispatcher.EXIT_STATUS_FRAME_ORPHAN);
        verify(frameDao, never()).updateFrameStopped(frame, FrameState.DEAD,
                Dispatcher.EXIT_STATUS_FRAME_ORPHAN);
    }

    @Test
    public void slowFrameDoesNotStarveNextFrame() {
        // A reachable-but-still-running frame hits its per-frame confirm timeout and is deferred;
        // the frame behind it in the batch must still get its own kill/confirm turn within the
        // pass budget instead of being starved.
        setConfirmTimeoutMs(0L);
        FrameDetail slowFrame = orphanFrame("frame-slow", "hostA/100/0");
        FrameDetail nextFrame = orphanFrame("frame-next", "hostB/100/0");
        when(frameDao.getOrphanedFrames(anyInt())).thenReturn(Arrays.asList(slowFrame, nextFrame));
        when(rqdClient.isFrameRunning("hostA", "frame-slow")).thenReturn(true);
        when(rqdClient.isFrameRunning("hostB", "frame-next")).thenReturn(false);

        maintenanceManager.clearOrphanedFrames();

        verify(rqdClient).killFrame(eq("hostA"), eq("frame-slow"), anyString());
        verify(rqdClient).killFrame(eq("hostB"), eq("frame-next"), anyString());
        // The slow frame is deferred with no state change; the next frame is confirmed dead and
        // reset for auto-retry.
        verify(frameDao, never()).updateFrameStopped(eq(slowFrame), any(FrameState.class),
                anyInt());
        verify(frameDao).updateFrameStopped(nextFrame, FrameState.WAITING,
                Dispatcher.EXIT_STATUS_FRAME_ORPHAN);
    }

    @Test
    public void noLongerOrphanedFrameIsSkipped() {
        // The frame stopped being an orphan between getOrphanedFrames() and its turn in the batch
        // (e.g. a late FrameCompleteReport finalized it and it was rebooked): it must be skipped
        // entirely -- no kill, no confirm, no state change -- or the kill could hit the new
        // legitimate run.
        FrameDetail frame = orphanFrame("frame-9", "host9/100/0");
        setSingleOrphan(frame);
        when(frameDao.isOrphan(frame)).thenReturn(false);

        maintenanceManager.clearOrphanedFrames();

        verify(rqdClient, never()).killFrame(anyString(), anyString(), anyString());
        verify(rqdClient, never()).isFrameRunning(anyString(), anyString());
        verify(frameDao, never()).updateFrameStopped(eq(frame), any(FrameState.class), anyInt());
    }

    @Test
    public void lockNotAcquiredSkipsSweep() {
        when(maintenanceDao.lockTask(MaintenanceTask.LOCK_ORPHANED_FRAME_CHECK)).thenReturn(false);

        maintenanceManager.clearOrphanedFrames();

        verify(frameDao, never()).getOrphanedFrames(anyInt());
        verify(maintenanceDao, never()).unlockTask(MaintenanceTask.LOCK_ORPHANED_FRAME_CHECK);
    }

    @Test
    public void disabledSkipsSweep() {
        when(env.getProperty(eq("maintenance.orphaned_frame_check_enabled"), eq(Boolean.class),
                anyBoolean())).thenReturn(false);

        maintenanceManager.clearOrphanedFrames();

        verify(maintenanceDao, never()).lockTask(MaintenanceTask.LOCK_ORPHANED_FRAME_CHECK);
        verify(frameDao, never()).getOrphanedFrames(anyInt());
    }
}
