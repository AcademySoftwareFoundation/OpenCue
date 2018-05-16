
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

import static org.junit.Assert.*;

import java.io.File;
import java.util.concurrent.CountDownLatch;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;

import javax.annotation.Resource;

import org.junit.Before;
import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.Group;
import com.imageworks.spcue.GroupDetail;
import com.imageworks.spcue.Inherit;
import com.imageworks.spcue.Job;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.Redirect;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.CueIce.RedirectType;
import com.imageworks.spcue.CueIce.HardwareState;
import com.imageworks.spcue.RqdIce.RenderHost;
import com.imageworks.spcue.dao.criteria.ProcSearch;
import com.imageworks.spcue.dispatcher.DispatchSupport;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.RedirectManager;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.GroupManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.RedirectService;


/**
 * Tests for the redirect manager.
 */
@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class RedirectManagerTests
    extends AbstractTransactionalJUnit4SpringContextTests {

    @Resource
    RedirectManager redirectManager;

    @Resource
    RedirectService redirectService;

    @Resource
    JobManager jobManager;

    @Resource
    JobLauncher jobLauncher;

    @Resource
    HostManager hostManager;

    @Resource
    AdminManager adminManager;

    @Resource
    Dispatcher dispatcher;

    @Resource
    DispatchSupport dispatchSupport;

    @Resource
    GroupManager groupManager;

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
        RenderHost host = new RenderHost();
        host.name = HOSTNAME;
        host.bootTime = 1192369572;
        host.freeMcp = 76020;
        host.freeMem = 53500;
        host.freeSwap = 20760;
        host.load = 1;
        host.totalMcp = 195430;
        host.totalMem = 8173264;
        host.totalSwap = 20960;
        host.nimbyEnabled = false;
        host.numProcs = 1;
        host.coresPerProc = 100;
        host.tags = new ArrayList<String>();
        host.tags.add("test");
        host.state = HardwareState.Up;
        host.facility = "spi";
        host.attributes = new HashMap<String, String>();
        host.attributes.put("SP_OS", "spinux1");

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
        ProcSearch search = new ProcSearch();
        search.getCriteria().jobs.add(job.getName());

        List<Job> jobs = new ArrayList<Job>(1);
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
        assertEquals(TARGET_JOB, jdbcTemplate.queryForObject(
                "SELECT str_redirect FROM proc WHERE pk_proc=?",
                String.class, proc.getId()));

        redirectManager.removeRedirect(proc);
        assertFalse(redirectManager.hasRedirect(proc));
        assertNull(jdbcTemplate.queryForObject(
                "SELECT str_redirect FROM proc WHERE pk_proc=?",
                String.class, proc.getId()));
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
        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM proc WHERE pk_proc=?",
                Integer.class, proc.getId()));

        /* Setup a proc search */
        ProcSearch search = new ProcSearch();
        search.getCriteria().jobs.add(job.getName());

        Group root  = groupManager.getRootGroupDetail(job);
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
        assertEquals(group.getName(), jdbcTemplate.queryForObject(
                "SELECT str_redirect FROM proc WHERE pk_proc=?",
                String.class, proc.getId()));

        redirectManager.removeRedirect(proc);
        assertFalse(redirectManager.hasRedirect(proc));
        assertNull(jdbcTemplate.queryForObject(
                "SELECT str_redirect FROM proc WHERE pk_proc=?",
                String.class, proc.getId()));
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

        assertTrue(redirectManager.addRedirect(proc, target,
                false, new Source()));

        assertTrue(redirectManager.hasRedirect(proc));
        assertEquals(TARGET_JOB, jdbcTemplate.queryForObject(
                "SELECT str_redirect FROM proc WHERE pk_proc=?",
                String.class, proc.getId()));

        redirectManager.removeRedirect(proc);
        assertFalse(redirectManager.hasRedirect(proc));
        assertNull(jdbcTemplate.queryForObject(
                "SELECT str_redirect FROM proc WHERE pk_proc=?",
                String.class, proc.getId()));
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

        assertEquals(group.getGroupId(), jdbcTemplate.queryForObject(
                "SELECT pk_folder FROM job WHERE pk_job=?", String.class,
                target.getJobId()));

        assertTrue(redirectManager.addRedirect(proc, group,
                false, new Source()));

        assertTrue(redirectManager.hasRedirect(proc));
        assertEquals(group.getName(), jdbcTemplate.queryForObject(
                "SELECT str_redirect FROM proc WHERE pk_proc=?",
                String.class, proc.getId()));

        redirectManager.removeRedirect(proc);
        assertFalse(redirectManager.hasRedirect(proc));
        assertNull(jdbcTemplate.queryForObject(
                "SELECT str_redirect FROM proc WHERE pk_proc=?",
                String.class, proc.getId()));
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

        assertTrue(redirectManager.addRedirect(proc, target,
                false, new Source()));

        assertTrue(redirectManager.hasRedirect(proc));
        assertEquals(TARGET_JOB, jdbcTemplate.queryForObject(
                "SELECT str_redirect FROM proc WHERE pk_proc=?",
                String.class, proc.getId()));

        assertTrue(redirectManager.redirect(proc));

        logger.info(jdbcTemplate.queryForObject(
                "SELECT pk_proc FROM proc WHERE pk_job=?",
                String.class,
                target.getJobId()));

        assertEquals(Integer.valueOf(100), jdbcTemplate.queryForObject(
                "SELECT int_cores FROM job_resource WHERE pk_job = ?",
                Integer.class, target.getJobId()));
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

        assertEquals(group.getGroupId(), jdbcTemplate.queryForObject(
                "SELECT pk_folder FROM job WHERE pk_job=?", String.class,
                target.getJobId()));

        assertTrue(redirectManager.addRedirect(proc, group,
                false, new Source()));

        assertTrue(redirectManager.hasRedirect(proc));
        assertEquals(group.getName(), jdbcTemplate.queryForObject(
                "SELECT str_redirect FROM proc WHERE pk_proc=?",
                String.class, proc.getId()));

        redirectManager.redirect(proc);

        assertEquals(Integer.valueOf(100), jdbcTemplate.queryForObject(
                "SELECT int_cores FROM folder_resource WHERE pk_folder = ?",
                Integer.class, group.getGroupId()));
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

        Redirect redirect = new Redirect(RedirectType.JobRedirect, "foo", "bar");

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

