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

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;
import javax.annotation.Resource;
import javax.sql.DataSource;

import com.google.common.collect.ImmutableList;
import org.junit.After;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.test.util.AopTestUtils;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.transaction.support.TransactionTemplate;

import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.host.LockState;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.rqd.RqdClient;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.HostManagerService;
import com.imageworks.spcue.test.AssumingPostgresEngine;
import com.imageworks.spcue.util.CueUtil;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;

/**
 * Checks through the Spring proxy that an operator lock is committed before RQD is called, so the
 * host row is not held locked while the RPC is in flight. Runs outside the test-managed transaction
 * so a second connection can observe the committed row; the fixture host is created and deleted for
 * real.
 */
@ContextConfiguration(classes = TestAppConfig.class, loader = AnnotationConfigContextLoader.class)
public class HostManagerLockCommitTests extends AbstractJUnit4SpringContextTests {

    private static final String HOST = "lock_commit_host";

    @Autowired
    @Rule
    public AssumingPostgresEngine assumingPostgresEngine;

    @Resource
    HostManager hostManager;

    @Resource
    HostDao hostDao;

    @Resource
    AdminManager adminManager;

    @Resource
    DataSource dataSource;

    @Resource
    PlatformTransactionManager transactionManager;

    private HostManagerService target;
    private RqdClient originalRqdClient;
    private HostInterface host;

    @Before
    public void setUp() {
        RenderHost rh =
                RenderHost.newBuilder().setName(HOST).setBootTime(1192369572).setFreeMcp(CueUtil.GB)
                        .setFreeMem(15290520).setFreeSwap(2076).setLoad(1).setTotalMcp(CueUtil.GB4)
                        .setTotalMem((int) CueUtil.GB16).setTotalSwap(2076).setNimbyEnabled(false)
                        .setNumProcs(2).setCoresPerProc(400).setState(HardwareState.UP)
                        .setFacility("spi").addAllTags(ImmutableList.of("linux", "64bit")).build();
        hostDao.insertRenderHost(rh, adminManager.findAllocationDetail("spi", "general"), false);
        host = hostDao.findHost(HOST);

        target = AopTestUtils.getUltimateTargetObject(hostManager);
        originalRqdClient = target.getRqdClient();
    }

    @After
    public void tearDown() {
        if (target != null) {
            target.setRqdClient(originalRqdClient);
        }
        if (host != null) {
            hostDao.deleteHost(host);
        }
    }

    @Test
    public void setHostLockCommitsBeforeCallingRqd() {
        AtomicBoolean txActiveDuringRpc = new AtomicBoolean(true);
        AtomicReference<String> seenByOtherConnection = new AtomicReference<>();
        RqdClient rqdClient = mock(RqdClient.class);
        doAnswer(invocation -> {
            txActiveDuringRpc.set(TransactionSynchronizationManager.isActualTransactionActive());
            // A raw connection, not the one bound to this thread, so only committed rows
            // are visible.
            try (Connection conn = dataSource.getConnection();
                    PreparedStatement ps = conn
                            .prepareStatement("SELECT str_lock_state FROM host WHERE pk_host=?")) {
                ps.setString(1, host.getHostId());
                try (ResultSet rs = ps.executeQuery()) {
                    rs.next();
                    seenByOtherConnection.set(rs.getString(1));
                }
            }
            return null;
        }).when(rqdClient).setHostLock(any(), any());
        target.setRqdClient(rqdClient);

        // A caller's own transaction is suspended too, not extended across the RPC.
        new TransactionTemplate(transactionManager).executeWithoutResult(
                status -> hostManager.setHostLock(host, LockState.LOCKED, new Source("HostApi")));

        assertFalse(txActiveDuringRpc.get());
        assertEquals(LockState.LOCKED.toString(), seenByOtherConnection.get());
    }
}
