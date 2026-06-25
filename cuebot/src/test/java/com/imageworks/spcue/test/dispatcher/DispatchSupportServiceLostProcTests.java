
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

import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.HostInterface;
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

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
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

        // Default: the host still looks Up in the DB (the dangerous flapping case).
        when(hostDao.isHostUp(any(HostInterface.class))).thenReturn(true);

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
        dispatchSupport.lostProc(proc, "orphaned", Dispatcher.EXIT_STATUS_FRAME_ORPHAN);

        InOrder inOrder = inOrder(rqdClient, procDao);
        inOrder.verify(rqdClient, times(1)).killFrame(eq(proc), anyString());
        inOrder.verify(procDao, times(1)).deleteVirtualProc(proc);
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
    public void releasesForFailedKillWhenHostConfirmedDownByDb() {
        // FAILED_KILL but the host is no longer Up in the DB: no live RQD remains, release
        // proceeds.
        when(hostDao.isHostUp(any(HostInterface.class))).thenReturn(false);

        dispatchSupport.lostProc(proc, "failed kill", Dispatcher.EXIT_STATUS_FAILED_KILL);

        verify(rqdClient, never()).killFrame(any(VirtualProc.class), anyString());
        verify(procDao, times(1)).deleteVirtualProc(proc);
    }

    @Test
    public void releasesProcWhenRqdKillThrowsForDownHost() {
        // A host reported DOWN is confirmed dead: the kill may throw, but release must still
        // proceed.
        doThrow(new RuntimeException("host unreachable")).when(rqdClient)
                .killFrame(any(VirtualProc.class), anyString());

        dispatchSupport.lostProc(proc, "down host", Dispatcher.EXIT_STATUS_DOWN_HOST);

        verify(rqdClient, times(1)).killFrame(eq(proc), anyString());
        verify(procDao, times(1)).deleteVirtualProc(proc);
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
    public void releasesWhenKillThrowsAndHostNotUp() {
        // The kill throws but the host is no longer Up: confirmed dead, so release is safe.
        doThrow(new RuntimeException("host unreachable")).when(rqdClient)
                .killFrame(any(VirtualProc.class), anyString());
        when(hostDao.isHostUp(any(HostInterface.class))).thenReturn(false);

        dispatchSupport.lostProc(proc, "orphaned", Dispatcher.EXIT_STATUS_FRAME_ORPHAN);

        verify(rqdClient, times(1)).killFrame(eq(proc), anyString());
        verify(procDao, times(1)).deleteVirtualProc(proc);
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
    }

    @Test
    public void skipsRqdKillWhenDisabledByProperty() {
        when(env.getProperty(eq(KILL_BEFORE_RELEASE_PROPERTY), eq(Boolean.class), eq(true)))
                .thenReturn(false);

        dispatchSupport.lostProc(proc, "orphaned", Dispatcher.EXIT_STATUS_FRAME_ORPHAN);

        verify(rqdClient, never()).killFrame(any(VirtualProc.class), anyString());
        verify(procDao, times(1)).deleteVirtualProc(proc);
    }
}
