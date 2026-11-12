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

package com.imageworks.spcue.test.servant;

import io.grpc.Status;
import io.grpc.stub.StreamObserver;
import org.junit.Before;
import org.junit.Test;

import com.imageworks.spcue.dao.criteria.HostSearchFactory;
import com.imageworks.spcue.grpc.host.HostLockHostsRequest;
import com.imageworks.spcue.grpc.host.HostLockHostsResponse;
import com.imageworks.spcue.grpc.host.HostSearchCriteria;
import com.imageworks.spcue.grpc.host.HostUnlockHostsRequest;
import com.imageworks.spcue.grpc.host.HostUnlockHostsResponse;
import com.imageworks.spcue.grpc.host.NimbyFilter;
import com.imageworks.spcue.servant.ManageHost;
import com.imageworks.spcue.service.HostManager;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

/**
 * Request validation of the bulk LockHosts/UnlockHosts RPCs.
 */
public class ManageHostBulkLockTests {

    private static final HostSearchCriteria NIMBY_ONLY =
            HostSearchCriteria.newBuilder().setNimby(NimbyFilter.NIMBY_ONLY).build();

    private static class CapturingObserver<T> implements StreamObserver<T> {
        T value;
        Throwable error;

        @Override
        public void onNext(T value) {
            this.value = value;
        }

        @Override
        public void onError(Throwable t) {
            error = t;
        }

        @Override
        public void onCompleted() {}
    }

    private ManageHost manageHost;
    private HostManager hostManager;

    @Before
    public void setUp() {
        hostManager = mock(HostManager.class);
        manageHost = new ManageHost();
        manageHost.setHostManager(hostManager);
        manageHost.setHostSearchFactory(new HostSearchFactory());
        when(hostManager.lockHosts(any(), anyBoolean(), any()))
                .thenReturn(HostLockHostsResponse.newBuilder().addLocked("ws-01").build());
        when(hostManager.unlockHosts(any(), any()))
                .thenReturn(HostUnlockHostsResponse.newBuilder().addUnlocked("ws-01").build());
    }

    private CapturingObserver<HostLockHostsResponse> lock(HostSearchCriteria criteria,
            String source) {
        CapturingObserver<HostLockHostsResponse> observer = new CapturingObserver<>();
        manageHost.lockHosts(HostLockHostsRequest.newBuilder().setCriteria(criteria)
                .setSource(source).setKillRunning(true).build(), observer);
        return observer;
    }

    private CapturingObserver<HostUnlockHostsResponse> unlock(HostSearchCriteria criteria,
            String source) {
        CapturingObserver<HostUnlockHostsResponse> observer = new CapturingObserver<>();
        manageHost.unlockHosts(
                HostUnlockHostsRequest.newBuilder().setCriteria(criteria).setSource(source).build(),
                observer);
        return observer;
    }

    private static void assertInvalidArgument(Throwable error) {
        assertEquals(Status.Code.INVALID_ARGUMENT, Status.fromThrowable(error).getCode());
    }

    @Test
    public void rejectsEmptyCriteria() {
        assertInvalidArgument(lock(HostSearchCriteria.getDefaultInstance(), "night").error);
        assertInvalidArgument(unlock(HostSearchCriteria.getDefaultInstance(), "night").error);
        verifyNoInteractions(hostManager);
    }

    @Test
    public void rejectsEmptySource() {
        assertInvalidArgument(lock(NIMBY_ONLY, "").error);
        assertInvalidArgument(unlock(NIMBY_ONLY, "").error);
        verifyNoInteractions(hostManager);
    }

    @Test
    public void rejectsTooLongSource() {
        String tooLong = new String(new char[65]).replace('\0', 'x');
        assertInvalidArgument(lock(NIMBY_ONLY, tooLong).error);
        assertInvalidArgument(unlock(NIMBY_ONLY, tooLong).error);
        verifyNoInteractions(hostManager);
    }

    @Test
    public void nimbyOnlyCountsAsFilter() {
        String maxLength = new String(new char[64]).replace('\0', 'x');
        CapturingObserver<HostLockHostsResponse> observer = lock(NIMBY_ONLY, maxLength);

        assertNull(observer.error);
        assertTrue(observer.value.getLockedList().contains("ws-01"));
        verify(hostManager).lockHosts(any(), eq(true), eq(maxLength));
    }

    @Test
    public void unlockPassesSource() {
        HostSearchCriteria byName = HostSearchCriteria.newBuilder().addHosts("ws-01").build();
        CapturingObserver<HostUnlockHostsResponse> observer = unlock(byName, "night-render");

        assertNull(observer.error);
        verify(hostManager).unlockHosts(any(), eq("night-render"));
    }
}
