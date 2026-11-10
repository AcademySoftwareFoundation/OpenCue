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

import java.util.Arrays;
import java.util.Collections;

import org.junit.Before;
import org.junit.Test;
import org.mockito.InOrder;

import com.imageworks.spcue.HostEntity;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dao.criteria.HostSearchInterface;
import com.imageworks.spcue.grpc.host.HostLockHostsResponse;
import com.imageworks.spcue.grpc.host.HostUnlockHostsResponse;
import com.imageworks.spcue.grpc.host.LockState;
import com.imageworks.spcue.rqd.RqdClient;
import com.imageworks.spcue.rqd.RqdClientException;
import com.imageworks.spcue.service.HostManagerService;
import com.imageworks.spcue.service.JobManagerSupport;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

/**
 * Unit tests for {@link HostManagerService#lockHosts} and {@link HostManagerService#unlockHosts}.
 * The conditional lock updates themselves are covered by HostDaoTests.
 */
public class HostManagerBulkLockTests {

    private static final Source NIGHT_RENDER = HostManagerService.bulkLockSource("night-render");

    private HostManagerService hostManager;
    private HostDao hostDao;
    private RqdClient rqdClient;
    private JobManagerSupport jobManagerSupport;
    private HostSearchInterface search;

    @Before
    public void setUp() {
        hostManager = new HostManagerService();
        hostDao = mock(HostDao.class);
        rqdClient = mock(RqdClient.class);
        jobManagerSupport = mock(JobManagerSupport.class);
        search = mock(HostSearchInterface.class);
        hostManager.setHostDao(hostDao);
        hostManager.setRqdClient(rqdClient);
        hostManager.setJobManagerSupport(jobManagerSupport);
        when(jobManagerSupport.killForHostLock(any(), any()))
                .thenReturn(new JobManagerSupport.HostLockKillResult());
    }

    private HostEntity host(String name) {
        HostEntity host = new HostEntity();
        host.id = name + "-id";
        host.name = name;
        return host;
    }

    private static Source eqSource(Source source) {
        return argThat(s -> s.toString().equals(source.toString()));
    }

    @Test
    public void bulkLockSourceIsPrefixed() {
        assertTrue(NIGHT_RENDER.toString().endsWith("\nHostApi:night-render"));
    }

    @Test
    public void locksOnlyMatchedHostsAndLocksRqdBeforeKilling() {
        HostEntity ws = host("ws-01");
        when(hostDao.findHosts(search)).thenReturn(Collections.singletonList(ws));
        when(hostDao.lockHostIfNotLockedByOther(eq(ws), eqSource(NIGHT_RENDER))).thenReturn(true);
        JobManagerSupport.HostLockKillResult kill = new JobManagerSupport.HostLockKillResult();
        kill.framesKilled = 2;
        when(jobManagerSupport.killForHostLock(eq(ws), any())).thenReturn(kill);

        HostLockHostsResponse response = hostManager.lockHosts(search, true, "night-render");

        assertEquals(Collections.singletonList("ws-01"), response.getLockedList());
        assertEquals(2, response.getFramesKilled());
        InOrder inOrder = inOrder(hostDao, rqdClient, jobManagerSupport);
        inOrder.verify(hostDao).lockHostIfNotLockedByOther(eq(ws), eqSource(NIGHT_RENDER));
        inOrder.verify(rqdClient).setHostLock(ws, LockState.LOCKED);
        inOrder.verify(jobManagerSupport).killForHostLock(eq(ws), eqSource(NIGHT_RENDER));
    }

    @Test
    public void lockWithoutKillDoesNotKill() {
        HostEntity ws = host("ws-01");
        when(hostDao.findHosts(search)).thenReturn(Collections.singletonList(ws));
        when(hostDao.lockHostIfNotLockedByOther(eq(ws), any())).thenReturn(true);

        HostLockHostsResponse response = hostManager.lockHosts(search, false, "night-render");

        assertEquals(Collections.singletonList("ws-01"), response.getLockedList());
        verifyNoInteractions(jobManagerSupport);
    }

