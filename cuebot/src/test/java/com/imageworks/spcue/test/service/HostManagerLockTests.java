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
import com.imageworks.spcue.Source;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.grpc.host.LockState;
import com.imageworks.spcue.rqd.RqdClient;
import com.imageworks.spcue.rqd.RqdClientException;
import com.imageworks.spcue.service.HostManagerService;

import static org.junit.Assert.fail;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;

/**
 * Unit tests for the host lock contract of {@link HostManagerService}: operator locks write the DB
 * before calling RQD and keep the DB state when the RPC fails, while report-driven syncs never call
 * RQD.
 */
public class HostManagerLockTests {

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
    public void setHostLockWritesDbBeforeCallingRqd() {
        Source source = new Source("HostApi");

        hostManager.setHostLock(host, LockState.LOCKED, source);

        InOrder inOrder = inOrder(hostDao, rqdClient);
        inOrder.verify(hostDao).updateHostLock(host, LockState.LOCKED, source);
        inOrder.verify(rqdClient).setHostLock(host, LockState.LOCKED);
    }

    @Test
    public void setHostLockKeepsDbStateWhenRqdFails() {
        Source source = new Source("HostApi");
        doThrow(new RqdClientException("rqd unreachable")).when(rqdClient).setHostLock(host,
                LockState.LOCKED);

        try {
            hostManager.setHostLock(host, LockState.LOCKED, source);
            fail("Expected the RqdClientException to propagate");
        } catch (RqdClientException expected) {
            // Expected: the operator must learn RQD did not apply the lock.
        }

        // No compensating write: the lock stays in the DB so the host is not booked.
        verify(hostDao, times(1)).updateHostLock(any(), any(), any());
        verify(hostDao).updateHostLock(host, LockState.LOCKED, source);
    }

    @Test
    public void syncHostLockNeverCallsRqd() {
        Source source = new Source("NIMBY");

        hostManager.syncHostLock(host, LockState.NIMBY_LOCKED, source);
        hostManager.syncHostLock(host, LockState.OPEN, source);

        verify(hostDao).updateHostLock(host, LockState.NIMBY_LOCKED, source);
        verify(hostDao).updateHostLock(host, LockState.OPEN, source);
        verifyNoInteractions(rqdClient);
    }
}
