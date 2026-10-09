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
import java.util.HashSet;
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
import com.imageworks.spcue.grpc.host.ThreadMode;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.util.CueUtil;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.assertEquals;

/**
 * Legacy-vs-scheduler booking parity on the repo's fixture jobs: both paths must find, and refuse,
 * the same jobs.
 */
@Transactional
@ContextConfiguration(classes = TestAppConfig.class, loader = AnnotationConfigContextLoader.class)
public class MaestroCandidateParityTests extends AbstractTransactionalJUnit4SpringContextTests {

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
    Maestro maestro;
    @Resource
    ConfigurableEnvironment springEnv;

    // Same fixture/host/values as DispatcherDaoTests; only delta is maestro.enabled=facility.
    private static final String HOSTNAME = "beta";
    private static final String JOB = "pipe-dev.cue-testuser_shell_dispatch_test_v1";

    // Facility mode ONLY while these tests run, injected into the SHARED
    // context's environment: no second Spring context, no second gRPC server.
    // Maestro reads maestro.enabled per call, so this takes effect live.
    @Before
    public void facilityMode() {
        springEnv.getPropertySources().addFirst(new MapPropertySource("parityFacility",
                Collections.singletonMap("maestro.enabled", "facility")));
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

    /** Maestro candidate list for the group containing HOSTNAME (empty if none). */
    private List<Maestro.LayerCandidate> candidates() {
        Map<Maestro.HostSpecKey, List<Maestro.BookableHost>> groups =
                Maestro.groupByHostSpec(maestro.readAllHosts());
        for (Map.Entry<Maestro.HostSpecKey, List<Maestro.BookableHost>> e : groups.entrySet()) {
            int maxCores = 0;
            boolean mine = false;
            for (Maestro.BookableHost h : e.getValue()) {
                if (h.coresTotal > maxCores)
                    maxCores = h.coresTotal;
                if (HOSTNAME.equals(h.hostName))
                    mine = true;
            }
            if (mine)
                return maestro.readLayerCandidatesForGroup(e.getKey(), maxCores);
        }
        return Collections.emptyList();
    }

    private boolean candidatesContainJob(String jobId) {
        for (Maestro.LayerCandidate c : candidates()) {
            if (jobId.equals(c.jobId))
                return true;
        }
        return false;
    }

    // The per-group candidate query the in-memory group cut replaced, kept here as the
    // oracle: for every host-spec group of the fixture farm, the layers the SQL admits must
    // be exactly the layers readLayerCandidatesForGroup admits.
    // spotless:off
    private static final String SQL_CANDIDATES_FOR_GROUP =
            "SELECT l.pk_layer "
            + "FROM   layer l "
            + "JOIN   job j           ON j.pk_job  = l.pk_job "
            + "JOIN   job_resource jr ON jr.pk_job = j.pk_job "
            + "JOIN   show sh         ON sh.pk_show = j.pk_show "
            + "JOIN   subscription sub ON sub.pk_show = j.pk_show AND sub.pk_alloc = ? "
            + "LEFT JOIN layer_stat  ls ON ls.pk_layer = l.pk_layer "
            + "LEFT JOIN folder_resource fr ON fr.pk_folder = j.pk_folder "
            + "LEFT JOIN ("
            + "    SELECT j2.pk_folder, "
            + "           SUM(ls2.int_running_count * l2.int_cores_min) AS folder_cores "
            + "    FROM   job j2 "
            + "    JOIN   folder_resource fr2 ON fr2.pk_folder = j2.pk_folder "
            + "                               AND fr2.int_max_cores <> -1 "
            + "    JOIN   layer l2      ON l2.pk_job = j2.pk_job "
            + "    JOIN   layer_stat ls2 ON ls2.pk_layer = l2.pk_layer "
            + "    WHERE  j2.str_state = 'PENDING' "
            + "    GROUP BY j2.pk_folder) fu ON fu.pk_folder = j.pk_folder "
            + "WHERE  j.str_state = 'PENDING' "
            + "  AND  j.b_paused  = false "
            + "  AND  (j.str_os IS NULL OR j.str_os = '' "
            + "        OR j.str_os = ANY(string_to_array(?, ','))) "
            + "  AND  j.pk_facility = ? "
            + "  AND  (CASE WHEN l.b_threadable = true THEN 1 ELSE 0 END) >= ? "
            + "  AND  ? ~* ('(?x)' || l.str_tags || '\\y') "
            + "  AND  jr.int_cores  < jr.int_max_cores "
            + "  AND  sub.int_cores < sub.int_burst "
            + "  AND  l.int_cores_min <= ? "
            + "  AND  COALESCE(ls.int_waiting_count, 0) > 0 "
            + "  AND (COALESCE(fr.int_max_cores, -1) = -1 "
            + "       OR COALESCE(fu.folder_cores, 0) + l.int_cores_min <= fr.int_max_cores) "
            + "  AND (? OR sh.b_scheduler_managed = true) ";
    // spotless:on

    private Set<String> sqlCandidateLayers(Maestro.HostSpecKey spec, int maxCores) {
        return new HashSet<>(jdbcTemplate.queryForList(SQL_CANDIDATES_FOR_GROUP, String.class,
                spec.pkAlloc, spec.os, spec.pkFacility, spec.allThreadMode ? 1 : 0,
                spec.tagsNormalized, maxCores, MaestroMode.facility(springEnv)));
    }

    /** Every group's in-memory cut admits exactly the layers the per-group SQL admitted. */
    @Test
    public void groupCutMatchesTheSqlForEveryGroup() {
        // A second host on another os and thread mode widens the farm to several groups,
        // so the os, thread-mode and tag predicates are all exercised.
        RenderHost other = RenderHost.newBuilder().setName("gamma").setBootTime(1192369572)
                .setFreeMcp(CueUtil.GB).setFreeMem(53500).setFreeSwap(20760).setLoad(1)
                .setTotalMcp(CueUtil.GB4).setTotalMem(8173264).setTotalSwap(20960)
                .setNimbyEnabled(false).setNumProcs(2).setCoresPerProc(100).addTags("other")
                .setState(HardwareState.UP).setFacility("spi").putAttributes("SP_OS", "rhel7,rhel9")
                .build();
        hostManager.createHost(other, adminManager.findAllocationDetail("spi", "general"));

        Map<Maestro.HostSpecKey, List<Maestro.BookableHost>> groups =
                Maestro.groupByHostSpec(maestro.readAllHosts());
        assertTrue("the fixture farm has several groups", groups.size() >= 2);
        int compared = 0;
        for (Map.Entry<Maestro.HostSpecKey, List<Maestro.BookableHost>> e : groups.entrySet()) {
            int maxCores = 0;
            for (Maestro.BookableHost h : e.getValue())
                maxCores = Math.max(maxCores, h.coresTotal);
            Set<String> fromSql = sqlCandidateLayers(e.getKey(), maxCores);
            Set<String> fromCut = new HashSet<>();
            for (Maestro.LayerCandidate c : maestro.readLayerCandidatesForGroup(e.getKey(),
                    maxCores))
                fromCut.add(c.layerId);
            assertEquals("group " + e.getKey(), fromSql, fromCut);
            if (!fromSql.isEmpty())
                compared++;
        }
        assertTrue("at least one group admitted the fixture job", compared >= 1);
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

    /** Non-threadable layer on a ThreadMode.ALL host: legacy refuses, scheduler must too. */
    @Test
    public void nonThreadableLayerOnAllModeHostIsRefusedByBothPaths() {
        DispatchHost host = getHost();
        JobDetail job = getJob();

        // NIMBY workstations register as ThreadMode.ALL (HostDaoJdbc), common in test farms.
        jdbcTemplate.update("UPDATE host SET int_thread_mode=? WHERE pk_host=?",
                ThreadMode.ALL_VALUE, host.id);
        jdbcTemplate.update("UPDATE layer SET b_threadable=false WHERE pk_job=?", job.id);

        DispatchHost fresh = getHost();
        Set<String> legacy = dispatcherDao.findDispatchJobs(fresh, 10);
        assertFalse("legacy refuses non-threadable work on an ALL host", legacy.contains(job.id));
        assertFalse("scheduler must refuse non-threadable work on an ALL host",
                candidatesContainJob(job.id));
    }

    /** Threadable layer on a ThreadMode.ALL host must still book in both paths. */
    @Test
    public void threadableLayerOnAllModeHostBooksInBothPaths() {
        DispatchHost host = getHost();
        JobDetail job = getJob();

        jdbcTemplate.update("UPDATE host SET int_thread_mode=? WHERE pk_host=?",
                ThreadMode.ALL_VALUE, host.id);
        jdbcTemplate.update("UPDATE layer SET b_threadable=true WHERE pk_job=?", job.id);

        DispatchHost fresh = getHost();
        Set<String> legacy = dispatcherDao.findDispatchJobs(fresh, 10);
        assertTrue("legacy books threadable work on an ALL host", legacy.contains(job.id));
        assertTrue("scheduler must book threadable work on an ALL host",
                candidatesContainJob(job.id));
    }

    /** A job from another facility must be refused by both paths. */
    @Test
    public void crossFacilityJobIsRefusedByBothPaths() {
        DispatchHost host = getHost();
        JobDetail job = getJob();

        jdbcTemplate.update("INSERT INTO facility (pk_facility, str_name) VALUES "
                + "('AAAAAAAA-0000-0000-0000-000000000001', 'parity_lax')");
        jdbcTemplate.update("UPDATE job SET pk_facility="
                + "'AAAAAAAA-0000-0000-0000-000000000001' WHERE pk_job=?", job.id);

        Set<String> legacy = dispatcherDao.findDispatchJobs(host, 10);
        assertFalse("legacy refuses a job from another facility", legacy.contains(job.id));
        assertFalse("scheduler must refuse a job from another facility",
                candidatesContainJob(job.id));
    }
}