    @Test
    public void hostLockedByAnotherSourceIsSkipped() {
        HostEntity ws = host("ws-01");
        when(hostDao.findHosts(search)).thenReturn(Collections.singletonList(ws));
        when(hostDao.lockHostIfNotLockedByOther(eq(ws), any())).thenReturn(false);

        HostLockHostsResponse response = hostManager.lockHosts(search, true, "night-render");

        assertEquals(Collections.singletonList("ws-01"), response.getSkippedList());
        assertEquals(0, response.getLockedCount());
        verifyNoInteractions(rqdClient);
        verifyNoInteractions(jobManagerSupport);
        verify(hostDao, never()).updateHostLock(any(), any(), any());
    }

    @Test
    public void unreachableRqdKeepsDbLockAndStillKills() {
        HostEntity ws = host("ws-01");
        when(hostDao.findHosts(search)).thenReturn(Collections.singletonList(ws));
        when(hostDao.lockHostIfNotLockedByOther(eq(ws), any())).thenReturn(true);
        doThrow(new RqdClientException("unreachable")).when(rqdClient).setHostLock(ws,
                LockState.LOCKED);
        JobManagerSupport.HostLockKillResult kill = new JobManagerSupport.HostLockKillResult();
        kill.framesDeferred.add("0001-render");
        when(jobManagerSupport.killForHostLock(eq(ws), any())).thenReturn(kill);

        HostLockHostsResponse response = hostManager.lockHosts(search, true, "night-render");

        assertEquals(Collections.singletonList("ws-01"), response.getUnreachableList());
        assertEquals(0, response.getLockedCount());
        assertEquals(Collections.singletonList("0001-render"), response.getFramesDeferredList());
        verify(hostDao, never()).updateHostLock(any(), any(), any());
        verify(hostDao, never()).unlockHostIfLockedBy(any(), any());
    }

    @Test
    public void lockAggregatesOutcomesInHostOrder() {
        HostEntity a = host("ws-01");
        HostEntity b = host("ws-02");
        HostEntity c = host("ws-03");
        when(hostDao.findHosts(search)).thenReturn(Arrays.asList(a, b, c));
        when(hostDao.lockHostIfNotLockedByOther(any(), any())).thenReturn(true);
        when(hostDao.lockHostIfNotLockedByOther(eq(b), any())).thenReturn(false);

        HostLockHostsResponse response = hostManager.lockHosts(search, false, "night-render");

        assertEquals(Arrays.asList("ws-01", "ws-03"), response.getLockedList());
        assertEquals(Collections.singletonList("ws-02"), response.getSkippedList());
    }

    @Test
    public void unlocksOnlySameSourceLockedHosts() {
        HostEntity mine = host("ws-01");
        HostEntity other = host("ws-02");
        when(hostDao.findHosts(search)).thenReturn(Arrays.asList(mine, other));
        when(hostDao.unlockHostIfLockedBy(eq(mine), eqSource(NIGHT_RENDER))).thenReturn(true);
        when(hostDao.unlockHostIfLockedBy(eq(other), any())).thenReturn(false);

        HostUnlockHostsResponse response = hostManager.unlockHosts(search, "night-render");

        assertEquals(Collections.singletonList("ws-01"), response.getUnlockedList());
        assertEquals(Collections.singletonList("ws-02"), response.getSkippedList());
        verify(rqdClient).setHostLock(mine, LockState.OPEN);
        verify(rqdClient, never()).setHostLock(eq((HostInterface) other), any());
    }

    @Test
    public void unlockReportsUnreachableRqd() {
        HostEntity ws = host("ws-01");
        when(hostDao.findHosts(search)).thenReturn(Collections.singletonList(ws));
        when(hostDao.unlockHostIfLockedBy(eq(ws), any())).thenReturn(true);
        doThrow(new RqdClientException("unreachable")).when(rqdClient).setHostLock(ws,
                LockState.OPEN);

        HostUnlockHostsResponse response = hostManager.unlockHosts(search, "night-render");

        assertEquals(Collections.singletonList("ws-01"), response.getUnreachableList());
    }

    @Test
    public void noMatchingHostsReturnsEmptyResponse() {
        when(hostDao.findHosts(search)).thenReturn(Collections.emptyList());

        HostLockHostsResponse response = hostManager.lockHosts(search, true, "night-render");

        assertEquals(HostLockHostsResponse.getDefaultInstance(), response);
        verifyNoInteractions(rqdClient);
    }
}
