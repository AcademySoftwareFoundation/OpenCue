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

package com.imageworks.spcue.dispatcher;

import java.io.File;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Set;
import javax.annotation.Resource;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.springframework.core.env.ConfigurableEnvironment;
import org.springframework.core.env.MapPropertySource;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.DispatcherDao;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.util.CueUtil;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/**
 * Legacy-vs-scheduler booking parity on the repo's fixture jobs: both paths must find, and refuse,
 * the same jobs.
 */
@Transactional
@ContextConfiguration(classes = TestAppConfig.class, loader = AnnotationConfigContextLoader.class)
public class SchedulerCandidateParityTests extends AbstractTransactionalJUnit4SpringContextTests {

    @Resource
    JobLauncher jobLauncher;
    @Resource
    JobManager jobManager;
    @Resource
    HostManager hostManager;
    @Resource
    AdminManager adminManager;
    @Resource
    DispatcherDao dispatcherDao;
    @Resource
    HostDao hostDao;
    @Resource
    Scheduler scheduler;
    @Resource
    ConfigurableEnvironment springEnv;

    // Same fixture/host/values as DispatcherDaoTests; only delta is scheduler.enabled=facility.
    private static final String HOSTNAME = "beta";
    private static final String JOB = "pipe-dev.cue-testuser_shell_dispatch_test_v1";

    // Facility mode ONLY while these tests run, injected into the SHARED
    // context's environment: no second Spring context, no second gRPC server.
    // Scheduler reads scheduler.enabled per call, so this takes effect live.
    @Before
    public void facilityMode() {
        springEnv.getPropertySources().addFirst(new MapPropertySource("parityFacility",
                Collections.singletonMap("scheduler.enabled", "facility")));
    }

    @After
    public void restoreMode() {
        springEnv.getPropertySources().remove("parityFacility");
    }

    @Before
    public void launchJob() {
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_dispatch_test.xml"));
    }

    @Before
    public void createHost() {
        RenderHost host = RenderHost.newBuilder().setName(HOSTNAME).setBootTime(1192369572)
                // The minimum amount of free space in the temporary directory to book a host.
                .setFreeMcp(CueUtil.GB).setFreeMem(53500).setFreeSwap(20760).setLoad(1)
                .setTotalMcp(CueUtil.GB4).setTotalMem(8173264).setTotalSwap(20960)
                .setNimbyEnabled(false).setNumProcs(2).setCoresPerProc(100).addTags("test")
                .setState(HardwareState.UP).setFacility("spi").putAttributes("SP_OS", "Linux")
                .build();
        hostManager.createHost(host, adminManager.findAllocationDetail("spi", "general"));
    }

    private DispatchHost getHost() {
        return hostDao.findDispatchHost(HOSTNAME);
    }

    private JobDetail getJob() {
        return jobManager.findJobDetail(JOB);
    }

    /** The Scheduler candidate list for the group containing HOSTNAME (empty if none). */
    private List<Scheduler.LayerCandidate> candidates() {
        Map<Scheduler.HostSpecKey, List<Scheduler.BookableHost>> groups =
                Scheduler.groupByHostSpec(scheduler.readAllHosts());
        for (Map.Entry<Scheduler.HostSpecKey, List<Scheduler.BookableHost>> e : groups.entrySet()) {
            int maxCores = 0;
            boolean mine = false;
            for (Scheduler.BookableHost h : e.getValue()) {
                if (h.coresTotal > maxCores)
                    maxCores = h.coresTotal;
                if (HOSTNAME.equals(h.hostName))
                    mine = true;
            }
            if (mine)
                return scheduler.readLayerCandidatesForGroup(e.getKey(), maxCores);
        }
        return Collections.emptyList();
    }

    private boolean candidatesContainJob(String jobId) {
        for (Scheduler.LayerCandidate c : candidates()) {
            if (jobId.equals(c.jobId))
                return true;
        }
        return false;
    }

    @Test
    public void fixtureJobIsFoundByBothPaths() {
        DispatchHost host = getHost();
        JobDetail job = getJob();

        Set<String> legacy = dispatcherDao.findDispatchJobs(host, 10);
        assertTrue("legacy dispatcher must find the fixture job", legacy.contains(job.id));
        assertTrue("scheduler candidate query must find the fixture job",
                candidatesContainJob(job.id));
    }

    /** Multi-OS host ("rhel7,rhel9") must book an os-pinned job in both paths. */
    @Test
    public void multiOsHostMatchesOsPinnedJobInBothPaths() {
        DispatchHost host = getHost();
        JobDetail job = getJob();

        jdbcTemplate.update("UPDATE host_stat SET str_os='rhel7,rhel9' WHERE pk_host=?", host.id);
        jdbcTemplate.update("UPDATE job SET str_os='rhel9' WHERE pk_job=?", job.id);

        DispatchHost fresh = getHost();
        Set<String> legacy = dispatcherDao.findDispatchJobs(fresh, 10);
        assertTrue("legacy books an os-pinned job on a multi-OS host", legacy.contains(job.id));
        assertTrue("scheduler must book an os-pinned job on a multi-OS host",
                candidatesContainJob(job.id));
    }

    /** A job from another facility must be refused by both paths. */
    @Test
    public void crossFacilityJobIsRefusedByBothPaths() {
        DispatchHost host = getHost();
        JobDetail job = getJob();

        jdbcTemplate.update(
                "INSERT INTO facility (pk_facility, str_name) VALUES "
                        + "('AAAAAAAA-0000-0000-0000-000000000001', 'parity_lax')");
        jdbcTemplate.update("UPDATE job SET pk_facility="
                + "'AAAAAAAA-0000-0000-0000-000000000001' WHERE pk_job=?", job.id);

        Set<String> legacy = dispatcherDao.findDispatchJobs(host, 10);
        assertFalse("legacy refuses a job from another facility", legacy.contains(job.id));
        assertFalse("scheduler must refuse a job from another facility",
                candidatesContainJob(job.id));
    }
}
