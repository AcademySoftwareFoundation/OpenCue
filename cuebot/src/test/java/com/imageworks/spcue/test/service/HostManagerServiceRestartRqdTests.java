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
import org.mockito.InOrder;

import com.imageworks.spcue.HostEntity;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.rqd.RqdClient;
import com.imageworks.spcue.rqd.RqdClientException;
import com.imageworks.spcue.service.HostManagerService;

import static org.junit.Assert.fail;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Unit tests for the RQD service restart contract of {@link HostManagerService}: restarts are
 * refused unless the host is UP (protecting pending reboots and repair holds from being clobbered
 * by the restart's boot report), RQD-side failures propagate instead of reporting silent success,
 * and the drain state is written before the RPC (so nothing is booked into the restart window) with
 * UP restored when the request fails.
 */
public class HostManagerServiceRestartRqdTests {

    private HostManagerService hostManager;
    private HostDao hostDao;
    private RqdClient rqdClient;
    private HostInterface host;

    @Before
    public void setUp() {
        hostManager = new HostManagerService();
        hostDao = mock(HostDao.class);
        rqdClient = mock(RqdClient.class);
        hostManager.setHostDao(hostDao);
        hostManager.setRqdClient(rqdClient);

        HostEntity hostEntity = new HostEntity();
        hostEntity.id = "host-id";
        hostEntity.name = "test-host";
        host = hostEntity;
    }

    @Test
    public void restartRqdNowSetsRebootingStateBeforeCallingRqd() {
        when(hostDao.isHostUp(host)).thenReturn(true);

        hostManager.restartRqdNow(host);

        // State must be written before the RPC so the dispatcher cannot book a frame into
        // the restart window while the request is in flight.
        InOrder inOrder = inOrder(hostDao, rqdClient);
        inOrder.verify(hostDao).updateHostState(host, HardwareState.REBOOTING);
        inOrder.verify(rqdClient).restartRqdNow(host);
        verify(hostDao, never()).updateHostState(host, HardwareState.UP);
    }

    @Test
    public void restartRqdWhenIdleSetsRebootWhenIdleStateBeforeCallingRqd() {
        when(hostDao.isHostUp(host)).thenReturn(true);

        hostManager.restartRqdWhenIdle(host);

        InOrder inOrder = inOrder(hostDao, rqdClient);
        inOrder.verify(hostDao).updateHostState(host, HardwareState.REBOOT_WHEN_IDLE);
        inOrder.verify(rqdClient).restartRqdWhenIdle(host);
        verify(hostDao, never()).updateHostState(host, HardwareState.UP);
    }

    @Test
    public void restartRqdNowRefusesWhenHostIsNotUp() {
        when(hostDao.isHostUp(host)).thenReturn(false);

        try {
            hostManager.restartRqdNow(host);
            fail("Expected IllegalStateException for a host that is not UP");
        } catch (IllegalStateException expected) {
            // Expected: the restart must be refused.
        }

        verify(rqdClient, never()).restartRqdNow(any());
        verify(hostDao, never()).updateHostState(any(), any());
    }

    @Test
    public void restartRqdWhenIdleRefusesWhenHostIsNotUp() {
        when(hostDao.isHostUp(host)).thenReturn(false);

        try {
            hostManager.restartRqdWhenIdle(host);
            fail("Expected IllegalStateException for a host that is not UP");
        } catch (IllegalStateException expected) {
            // Expected: the restart must be refused.
        }

        verify(rqdClient, never()).restartRqdWhenIdle(any());
        verify(hostDao, never()).updateHostState(any(), any());
    }

    @Test
    public void restartRqdNowPropagatesRqdFailureAndRestoresUpState() {
        when(hostDao.isHostUp(host)).thenReturn(true);
        doThrow(new RqdClientException("rqd unreachable")).when(rqdClient).restartRqdNow(host);

        try {
            hostManager.restartRqdNow(host);
            fail("Expected the RqdClientException to propagate");
        } catch (RqdClientException expected) {
            // Expected: RQD-side failures must reach the caller.
        }

        // The pre-RPC REBOOTING write must be rolled back so a failed request leaves no
        // residue that would keep the host out of the booking pool.
        InOrder inOrder = inOrder(hostDao);
        inOrder.verify(hostDao).updateHostState(host, HardwareState.REBOOTING);
        inOrder.verify(hostDao).updateHostState(host, HardwareState.UP);
    }

    @Test
    public void restartRqdWhenIdlePropagatesRqdFailureAndRestoresUpState() {
        when(hostDao.isHostUp(host)).thenReturn(true);
        doThrow(new RqdClientException("not supported")).when(rqdClient).restartRqdWhenIdle(host);

        try {
            hostManager.restartRqdWhenIdle(host);
            fail("Expected the RqdClientException to propagate");
        } catch (RqdClientException expected) {
            // Expected: RQD-side failures must reach the caller.
        }

        InOrder inOrder = inOrder(hostDao);
        inOrder.verify(hostDao).updateHostState(host, HardwareState.REBOOT_WHEN_IDLE);
        inOrder.verify(hostDao).updateHostState(host, HardwareState.UP);
    }
}
