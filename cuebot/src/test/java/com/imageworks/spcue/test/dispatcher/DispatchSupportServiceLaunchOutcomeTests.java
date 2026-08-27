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
import org.springframework.core.env.Environment;
import org.springframework.test.util.ReflectionTestUtils;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dao.ProcDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.dispatcher.DispatchSupportService;
import com.imageworks.spcue.rqd.RqdClient;
import com.imageworks.spcue.rqd.RqdClientException;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Unit tests for {@link DispatchSupportService#resolveUnknownLaunchOutcome}: the fail-closed
 * resolution of a dispatch whose launch RPC failed without proving the frame never started. Like
 * the lostProc tests, the method is {@code @Transactional(NOT_SUPPORTED)} and is exercised directly
 * with mocked collaborators.
 */
public class DispatchSupportServiceLaunchOutcomeTests {

    private static final String BUDGET_PROPERTY = "dispatcher.launch_confirm_budget_ms";
    private static final long BUDGET_DEFAULT = 20000L;
    private static final String POLL_INTERVAL_PROPERTY =
            "dispatcher.launch_confirm_poll_interval_ms";
    private static final long POLL_INTERVAL_DEFAULT = 7000L;

    private DispatchSupportService dispatchSupport;
    private RqdClient rqdClient;
    private ProcDao procDao;
    private FrameDao frameDao;
    private Environment env;
    private VirtualProc proc;
    private DispatchFrame frame;

    @Before
    public void setup() {
        dispatchSupport = new DispatchSupportService();
        rqdClient = mock(RqdClient.class);
        procDao = mock(ProcDao.class);
        frameDao = mock(FrameDao.class);
        env = mock(Environment.class);

        dispatchSupport.setRqdClient(rqdClient);
        dispatchSupport.setProcDao(procDao);
        dispatchSupport.setFrameDao(frameDao);
        dispatchSupport.setHostDao(mock(HostDao.class));
        dispatchSupport.setShowDao(mock(ShowDao.class));
        dispatchSupport.setJobDao(mock(JobDao.class));
        dispatchSupport.setLayerDao(mock(LayerDao.class));
        ReflectionTestUtils.setField(dispatchSupport, "env", env);

        when(env.getProperty(eq(BUDGET_PROPERTY), eq(Long.class), eq(BUDGET_DEFAULT)))
                .thenReturn(BUDGET_DEFAULT);
        // Keep the tests fast: the interval only exists to let a delivered launch surface.
        setPollInterval(1L);

        proc = new VirtualProc();
        proc.id = "00000000-0000-0000-0000-000000000001";
        proc.frameId = "00000000-0000-0000-0000-0000000000f1";
        proc.hostName = "test-host";

        frame = new DispatchFrame();
        frame.id = proc.frameId;
        frame.name = "0001-test_layer";

        when(procDao.deleteVirtualProc(any(VirtualProc.class))).thenReturn(true);

        when(frameDao.updateFrameClearedIfRunning(frame)).thenReturn(true);
    }

    private void setBudget(long budgetMs) {
        when(env.getProperty(eq(BUDGET_PROPERTY), eq(Long.class), eq(BUDGET_DEFAULT)))
                .thenReturn(budgetMs);
    }

    private void setPollInterval(long pollIntervalMs) {
        when(env.getProperty(eq(POLL_INTERVAL_PROPERTY), eq(Long.class), eq(POLL_INTERVAL_DEFAULT)))
                .thenReturn(pollIntervalMs);
    }

    @Test
    public void keepsBookingWhenFrameIsRunning() {
        when(rqdClient.isFrameRunning(proc.hostName, frame.getFrameId())).thenReturn(true);

        assertFalse(dispatchSupport.resolveUnknownLaunchOutcome(proc, frame));

        verify(procDao, never()).deleteVirtualProc(any(VirtualProc.class));
        verify(frameDao, never()).updateFrameClearedIfRunning(any());
        verify(rqdClient, never()).killFrame(any(VirtualProc.class), anyString());
    }

    @Test
    public void releasesBookingWhenFrameConfirmedNotRunning() {
        when(rqdClient.isFrameRunning(proc.hostName, frame.getFrameId())).thenReturn(false);

        assertTrue(dispatchSupport.resolveUnknownLaunchOutcome(proc, frame));

        // Confirmation requires two polls before the release.
        verify(rqdClient, times(2)).isFrameRunning(proc.hostName, frame.getFrameId());
        verify(procDao, times(1)).deleteVirtualProc(proc);
        verify(frameDao, times(1)).updateFrameClearedIfRunning(frame);
        verify(rqdClient, never()).killFrame(any(VirtualProc.class), anyString());
    }

    @Test
    public void leavesFrameAloneWhenItCompletedDuringConfirmation() {
        // The frame ran, finished and was reaped by RQD while we polled: it polls as not running,
        // but resetting it would re-render finished work.
        when(rqdClient.isFrameRunning(proc.hostName, frame.getFrameId())).thenReturn(false);
        when(frameDao.updateFrameClearedIfRunning(frame)).thenReturn(false);

        assertTrue(dispatchSupport.resolveUnknownLaunchOutcome(proc, frame));

        verify(procDao, times(1)).deleteVirtualProc(proc);
    }

    @Test
    public void keepsBookingWhenFrameStartsBetweenPolls() {
        // First poll races ahead of a delivered-but-unprocessed launch; the second sees it.
        when(rqdClient.isFrameRunning(proc.hostName, frame.getFrameId())).thenReturn(false)
                .thenReturn(true);

        assertFalse(dispatchSupport.resolveUnknownLaunchOutcome(proc, frame));

        verify(procDao, never()).deleteVirtualProc(any(VirtualProc.class));
        verify(frameDao, never()).updateFrameClearedIfRunning(any());
    }

    @Test
    public void keepsBookingWhenStateCannotBeConfirmed() {
        when(rqdClient.isFrameRunning(proc.hostName, frame.getFrameId()))
                .thenThrow(new RqdClientException("host unreachable"));

        assertFalse(dispatchSupport.resolveUnknownLaunchOutcome(proc, frame));

        verify(procDao, never()).deleteVirtualProc(any(VirtualProc.class));
        verify(frameDao, never()).updateFrameClearedIfRunning(any());
    }

    @Test
    public void keepsBookingWhenSecondPollCannotBeConfirmed() {
        when(rqdClient.isFrameRunning(proc.hostName, frame.getFrameId())).thenReturn(false)
                .thenThrow(new RqdClientException("host unreachable"));

        assertFalse(dispatchSupport.resolveUnknownLaunchOutcome(proc, frame));

        verify(procDao, never()).deleteVirtualProc(any(VirtualProc.class));
        verify(frameDao, never()).updateFrameClearedIfRunning(any());
    }

    @Test
    public void keepsBookingWhenBudgetExpiresBeforeConfirmation() {
        // A budget shorter than the poll interval cannot fit the second poll: fail closed.
        setPollInterval(10000L);
        setBudget(1L);
        when(rqdClient.isFrameRunning(proc.hostName, frame.getFrameId())).thenReturn(false);

        assertFalse(dispatchSupport.resolveUnknownLaunchOutcome(proc, frame));

        verify(rqdClient, times(1)).isFrameRunning(proc.hostName, frame.getFrameId());
        verify(procDao, never()).deleteVirtualProc(any(VirtualProc.class));
        verify(frameDao, never()).updateFrameClearedIfRunning(any());
    }

    @Test
    public void nonPositiveBudgetRestoresLegacyRelease() {
        setBudget(0L);

        assertTrue(dispatchSupport.resolveUnknownLaunchOutcome(proc, frame));

        verify(rqdClient, never()).isFrameRunning(anyString(), anyString());
        verify(procDao, times(1)).deleteVirtualProc(proc);
        verify(frameDao, times(1)).updateFrameClearedIfRunning(frame);
        verify(rqdClient, times(1)).killFrame(eq(proc), anyString());
    }

    @Test
    public void legacyReleaseSwallowsKillFailure() {
        setBudget(-1L);
        org.mockito.Mockito.doThrow(new RqdClientException("kill failed")).when(rqdClient)
                .killFrame(any(VirtualProc.class), anyString());

        assertTrue(dispatchSupport.resolveUnknownLaunchOutcome(proc, frame));

        verify(procDao, times(1)).deleteVirtualProc(proc);
        verify(frameDao, times(1)).updateFrameClearedIfRunning(frame);
    }
}
