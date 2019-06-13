
/*
 * Copyright (c) 2018 Sony Pictures Imageworks Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */


package com.imageworks.spcue.test.dispatcher;

import com.imageworks.spcue.*;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.ProcDao;
import com.imageworks.spcue.dao.criteria.ProcSearchFactory;
import com.imageworks.spcue.dao.criteria.ProcSearchInterface;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.RedirectManager;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.host.ProcSearchCriteria;
import com.imageworks.spcue.grpc.host.RedirectType;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.*;
import com.imageworks.spcue.util.Convert;
import org.junit.Before;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import java.io.File;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;

import static org.hamcrest.Matchers.is;
import static org.hamcrest.Matchers.isEmptyString;
import static org.junit.Assert.*;


/**
 * Tests for the redirect manager.
 */
@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class RedirectManagerTests
    extends AbstractTransactionalJUnit4SpringContextTests {

    @Autowired
    RedirectManager redirectManager;

    @Autowired
    RedirectService redirectService;

    @Autowired
    JobManager jobManager;

    @Autowired
    JobLauncher jobLauncher;

    @Autowired
    HostManager hostManager;

    @Autowired
    AdminManager adminManager;

    @Autowired
    Dispatcher dispatcher;

    @Autowired
    GroupManager groupManager;

    @Autowired
    ProcDao procDao;

    @Autowired
    JobDao jobDao;

    @Autowired
    Whiteboard whiteboard;
    
    @Autowired
    ProcSearchFactory procSearchFactory;

    private static final String HOSTNAME = "beta";

    private static final String JOBNAME =
        "pipe-dev.cue-testuser_shell_dispatch_test_v1";

    private static final String TARGET_JOB =
        "pipe-dev.cue-testuser_shell_dispatch_test_v2";

    @Before
    public void launchJob() {
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_dispatch_test.xml"));
    }

    @Before
    public void setTestMode() {
        dispatcher.setTestMode(true);
    }

    @Before
    public void createHost() {
        RenderHost host = RenderHost.newBuilder()
                .setName(HOSTNAME)
                .setBootTime(1192369572)
                .setFreeMcp(76020)
                .setFreeMem(53500)
                .setFreeSwap(20760)
                .setLoad(1)
                .setTotalMcp(195430)
                .setTotalMem(8173264)
                .setTotalSwap(20960)
                .setNimbyEnabled(false)
                .setNumProcs(1)
                .setCoresPerProc(100)
                .setState(HardwareState.UP)
                .setFacility("spi")
                .addTags("test")
                .putAttributes("SP_OS", "Linux")
                .build();

        hostManager.createHost(host,
                adminManager.findAllocationDetail("spi", "general"));
    }

    public JobDetail getJob() {
        return jobManager.findJobDetail(JOBNAME);
    }

    public JobDetail getTargetJob() {
        return jobManager.findJobDetail(TARGET_JOB);
    }


    public DispatchHost getHost() {
        return hostManager.findDispatchHost(HOSTNAME);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testAddJobRedirectByCriteria() {

        JobDetail job = getJob();
        DispatchHost host = getHost();

        List<VirtualProc> procs = dispatcher.dispatchHost(host, job);
        assertEquals(1, procs.size());
        VirtualProc proc = procs.get(0);

        /* Setup a proc search */
        ProcSearchInterface search = procSearchFactory.create();
        ProcSearchCriteria criteria = search.getCriteria();
        search.setCriteria(criteria.toBuilder().addJobs(job.getName()).build());

        List<JobInterface> jobs = new ArrayList<JobInterface>(1);
        jobs.add(jobManager.findJob(TARGET_JOB));

        /* Now redirect this proc to the other job */
        redirectManager.addRedirect(
                search.getCriteria(),
                jobs,
                false,
                new Source());

        /* Test that the redirect was added properly. */
        assertTrue(redirectManager.hasRedirect(procs.get(0)));

        /* Check to ensure the redirect target was set. */
        assertEquals(TARGET_JOB, whiteboard.getProcs(search).getProcs(0).getRedirectTarget());

        redirectManager.removeRedirect(proc);
        assertFalse(redirectManager.hasRedirect(proc));
        assertThat(
                whiteboard.getProcs(search).getProcs(0).getRedirectTarget(),
                is(isEmptyString()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testAddGroupRedirectByCriteria() {

        JobDetail job = getJob();
        DispatchHost host = getHost();

        List<VirtualProc> procs = dispatcher.dispatchHost(host, job);
        assertEquals(1, procs.size());
        VirtualProc proc = procs.get(0);

        // Double check there is a proc.
        procDao.getVirtualProc(proc.getId());

        /* Setup a proc search */
        ProcSearchInterface search = procSearchFactory.create();
        ProcSearchCriteria criteria = search.getCriteria();
        search.setCriteria(criteria.toBuilder().addJobs(job.getName()).build());

        GroupInterface root  = groupManager.getRootGroupDetail(job);
        GroupDetail group = new GroupDetail();
        group.name = "Foo";
        group.showId = root.getShowId();

        groupManager.createGroup(group, root);

        /* Now redirect this proc to the other job */
        redirectManager.addRedirect(
                search.getCriteria(),
                group,
                false,
                new Source());

        /* Test that the redirect was added properly. */
        assertTrue(redirectManager.hasRedirect(procs.get(0)));

        /* Check to ensure the redirect target was set. */
        assertEquals(group.getName(), whiteboard.getProcs(search).getProcs(0).getRedirectTarget());

        redirectManager.removeRedirect(proc);
        assertFalse(redirectManager.hasRedirect(proc));
        assertThat(
                whiteboard.getProcs(search).getProcs(0).getRedirectTarget(),
                is(isEmptyString()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testAddJobRedirect() {

        JobDetail job = getJob();
        JobDetail target = getTargetJob();
        DispatchHost host = getHost();

        List<VirtualProc> procs = dispatcher.dispatchHost(host, job);
        assertEquals(1, procs.size());
        VirtualProc proc = procs.get(0);

        ProcSearchInterface search = procSearchFactory.create();
        search.setCriteria(ProcSearchCriteria.newBuilder().addJobs(job.getName()).build());

        assertTrue(redirectManager.addRedirect(proc, target,
                false, new Source()));

        assertTrue(redirectManager.hasRedirect(proc));
        assertEquals(TARGET_JOB, whiteboard.getProcs(search).getProcs(0).getRedirectTarget());

        redirectManager.removeRedirect(proc);
        assertFalse(redirectManager.hasRedirect(proc));
        assertThat(
                whiteboard.getProcs(search).getProcs(0).getRedirectTarget(),
                is(isEmptyString()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testAddGroupRedirect() {

        JobDetail job = getJob();
        JobDetail target = getTargetJob();
        DispatchHost host = getHost();

        /* Find the root group and move our target job there. */
        GroupDetail group = groupManager.getRootGroupDetail(job);
        groupManager.reparentJob(target,
                group,
                new Inherit[] { });

        assertEquals(group.getId(),
                groupManager.getGroupDetail(target).getId());

        List<VirtualProc> procs = dispatcher.dispatchHost(host, job);
        assertEquals(1, procs.size());
        VirtualProc proc = procs.get(0);

        ProcSearchInterface search = procSearchFactory.create();
        search.setCriteria(ProcSearchCriteria.newBuilder().addJobs(job.getName()).build());

        assertEquals(group.getGroupId(), jobDao.getJobDetail(target.getJobId()).groupId);

        assertTrue(redirectManager.addRedirect(proc, group, false, new Source()));

        assertTrue(redirectManager.hasRedirect(proc));
        assertEquals(group.getName(), whiteboard.getProcs(search).getProcs(0).getRedirectTarget());

        redirectManager.removeRedirect(proc);
        assertFalse(redirectManager.hasRedirect(proc));
        assertThat(
                whiteboard.getProcs(search).getProcs(0).getRedirectTarget(),
                is(isEmptyString()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testJobRedirect() {

        JobDetail job = getJob();
        JobDetail target = getTargetJob();
        DispatchHost host = getHost();

        List<VirtualProc> procs = dispatcher.dispatchHost(host, job);
        assertEquals(1, procs.size());
        VirtualProc proc = procs.get(0);

        ProcSearchInterface search = procSearchFactory.create();
        search.setCriteria(ProcSearchCriteria.newBuilder().addJobs(job.getName()).build());

        assertTrue(redirectManager.addRedirect(proc, target,
                false, new Source()));

        assertTrue(redirectManager.hasRedirect(proc));
        assertEquals(TARGET_JOB, whiteboard.getProcs(search).getProcs(0).getRedirectTarget());

        assertTrue(redirectManager.redirect(proc));

        assertEquals(
                Convert.coreUnitsToCores(100),
                whiteboard.getJob(target.getJobId()).getJobStats().getReservedCores(),
                0);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGroupRedirect() {

        JobDetail job = getJob();
        JobDetail target = getTargetJob();
        DispatchHost host = getHost();

        /* Find the root group and move our target job there. */
        GroupDetail group = groupManager.getRootGroupDetail(job);
        groupManager.reparentJob(target,
                group,
                new Inherit[] { });

        assertEquals(group.getId(),
                groupManager.getGroupDetail(target).getId());

        List<VirtualProc> procs = dispatcher.dispatchHost(host, job);
        assertEquals(1, procs.size());
        VirtualProc proc = procs.get(0);

        ProcSearchInterface search = procSearchFactory.create();
        search.setCriteria(ProcSearchCriteria.newBuilder().addJobs(job.getName()).build());

        assertEquals(group.getGroupId(), jobDao.getJobDetail(target.getJobId()).groupId);

        assertTrue(redirectManager.addRedirect(proc, group,
                false, new Source()));

        assertTrue(redirectManager.hasRedirect(proc));
        assertEquals(
                group.getName(), whiteboard.getProcs(search).getProcs(0).getRedirectTarget());

        redirectManager.redirect(proc);

        assertEquals(
                Convert.coreUnitsToCores(100),
                whiteboard.getGroup(group.getGroupId()).getGroupStats().getReservedCores(),
                0);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testNonExistentRedirect() {
        JobDetail job = getJob();
        DispatchHost host = getHost();

        List<VirtualProc> procs = dispatcher.dispatchHost(host, job);
        assertEquals(1, procs.size());
        VirtualProc proc = procs.get(0);

        assertFalse(redirectManager.hasRedirect(proc));

        // This should not throw any exception.
        assertFalse(redirectManager.redirect(proc));
    }

    /**
     * Test that parallel attempts to save a redirect with the
     * same key succeed without throwing an exception.
     */
    @Test
    @Transactional
    @Rollback(true)
    public void testParallelPuts() {
        final int N = 20;

        CountDownLatch startSignal = new CountDownLatch(1);
        CountDownLatch stopSignal = new CountDownLatch(N);

        final String redirect_key = "test";

        Redirect redirect = new Redirect(RedirectType.JOB_REDIRECT, "foo", "bar");

        for (int i = 0; i < N; i++) {
            new Thread(new Runnable() {
                @Override
                public void run() {
                    try {
                        try {
                            startSignal.await();
                        }
                        catch (InterruptedException e) {
                            throw new RuntimeException("Failed to wait for start signal", e);
                        }

                        // This should not throw anything...
                        redirectService.put(redirect_key, redirect);
                    }
                    finally {
                        stopSignal.countDown();
                    }
                }
            }).start();
        }

        // Start all the threads at roughly the same time.
        try {
            startSignal.countDown();
            try {
                stopSignal.await();
            }
            catch (InterruptedException e) {
                throw new RuntimeException("Failed to wait for stop signal", e);
            }
        }
        finally {
            // Clean up after test.
            redirectService.remove(redirect_key);
        }
    }
}

