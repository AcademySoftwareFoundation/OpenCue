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
import java.lang.reflect.Field;
import java.sql.Connection;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import javax.annotation.Resource;
import javax.sql.DataSource;

import org.junit.Rule;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.GroupDetail;
import com.imageworks.spcue.Inherit;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.GroupManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.test.AssumingPostgresEngine;
import com.imageworks.spcue.util.CueUtil;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * The commit against a site trigger that rejects a frame start once its folder is over its core cap
 * (the 2021 folder-cap function, installed here on the WAITING to RUNNING transition). One folder
 * over its cap must cost the tick only that folder's bookings: every other host's bookings land in
 * the same tick, with their procs and resource mirrors, and the rejected frames stay WAITING.
 *
 * Runs outside the test-managed transaction: a rejected statement aborts the Postgres transaction
 * it ran in, so each retry piece must have a transaction of its own, which only real commits give.
 * The fixtures are created and removed for real, and the resource mirrors the commit moves
 * (subscription, folder, point) are put back, since nothing here releases the procs through the
 * paths that would subtract them.
 */
@ContextConfiguration(classes = TestAppConfig.class, loader = AnnotationConfigContextLoader.class)
public class MaestroFolderCapCommitTests extends AbstractJUnit4SpringContextTests {

    private static final String[] HOSTS =
            {"maestro_fcap_host_a", "maestro_fcap_host_b", "maestro_fcap_host_c"};
    private static final String TRIGGER = "maestro_fcap_test_folder_cap";
    private static final long FRAME_MEM_KB = 2L * CueUtil.GB;

    @Autowired
    @Rule
    public AssumingPostgresEngine assumingPostgresEngine;

    @Resource
    Maestro maestro;
    @Resource
    FrameDao frameDao;
    @Resource
    JobDao jobDao;
    @Resource
    HostDao hostDao;
    @Resource
    HostManager hostManager;
    @Resource
    JobManager jobManager;
    @Resource
    JobLauncher jobLauncher;
    @Resource
    GroupManager groupManager;
    @Resource
    AdminManager adminManager;
    @Resource
    DataSource dataSource;

    @Test
    public void anOverCapFolderCostsTheTickOnlyItsOwnBookings() throws Exception {
        Fixture fx = new Fixture();
        try {
            fx.create();
            // Host a: three frames of the healthy job; host b: three frames of
            // the over-cap folder's job; host c: three more of the healthy job.
            // One chunk, three hosts, the poison in the middle.
            List<FrameBooking> plan = new ArrayList<>();
            plan.addAll(fx.bookings(fx.healthy, "pass_1", fx.hosts[0]));
            plan.addAll(fx.bookings(fx.capped, "pass_1", fx.hosts[1]));
            plan.addAll(fx.bookings(fx.healthy, "pass_2", fx.hosts[2]));
            long healthyFolderBefore = fx.folderCores(fx.healthyFolder);
            long cappedFolderBefore = fx.folderCores(fx.cappedFolder);

            List<FrameBooking> won = maestro.commitInChunks(plan);

            assertEquals("both healthy hosts landed in the same tick", 6, won.size());
            for (FrameBooking b : won)
                assertEquals(fx.healthy.id, b.frame.getJobId());
            assertEquals("the poison host's bookings, and only those, were dropped", 3,
                    maestro.lastCommitDropped);
            assertTrue("the chunk was split rather than dropped whole",
                    maestro.lastCommitSplits >= 1);

            JdbcTemplate jdbc = fx.jdbc;
            assertEquals(Integer.valueOf(6), jdbc.queryForObject(
                    "SELECT count(*) FROM proc WHERE pk_job = ?", Integer.class, fx.healthy.id));
            assertEquals(Integer.valueOf(0), jdbc.queryForObject(
                    "SELECT count(*) FROM proc WHERE pk_job = ?", Integer.class, fx.capped.id));
            assertEquals(Integer.valueOf(6),
                    jdbc.queryForObject(
                            "SELECT count(*) FROM frame WHERE pk_job = ? AND str_state = 'RUNNING'",
                            Integer.class, fx.healthy.id));
            assertEquals("the rejected frames wait for the next tick", Integer.valueOf(0),
                    jdbc.queryForObject(
                            "SELECT count(*) FROM frame WHERE pk_job = ? AND str_state <> 'WAITING'",
                            Integer.class, fx.capped.id));
            // The mirrors moved by exactly the procs that exist.
            assertEquals(600, fx.folderCores(fx.healthyFolder) - healthyFolderBefore);
            assertEquals(600,
                    (long) jdbc.queryForObject(
                            "SELECT int_cores FROM job_resource WHERE pk_job = ?", Long.class,
                            fx.healthy.id));
            assertEquals(cappedFolderBefore, fx.folderCores(fx.cappedFolder));
            assertEquals(0,
                    (long) jdbc.queryForObject(
                            "SELECT int_cores FROM job_resource WHERE pk_job = ?", Long.class,
                            fx.capped.id));
        } finally {
            fx.destroy();
        }
    }

