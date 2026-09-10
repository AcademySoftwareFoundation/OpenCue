
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

import org.junit.Before;
import org.junit.Test;
import org.mockito.InOrder;
import org.springframework.core.env.Environment;
import org.springframework.test.util.ReflectionTestUtils;

import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.ProcInterface;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dao.ProcDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.dispatcher.DispatchSupportService;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.rqd.RqdClient;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Unit tests for the kill-before-release behavior added to {@link DispatchSupportService#lostProc}.
 * lostProc is {@code @Transactional(NOT_SUPPORTED)} and its nested DAO calls open independent
 * transactions, which does not play well with the commit-and-rollback embedded-DB harness. These
 * tests therefore exercise the method directly with mocked collaborators so the kill/release
 * ordering can be asserted deterministically.
 */
public class DispatchSupportServiceLostProcTests {

    private static final String KILL_BEFORE_RELEASE_PROPERTY =
            "dispatcher.kill_running_frame_before_release_enabled";
    private static final String DEFER_RELEASE_PROPERTY =
            "dispatcher.defer_release_on_failed_kill_enabled";
    private static final String MAX_DEFER_PROPERTY = "dispatcher.lost_proc_max_defer_ms";
    private static final long MAX_DEFER_DEFAULT = 1200000L;

    private DispatchSupportService dispatchSupport;
    private RqdClient rqdClient;
    private ProcDao procDao;
    private FrameDao frameDao;
    private HostDao hostDao;
    private Environment env;
    private VirtualProc proc;

    @Before
    public void setup() {
        dispatchSupport = new DispatchSupportService();
        rqdClient = mock(RqdClient.class);
        procDao = mock(ProcDao.class);
        frameDao = mock(FrameDao.class);
        hostDao = mock(HostDao.class);
        env = mock(Environment.class);

        dispatchSupport.setRqdClient(rqdClient);
        dispatchSupport.setProcDao(procDao);
        dispatchSupport.setFrameDao(frameDao);
        dispatchSupport.setHostDao(hostDao);
        dispatchSupport.setShowDao(mock(ShowDao.class));
        dispatchSupport.setJobDao(mock(JobDao.class));
        dispatchSupport.setLayerDao(mock(LayerDao.class));
        ReflectionTestUtils.setField(dispatchSupport, "env", env);

        // Kill-before-release and defer-release both enabled by default.
        when(env.getProperty(eq(KILL_BEFORE_RELEASE_PROPERTY), eq(Boolean.class), eq(true)))
                .thenReturn(true);
        when(env.getProperty(eq(DEFER_RELEASE_PROPERTY), eq(Boolean.class), eq(true)))
                .thenReturn(true);
        when(env.getProperty(eq(MAX_DEFER_PROPERTY), eq(Long.class), eq(MAX_DEFER_DEFAULT)))
                .thenReturn(MAX_DEFER_DEFAULT);

        // Default: the host still looks Up in the DB (the dangerous flapping case).
        when(hostDao.isHostUp(any(HostInterface.class))).thenReturn(true);

        // Default: the proc's deferral bound has not expired yet.
        when(procDao.isPingOlderThan(any(ProcInterface.class), anyLong())).thenReturn(false);

        // Default: the host has not been rebooted since the proc was dispatched.
        when(procDao.isHostRebootedSinceDispatch(any(ProcInterface.class))).thenReturn(false);

        proc = new VirtualProc();
        proc.id = "00000000-0000-0000-0000-000000000001";
        proc.frameId = "00000000-0000-0000-0000-0000000000f1";
        proc.hostName = "test-host";

        when(procDao.deleteVirtualProc(any(VirtualProc.class))).thenReturn(true);
        when(frameDao.getFrame(proc.frameId)).thenReturn(mock(FrameInterface.class));
        when(frameDao.updateFrameStopped(any(FrameInterface.class), any(FrameState.class),
                anyInt())).thenReturn(true);
    }

    @Test
    public void killsRqdBeforeReleasingProc() {
        // The kill confirms nothing is running there (RQD answered NOT_FOUND): release is safe.
        when(rqdClient.killFrame(eq(proc), anyString())).thenReturn(true);

        dispatchSupport.lostProc(proc, "orphaned", Dispatcher.EXIT_STATUS_FRAME_ORPHAN);

        InOrder inOrder = inOrder(rqdClient, procDao);
        inOrder.verify(rqdClient, times(1)).killFrame(eq(proc), anyString());
        inOrder.verify(procDao, times(1)).deleteVirtualProc(proc);
        verify(frameDao, times(1)).updateFrameStopped(any(FrameInterface.class),
                eq(FrameState.WAITING), anyInt());
    }

    @Test
    public void defersReleaseWhenKillOnlyDeliveredToLiveRender() {
        // RQD acknowledged the kill: the signal was delivered but the render is still alive
        // until it honors it. Releasing on the ACK would re-book the frame while the superseded
        // render is still shutting down (and writing output), so the release is deferred and the
        // run's own frame complete report finalizes it.
        when(rqdClient.killFrame(eq(proc), anyString())).thenReturn(false);

        assertFalse(
                dispatchSupport.lostProc(proc, "orphaned", Dispatcher.EXIT_STATUS_FRAME_ORPHAN));

        verify(rqdClient, times(1)).killFrame(eq(proc), anyString());
        verify(procDao, never()).deleteVirtualProc(any(VirtualProc.class));
        verify(frameDao, never()).updateFrameStopped(any(FrameInterface.class),
                any(FrameState.class), anyInt());
        // A delivered kill proves the render is alive right now; the reboot escape hatch must
        // not release it.
        verify(procDao, never()).isHostRebootedSinceDispatch(any(ProcInterface.class));
    }

    @Test
    public void defersWhenKillDeliveredEvenIfHostMarkedDown() {
        // A host marked DOWN that still answers its kill RPC is partitioned or report-starved,
        // not dead: the delivered kill is positive proof of a live render, so the DOWN state must
        // not release the frame for re-booking.
        when(rqdClient.killFrame(eq(proc), anyString())).thenReturn(false);
        when(hostDao.isHostUp(any(HostInterface.class))).thenReturn(false);

        assertFalse(dispatchSupport.lostProc(proc, "down host", Dispatcher.EXIT_STATUS_DOWN_HOST));

        verify(procDao, never()).deleteVirtualProc(any(VirtualProc.class));
        verify(frameDao, never()).updateFrameStopped(any(FrameInterface.class),
                any(FrameState.class), anyInt());
    }

    @Test
    public void failsClosedToDeadWhenKillDeliveredAndBoundExceeded() {
        // A delivered kill whose frame complete report never arrives (e.g. the render ignores
        // the signal) cannot defer forever: past the bound the frame is parked DEAD, not WAITING.
        when(rqdClient.killFrame(eq(proc), anyString())).thenReturn(false);
        when(procDao.isPingOlderThan(any(ProcInterface.class), anyLong())).thenReturn(true);

        assertTrue(dispatchSupport.lostProc(proc, "orphaned", Dispatcher.EXIT_STATUS_FRAME_ORPHAN));

        verify(procDao, times(1)).deleteVirtualProc(proc);
        verify(frameDao, times(1)).updateFrameStopped(any(FrameInterface.class),
                eq(FrameState.DEAD), anyInt());
    }

    @Test
    public void skipsRqdKillForFailedKillExitStatus() {
        // The failed-kill path already attempted this exact kill, so lostProc must not re-issue it.
        // Since that kill demonstrably failed and the host still looks Up, the release is deferred
        // to avoid double-booking a possibly-still-rendering host.
        dispatchSupport.lostProc(proc, "failed kill", Dispatcher.EXIT_STATUS_FAILED_KILL);

        verify(rqdClient, never()).killFrame(any(VirtualProc.class), anyString());
        verify(procDao, never()).deleteVirtualProc(any(VirtualProc.class));
        verify(frameDao, never()).updateFrameStopped(any(FrameInterface.class),
                any(FrameState.class), anyInt());
    }

    @Test
    public void defersForFailedKillEvenWhenHostMarkedDownByDb() {
        // FAILED_KILL and the host no longer Up in the DB: the DOWN mark only means missed
        // reports, which a partition or report-ingest stall produces while the render keeps
        // running, so it is not proof of death and the release must defer.
        when(hostDao.isHostUp(any(HostInterface.class))).thenReturn(false);

        assertFalse(
                dispatchSupport.lostProc(proc, "failed kill", Dispatcher.EXIT_STATUS_FAILED_KILL));

        verify(rqdClient, never()).killFrame(any(VirtualProc.class), anyString());
        verify(procDao, never()).deleteVirtualProc(any(VirtualProc.class));
        verify(frameDao, never()).updateFrameStopped(any(FrameInterface.class),
                any(FrameState.class), anyInt());
    }

    @Test
    public void defersProcWhenRqdKillThrowsForDownHost() {
        // A host reported DOWN whose kill also throws is a partitioned-or-dead host; both look
        // identical, so the release defers until the silence bound decides.
        doThrow(new RuntimeException("host unreachable")).when(rqdClient)
                .killFrame(any(VirtualProc.class), anyString());

        assertFalse(dispatchSupport.lostProc(proc, "down host", Dispatcher.EXIT_STATUS_DOWN_HOST));

        verify(rqdClient, times(1)).killFrame(eq(proc), anyString());
        verify(procDao, never()).deleteVirtualProc(any(VirtualProc.class));
        verify(frameDao, never()).updateFrameStopped(any(FrameInterface.class),
                any(FrameState.class), anyInt());
    }

    @Test
    public void releasesWaitingWhenDownHostSilentPastBound() {
        // A DOWN host that has also been silent for the whole deferral bound is genuinely dead:
        // its frame is reset to WAITING (auto-retry), not parked DEAD.
        doThrow(new RuntimeException("host unreachable")).when(rqdClient)
                .killFrame(any(VirtualProc.class), anyString());
        when(procDao.isPingOlderThan(any(ProcInterface.class), anyLong())).thenReturn(true);

        assertTrue(dispatchSupport.lostProc(proc, "down host", Dispatcher.EXIT_STATUS_DOWN_HOST));

        verify(procDao, times(1)).deleteVirtualProc(proc);
        verify(frameDao, times(1)).updateFrameStopped(any(FrameInterface.class),
                eq(FrameState.WAITING), anyInt());
        verify(frameDao, never()).updateFrameStopped(any(FrameInterface.class), eq(FrameState.DEAD),
                anyInt());
    }

    @Test
    public void updatesFrameHostDownWhenFrameNotRunningForDownHost() {
        // Down host, silent past the bound, whose frame is no longer RUNNING but already DEAD:
        // updateFrameStopped reports nothing to stop, so the down-host fallback must reset it
        // via updateFrameHostDown.
        doThrow(new RuntimeException("host unreachable")).when(rqdClient)
                .killFrame(any(VirtualProc.class), anyString());
        when(procDao.isPingOlderThan(any(ProcInterface.class), anyLong())).thenReturn(true);
        when(frameDao.updateFrameStopped(any(FrameInterface.class), any(FrameState.class),
                anyInt())).thenReturn(false);
        FrameDetail deadFrame = new FrameDetail();
        deadFrame.state = FrameState.DEAD;
        when(frameDao.getFrameDetail(any(FrameInterface.class))).thenReturn(deadFrame);

        dispatchSupport.lostProc(proc, "down host", Dispatcher.EXIT_STATUS_DOWN_HOST);

        verify(procDao, times(1)).deleteVirtualProc(proc);
        verify(frameDao, times(1)).updateFrameHostDown(any(FrameInterface.class));
    }

    @Test
    public void defersReleaseWhenKillThrowsAndHostStillUp() {
        // The flapping-host case: the kill throws and the host still looks Up. Releasing now would
        // re-book the frame onto a second host while this RQD keeps rendering, so we must defer.
        doThrow(new RuntimeException("transient unreachable")).when(rqdClient)
                .killFrame(any(VirtualProc.class), anyString());

        dispatchSupport.lostProc(proc, "orphaned", Dispatcher.EXIT_STATUS_FRAME_ORPHAN);

        verify(rqdClient, times(1)).killFrame(eq(proc), anyString());
        verify(procDao, never()).deleteVirtualProc(any(VirtualProc.class));
        verify(frameDao, never()).updateFrameStopped(any(FrameInterface.class),
                any(FrameState.class), anyInt());
    }

    @Test
    public void releasesWaitingWhenKillThrowsAndHostNotUpPastBound() {
        // The kill throws, the host is not Up AND has been silent past the bound: dead with its
        // host, released back to WAITING.
        doThrow(new RuntimeException("host unreachable")).when(rqdClient)
                .killFrame(any(VirtualProc.class), anyString());
        when(hostDao.isHostUp(any(HostInterface.class))).thenReturn(false);
        when(procDao.isPingOlderThan(any(ProcInterface.class), anyLong())).thenReturn(true);

        assertTrue(dispatchSupport.lostProc(proc, "orphaned", Dispatcher.EXIT_STATUS_FRAME_ORPHAN));

        verify(rqdClient, times(1)).killFrame(eq(proc), anyString());
        verify(procDao, times(1)).deleteVirtualProc(proc);
        verify(frameDao, times(1)).updateFrameStopped(any(FrameInterface.class),
                eq(FrameState.WAITING), anyInt());
    }

    @Test
    public void releasesWhenDeferDisabledByPropertyEvenIfKillThrows() {
        // With defer disabled, behavior falls back to the prior always-release semantics.
        when(env.getProperty(eq(DEFER_RELEASE_PROPERTY), eq(Boolean.class), eq(true)))
                .thenReturn(false);
        doThrow(new RuntimeException("transient unreachable")).when(rqdClient)
                .killFrame(any(VirtualProc.class), anyString());

        dispatchSupport.lostProc(proc, "orphaned", Dispatcher.EXIT_STATUS_FRAME_ORPHAN);

        verify(procDao, times(1)).deleteVirtualProc(proc);
        verify(frameDao, times(1)).updateFrameStopped(any(FrameInterface.class),
                eq(FrameState.WAITING), anyInt());
    }

    @Test
    public void releasesWhenHostRebootedSinceDispatch() {
        // The kill cannot confirm the frame stopped and the host still looks Up, but the host
        // reports a boot time later than the proc's dispatch: the render died with the reboot, so
        // release is safe and the frame goes back to WAITING (auto-retry), not deferred.
        doThrow(new RuntimeException("transient unreachable")).when(rqdClient)
                .killFrame(any(VirtualProc.class), anyString());
        when(procDao.isHostRebootedSinceDispatch(any(ProcInterface.class))).thenReturn(true);

        assertTrue(dispatchSupport.lostProc(proc, "orphaned", Dispatcher.EXIT_STATUS_FRAME_ORPHAN));

        verify(procDao, times(1)).deleteVirtualProc(proc);
        verify(frameDao, times(1)).updateFrameStopped(any(FrameInterface.class),
                eq(FrameState.WAITING), anyInt());
    }

    @Test
    public void failsClosedToDeadWhenDeferralBoundExceeded() {
        // The kill still cannot confirm the frame stopped and the host still looks Up, but the
        // proc has gone unpinged longer than the deferral bound: instead of deferring forever the
        // proc is released and the frame is parked DEAD (manual retry), never WAITING, so it
        // cannot be auto-rebooked while the original render's fate is unknown.
        doThrow(new RuntimeException("transient unreachable")).when(rqdClient)
                .killFrame(any(VirtualProc.class), anyString());
        when(procDao.isPingOlderThan(any(ProcInterface.class), anyLong())).thenReturn(true);

        assertTrue(dispatchSupport.lostProc(proc, "orphaned", Dispatcher.EXIT_STATUS_FRAME_ORPHAN));

        verify(procDao, times(1)).deleteVirtualProc(proc);
        verify(frameDao, times(1)).updateFrameStopped(any(FrameInterface.class),
                eq(FrameState.DEAD), anyInt());
        verify(frameDao, never()).updateFrameStopped(any(FrameInterface.class),
                eq(FrameState.WAITING), anyInt());
    }

    @Test
    public void failsClosedToDeadForFailedKillExitStatusWhenBoundExceeded() {
        // Same bound applies to the upstream-failed-kill path (EXIT_STATUS_FAILED_KILL), which
        // never re-issues the kill but otherwise defers identically.
        when(procDao.isPingOlderThan(any(ProcInterface.class), anyLong())).thenReturn(true);

        assertTrue(
                dispatchSupport.lostProc(proc, "failed kill", Dispatcher.EXIT_STATUS_FAILED_KILL));

        verify(rqdClient, never()).killFrame(any(VirtualProc.class), anyString());
        verify(procDao, times(1)).deleteVirtualProc(proc);
        verify(frameDao, times(1)).updateFrameStopped(any(FrameInterface.class),
                eq(FrameState.DEAD), anyInt());
    }

    @Test
    public void defersIndefinitelyWhenBoundDisabledByProperty() {
        // A negative bound disables the fail-closed path entirely: deferral never expires, and
        // the ping-age query is not even consulted.
        when(env.getProperty(eq(MAX_DEFER_PROPERTY), eq(Long.class), eq(MAX_DEFER_DEFAULT)))
                .thenReturn(-1L);
        doThrow(new RuntimeException("transient unreachable")).when(rqdClient)
                .killFrame(any(VirtualProc.class), anyString());

        assertFalse(
                dispatchSupport.lostProc(proc, "orphaned", Dispatcher.EXIT_STATUS_FRAME_ORPHAN));

        verify(procDao, never()).isPingOlderThan(any(ProcInterface.class), anyLong());
        verify(procDao, never()).deleteVirtualProc(any(VirtualProc.class));
        verify(frameDao, never()).updateFrameStopped(any(FrameInterface.class),
                any(FrameState.class), anyInt());
    }

    @Test
    public void skipsRqdKillWhenDisabledByProperty() {
        when(env.getProperty(eq(KILL_BEFORE_RELEASE_PROPERTY), eq(Boolean.class), eq(true)))
                .thenReturn(false);

        dispatchSupport.lostProc(proc, "orphaned", Dispatcher.EXIT_STATUS_FRAME_ORPHAN);

        verify(rqdClient, never()).killFrame(any(VirtualProc.class), anyString());
        verify(procDao, times(1)).deleteVirtualProc(proc);
        verify(frameDao, times(1)).updateFrameStopped(any(FrameInterface.class),
                eq(FrameState.WAITING), anyInt());
    }
}
