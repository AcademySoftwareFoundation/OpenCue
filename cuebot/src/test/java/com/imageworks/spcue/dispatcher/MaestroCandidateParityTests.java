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
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
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
import com.imageworks.spcue.GroupDetail;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.DispatcherDao;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.host.ThreadMode;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.GroupManager;
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
    GroupManager groupManager;
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
        return candidateOfJob(jobId) != null;
    }

    private Maestro.LayerCandidate candidateOfJob(String jobId) {
        for (Maestro.LayerCandidate c : candidates()) {
            if (jobId.equals(c.jobId))
                return c;
        }
        return null;
    }

    /**
     * The folder figure Maestro plans against is folder_resource.int_cores, the cores the folder's
     * procs reserve and the number the database enforces the cap against, not a count rebuilt from
     * running frames x int_cores_min. 350 is a figure that estimate could never produce for
     * 100-core layers; at the cap the layer leaves the candidate set, one core of room and it is
     * back.
     */
    @Test
    public void folderRunningIsTheFoldersReservedCores() {
        JobDetail job = getJob();
        GroupDetail folder = groupManager.getGroupDetail(job);
        jdbcTemplate.update(
                "UPDATE folder_resource SET int_max_cores = 1000, int_cores = 350 WHERE pk_folder=?",
                folder.id);
        Maestro.LayerCandidate c = candidateOfJob(job.id);
        assertTrue("the capped folder's job is a candidate under its cap", c != null);
        assertEquals(1000, c.folderMax);
        assertEquals("folder_running is folder_resource.int_cores", 350, c.folderRunning);

        jdbcTemplate.update("UPDATE folder_resource SET int_cores = 950 WHERE pk_folder=?",
                folder.id);
        assertFalse("950 reserved + a 100-core layer is over a 1000 cap",
                candidatesContainJob(job.id));
        jdbcTemplate.update("UPDATE folder_resource SET int_cores = 900 WHERE pk_folder=?",
                folder.id);
        assertTrue("900 + 100 fits the cap exactly", candidatesContainJob(job.id));
        jdbcTemplate.update("UPDATE folder_resource SET int_cores = 2000 WHERE pk_folder=?",
                folder.id);
        assertFalse("a folder already over its cap is never planned", candidatesContainJob(job.id));
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
            + "       OR COALESCE(fr.int_cores, 0) + l.int_cores_min <= fr.int_max_cores) "
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

    // The pinned read the in-memory pin resolution replaced, kept here as the oracle: one row
    // per (layer, named host) for the waiting layers whose tags are not all spec tags, the host
    // resolved and checked in SQL, and one null-host row for a layer none of whose names
    // resolves. Binds: thread mode ALL, the spec tags (csv, lower case), the facility-mode
    // flag. The lottery and the row cap are left out: they are drawn per group now, and the
    // comparison is on sets with the cap set high.
    // spotless:off
    private static final String SQL_PINNED_ROWS =
            "SELECT l.pk_layer, h.pk_host AS pin_host, l.str_tags "
            + "FROM   layer l "
            + "JOIN   job j           ON j.pk_job  = l.pk_job "
            + "JOIN   job_resource jr ON jr.pk_job = j.pk_job "
            + "JOIN   show sh         ON sh.pk_show = j.pk_show "
            + "LEFT JOIN layer_stat  ls ON ls.pk_layer = l.pk_layer "
            + "LEFT JOIN folder_resource fr ON fr.pk_folder = j.pk_folder "
            + "LEFT JOIN (host h JOIN host_stat hs ON hs.pk_host = h.pk_host "
            + "                  JOIN alloc a ON a.pk_alloc = h.pk_alloc) "
            + "       ON lower(h.str_name) = "
            + "          ANY(string_to_array(lower(replace(l.str_tags, ' ', '')), '|')) "
            + "      AND hs.str_state = 'UP' "
            + "      AND h.str_lock_state = 'OPEN' "
            + "      AND j.pk_facility = a.pk_facility "
            + "      AND (j.str_os IS NULL OR j.str_os = '' "
            + "           OR j.str_os = ANY(string_to_array(hs.str_os, ','))) "
            + "      AND (CASE WHEN l.b_threadable = true THEN 1 ELSE 0 END) "
            + "          >= (CASE WHEN h.int_thread_mode = ? THEN 1 ELSE 0 END) "
            + "      AND l.int_cores_min <= h.int_cores "
            + "LEFT JOIN subscription sub ON sub.pk_show = j.pk_show AND sub.pk_alloc = h.pk_alloc "
            + "WHERE  j.str_state = 'PENDING' "
            + "  AND  j.b_paused  = false "
            + "  AND  NOT (string_to_array(lower(replace(l.str_tags, ' ', '')), '|') "
            + "            <@ string_to_array(?, ',')) "
            + "  AND  (h.pk_host IS NULL "
            + "        OR (sub.pk_subscription IS NOT NULL AND sub.int_cores < sub.int_burst)) "
            + "  AND  jr.int_cores  < jr.int_max_cores "
            + "  AND  COALESCE(ls.int_waiting_count, 0) > 0 "
            + "  AND (COALESCE(fr.int_max_cores, -1) = -1 "
            + "       OR COALESCE(fr.int_cores, 0) + l.int_cores_min <= fr.int_max_cores) "
            + "  AND (? OR sh.b_scheduler_managed = true) ";
    // spotless:on

    private void createPinHost(String name, String alloc, String tag, String os) {
        RenderHost host = RenderHost.newBuilder().setName(name).setBootTime(1192369572)
                .setFreeMcp(CueUtil.GB).setFreeMem(53500).setFreeSwap(20760).setLoad(1)
                .setTotalMcp(CueUtil.GB4).setTotalMem(8173264).setTotalSwap(20960)
                .setNimbyEnabled(false).setNumProcs(2).setCoresPerProc(100).addTags(tag)
                .setState(HardwareState.UP).setFacility("spi").putAttributes("SP_OS", os).build();
        hostManager.createHost(host,
                adminManager.findAllocationDetail(alloc.split("\\.")[0], alloc.split("\\.")[1]));
    }

    /** The (layer, host) pairs and the dead layers of one tag assignment, from the SQL oracle. */
    private void sqlPins(Set<String> specTags, Set<String> pairs, Set<String> dead) {
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(SQL_PINNED_ROWS,
                ThreadMode.ALL_VALUE, String.join(",", specTags), MaestroMode.facility(springEnv));
        for (Map<String, Object> r : rows) {
            String layer = (String) r.get("pk_layer");
            Object host = r.get("pin_host");
            if (host != null)
                pairs.add(layer + "|" + host);
            else if (!Maestro.namesSpecTag((String) r.get("str_tags"), specTags))
                dead.add(layer);
        }
    }

    /**
     * Every shape of the pin parity table, cycled over the fixture's three waiting layers: for each
     * assignment the in-memory resolution must produce exactly the (layer, host) pairs and the "no
     * host" layers the pinned SQL produced.
     */
    @Test
    public void pinResolutionMatchesThePinnedSqlForEveryShape() {
        createPinHost("pina", "spi.general", "test", "Linux");
        createPinHost("pinb", "spi.general", "test", "Linux");
        createPinHost("PINB", "spi.general", "test", "Linux"); // str_name is unique raw, not lower
        createPinHost("pinother", "spi.general", "other", "Linux"); // a second spec
        createPinHost("pinos", "spi.general", "test", "rhel9"); // os misfit
        createPinHost("pinall", "spi.general", "test", "Linux"); // thread mode ALL below
        createPinHost("pinsmall", "spi.general", "test", "Linux"); // too small below
        createPinHost("pinlax", "lax.general", "test", "Linux"); // other facility
        createPinHost("pindesk", "spi.desktop", "test", "Linux"); // subscription at burst below
        jdbcTemplate.update("UPDATE host SET int_thread_mode=? WHERE str_name='pinall'",
                ThreadMode.ALL_VALUE);
        jdbcTemplate.update("UPDATE host SET int_cores=50 WHERE str_name='pinsmall'");
        jdbcTemplate.update("UPDATE subscription SET int_cores=int_burst WHERE pk_alloc="
                + "(SELECT pk_alloc FROM alloc WHERE str_name='spi.desktop')");
        List<String> layers = jdbcTemplate.queryForList("SELECT l.pk_layer FROM layer l "
                + "JOIN job j ON j.pk_job = l.pk_job WHERE j.str_name LIKE ? ORDER BY l.pk_layer",
                String.class, "pipe-dev.cue-testuser_shell_dispatch_test_%");
        assertEquals("the fixture's layers", 3, layers.size());
        // The non-threadable layer meets the ALL-mode host in the third round.
        jdbcTemplate.update("UPDATE layer SET b_threadable=false WHERE pk_layer=?", layers.get(0));
        List<List<String>> rounds =
                Arrays.asList(Arrays.asList("PinA | pina | pinb |", "test | pina", "nosuchhost"),
                        Arrays.asList("pinother | pina", "pindesk", "pinlax | pinos | pinsmall"),
                        Arrays.asList("pinall", "pinall", "test | nosuchhost"),
                        Arrays.asList("pinos | nosuchhost", "pindesk | pinb", "pinlax"));

        int comparedPairs = 0, comparedDead = 0;
        for (List<String> round : rounds) {
            for (int i = 0; i < layers.size(); i++)
                jdbcTemplate.update("UPDATE layer SET str_tags=? WHERE pk_layer=?", round.get(i),
                        layers.get(i));
            Map<Maestro.HostSpecKey, List<Maestro.BookableHost>> groups =
                    Maestro.groupByHostSpec(maestro.readAllHosts());
            Set<String> specTags = new HashSet<>();
            Map<String, List<Maestro.BookableHost>> hostByName = new HashMap<>();
            for (Map.Entry<Maestro.HostSpecKey, List<Maestro.BookableHost>> e : groups.entrySet()) {
                for (String t : e.getKey().tagsNormalized.split("\\s+"))
                    if (!t.isEmpty())
                        specTags.add(t.toLowerCase());
                for (Maestro.BookableHost h : e.getValue())
                    hostByName.computeIfAbsent(h.hostName.toLowerCase(), x -> new ArrayList<>())
                            .add(h);
            }
            Set<String> sqlPairs = new HashSet<>(), sqlDead = new HashSet<>();
            sqlPins(specTags, sqlPairs, sqlDead);

            Map<String, String> reason = new HashMap<>();
            Map<Maestro.HostSpecKey, List<Maestro.LayerCandidate>> pins =
                    Maestro.resolvePins(maestro.readTickCandidates(), hostByName, specTags, 100000,
                            new Random(1), reason, new HashMap<>());
            Set<String> javaPairs = new HashSet<>();
            for (Map.Entry<Maestro.HostSpecKey, List<Maestro.LayerCandidate>> e : pins.entrySet())
                for (Maestro.LayerCandidate c : e.getValue())
                    for (Maestro.BookableHost h : c.pinnedHosts) {
                        assertEquals("filed under its hosts' group", e.getKey(),
                                Maestro.hostSpecKey(h));
                        javaPairs.add(c.layerId + "|" + h.hostId);
                    }

            assertEquals("pairs for " + round, sqlPairs, javaPairs);
            assertEquals("dead layers for " + round, sqlDead, reason.keySet());
            comparedPairs += sqlPairs.size();
            comparedDead += sqlDead.size();
        }
        assertTrue("the oracle produced pins to compare", comparedPairs >= 6);
        assertTrue("and dead layers to compare", comparedDead >= 3);
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