    private static Field field(String name) throws Exception {
        Field f = Maestro.class.getDeclaredField(name);
        f.setAccessible(true);
        return f;
    }

    /**
     * Three committed hosts, the two fixture jobs with the second moved into a folder that is
     * already over its cap, the folder-cap trigger on frame, and a Maestro bean that believes it
     * holds the planning lock and launches nothing. Every step records what it made, so destroy()
     * undoes exactly what create() got through, in reverse, whatever point it failed at.
     */
    private final class Fixture {
        final JdbcTemplate jdbc = new JdbcTemplate(dataSource);
        final DispatchHost[] hosts = new DispatchHost[HOSTS.length];
        JobDetail healthy;
        JobDetail capped;
        String healthyFolder;
        String cappedFolder;
        GroupDetail group;
        boolean jobsLaunched;
        boolean triggerInstalled;
        // Rows the commit's delta flush moves and nothing here moves back: restored by key.
        final Map<String, Long> subscriptionCores = new LinkedHashMap<>();
        final Map<String, Long> pointCores = new LinkedHashMap<>();
        Long healthyFolderCores;
        Object savedLeaderConn;
        Object savedLaunchPool;
        boolean beanPatched;

        void create() throws Exception {
            for (int i = 0; i < HOSTS.length; i++)
                hosts[i] = createHost(HOSTS[i]);
            jobLauncher.testMode = true;
            jobLauncher
                    .launch(new File("src/test/resources/conf/jobspec/jobspec_dispatch_test.xml"));
            jobsLaunched = true;
            healthy = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_dispatch_test_v1");
            capped = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_dispatch_test_v2");
            healthyFolder = groupManager.getGroupDetail(healthy).id;
            snapshotMirrors();

            GroupDetail g = new GroupDetail();
            g.name = "maestro_fcap_over_cap";
            g.showId = healthy.getShowId();
            groupManager.createGroup(g, groupManager
                    .getRootGroupDetail(adminManager.getShowEntity(healthy.getShowId())));
            group = g;
            groupManager.reparentJob(capped, group, new Inherit[0]);
            cappedFolder = group.id;
            // Over its cap already, as after an admin lowered it under running work.
            jdbc.update("UPDATE folder_resource SET int_max_cores = 200, int_cores = 300 "
                    + "WHERE pk_folder = ?", cappedFolder);
            installTrigger();

            savedLeaderConn = field("leaderConn").get(maestro);
            savedLaunchPool = field("launchPool").get(maestro);
            Connection held = mock(Connection.class);
            when(held.isValid(anyInt())).thenReturn(true);
            // A shut-down pool with a discard policy: the committed bookings are
            // never launched against the fixture hosts.
            ThreadPoolExecutor noLaunch = new ThreadPoolExecutor(1, 1, 0L, TimeUnit.MILLISECONDS,
                    new LinkedBlockingQueue<>(), new ThreadPoolExecutor.DiscardPolicy());
            noLaunch.shutdown();
            field("leaderConn").set(maestro, held);
            field("launchPool").set(maestro, noLaunch);
            beanPatched = true;
        }

        private void snapshotMirrors() {
            String show = healthy.getShowId();
            jdbc.query("SELECT pk_subscription, int_cores FROM subscription WHERE pk_show = ?",
                    rs -> {
                        subscriptionCores.put(rs.getString(1), rs.getLong(2));
                    }, show);
            jdbc.query("SELECT pk_point, int_cores FROM point WHERE pk_show = ?", rs -> {
                pointCores.put(rs.getString(1), rs.getLong(2));
            }, show);
            healthyFolderCores = folderCores(healthyFolder);
        }

        private void restoreMirrors() {
            for (Map.Entry<String, Long> e : subscriptionCores.entrySet())
                jdbc.update("UPDATE subscription SET int_cores = ? WHERE pk_subscription = ?",
                        e.getValue(), e.getKey());
            for (Map.Entry<String, Long> e : pointCores.entrySet())
                jdbc.update("UPDATE point SET int_cores = ? WHERE pk_point = ?", e.getValue(),
                        e.getKey());
            if (healthyFolderCores != null)
                jdbc.update("UPDATE folder_resource SET int_cores = ? WHERE pk_folder = ?",
                        healthyFolderCores, healthyFolder);
        }

        /**
         * The 2021 folder-cap function, fired on the WAITING to RUNNING transition, with the one
         * fix a site must have made to run it at all: an uncapped folder (int_max_cores = -1) is
         * not over its cap.
         */
        private void installTrigger() {
            jdbc.execute("CREATE OR REPLACE FUNCTION trigger__update_frame_int_cores() "
                    + "RETURNS TRIGGER AS $body$ "
                    + "DECLARE v_int_cores INT; v_int_max_cores INT; v_pk_folder VARCHAR; "
                    + "BEGIN "
                    + "  SELECT pk_folder INTO v_pk_folder FROM job WHERE pk_job = OLD.pk_job; "
                    + "  SELECT int_cores, int_max_cores INTO v_int_cores, v_int_max_cores "
                    + "    FROM folder_resource WHERE pk_folder = v_pk_folder; "
                    + "  IF v_int_max_cores >= 0 AND v_int_cores > v_int_max_cores THEN "
                    + "    RAISE EXCEPTION 'Job exceeded max folder resources'; " + "  END IF; "
                    + "  RETURN NEW; " + "END; $body$ LANGUAGE PLPGSQL");
            jdbc.execute("DROP TRIGGER IF EXISTS " + TRIGGER + " ON frame");
            jdbc.execute("CREATE TRIGGER " + TRIGGER + " BEFORE UPDATE ON frame FOR EACH ROW "
                    + "WHEN (OLD.str_state = 'WAITING' AND NEW.str_state = 'RUNNING') "
                    + "EXECUTE PROCEDURE trigger__update_frame_int_cores()");
            triggerInstalled = true;
        }

        private DispatchHost createHost(String name) {
            hostManager.createHost(
                    RenderHost.newBuilder().setName(name).setBootTime(1192369572)
                            .setFreeMcp(CueUtil.GB).setFreeMem(8173264).setFreeSwap(20760)
                            .setLoad(1).setTotalMcp(CueUtil.GB4).setTotalMem(8173264)
                            .setTotalSwap(20960).setNimbyEnabled(false).setNumProcs(8)
                            .setCoresPerProc(100).addTags("general").setState(HardwareState.UP)
                            .setFacility("spi").putAttributes("SP_OS", "Linux").build(),
                    adminManager.findAllocationDetail("spi", "general"));
            return hostDao.findDispatchHost(name);
        }

        /** Frames 1-3 of the layer, one core and 2G each, all on one host. */
        List<FrameBooking> bookings(JobDetail job, String layer, DispatchHost host) {
            List<FrameBooking> out = new ArrayList<>();
            for (int i = 1; i <= 3; i++) {
                FrameDetail detail =
                        frameDao.findFrameDetail(job, String.format("%04d-%s", i, layer));
                DispatchFrame frame = jobManager.getDispatchFrame(detail.id);
                VirtualProc proc = new VirtualProc();
                proc.allocationId = host.allocationId;
                proc.hostId = host.id;
                proc.hostName = host.name;
                proc.coresReserved = 100;
                proc.memoryReserved = FRAME_MEM_KB;
                proc.jobId = job.id;
                proc.frameId = frame.id;
                proc.layerId = frame.layerId;
                proc.showId = frame.showId;
                out.add(new FrameBooking(frame, proc));
            }
            return out;
        }

        long folderCores(String folderId) {
            return jdbc.queryForObject("SELECT int_cores FROM folder_resource WHERE pk_folder = ?",
                    Long.class, folderId);
        }

        /** Undo in reverse order; every step is independent so one failure skips nothing. */
        void destroy() {
            if (beanPatched) {
                try {
                    field("leaderConn").set(maestro, savedLeaderConn);
                    field("launchPool").set(maestro, savedLaunchPool);
                } catch (Exception ignore) {
                    // best effort
                }
            }
            if (triggerInstalled) {
                jdbc.execute("DROP TRIGGER IF EXISTS " + TRIGGER + " ON frame");
                jdbc.execute("DROP FUNCTION IF EXISTS trigger__update_frame_int_cores()");
            }
            for (DispatchHost h : hosts)
                if (h != null)
                    jdbc.update("DELETE FROM proc WHERE pk_host = ?", h.id);
            if (jobsLaunched) {
                jobDao.deleteJob(healthy);
                jobDao.deleteJob(capped);
                restoreMirrors();
            }
            if (group != null)
                jdbc.update("DELETE FROM folder WHERE pk_folder = ?", group.id);
            for (DispatchHost h : hosts)
                if (h != null)
                    hostDao.deleteHost(h);
        }
    }
}
