
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

package com.imageworks.spcue.test.dao.postgres;

import java.io.File;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.util.Arrays;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import javax.annotation.Resource;
import javax.sql.DataSource;

import com.google.common.collect.ImmutableList;
import org.junit.Rule;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dispatcher.FrameBooking;
import com.imageworks.spcue.dispatcher.QueuedFrameCompletion;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.report.FrameCompleteReport;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.grpc.report.RunningFrameInfo;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.test.AssumingPostgresEngine;
import com.imageworks.spcue.util.CueUtil;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/**
 * The frame batches against a concurrent single-frame writer, on two real connections.
 *
 * A single-frame stop (or eat, retry, orphan reset) holds its frame row and then reaches for the
 * layer_stat and job_stat rows through the status-count trigger. A batch that pre-locked those stat
 * rows and then waited on that frame row closed a deadlock cycle, which cost the Maestro drain
 * whole chunks against the orphan sweep. The batches now lock their matching frame rows before any
 * stat row, so against a writer holding a frame they wait without any stat row, and the frame that
 * writer moved on is a clean loser.
 *
 * These tests run outside the test-managed transaction: the second connection must see committed
 * rows, so the fixtures are created and deleted for real.
 */
@ContextConfiguration(classes = TestAppConfig.class, loader = AnnotationConfigContextLoader.class)
public class FrameDaoBatchLockOrderTests extends AbstractJUnit4SpringContextTests {

    private static final String HOST = "batch_lock_order_host";

    @Autowired
    @Rule
    public AssumingPostgresEngine assumingPostgresEngine;

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
    DataSource dataSource;

    @Resource
    PlatformTransactionManager transactionManager;

    @Test
    public void theStopBatchWaitsOnTheFrameBeforeTakingStatRows() throws Exception {
        Fixture fx = new Fixture();
        try {
            // Both frames RUNNING via the single-frame start path.
            frameDao.updateFrameStarted(fx.proc1, fx.frame1);
            frameDao.updateFrameStarted(fx.proc2, fx.frame2);
            DispatchFrame running1 = frameDao.getDispatchFrame(fx.frame1.getFrameId());
            DispatchFrame running2 = frameDao.getDispatchFrame(fx.frame2.getFrameId());

            boolean[] won = raceAgainstSingleFrameWriter(fx, running1,
                    () -> frameDao.batchUpdateFramesStopped(Arrays.asList(
                            completion(running1, fx.proc1), completion(running2, fx.proc2))),
                    "UPDATE frame SET str_state = 'WAITING', int_version = int_version + 1, "
                            + "ts_updated = current_timestamp WHERE pk_frame = ?");

            // The frame the writer moved on is a loser, untouched by the batch; its sibling won.
            assertFalse(won[0]);
            assertTrue(won[1]);
            assertEquals("WAITING", state(fx.frame1));
            assertEquals(running1.version + 1, version(fx.frame1));
            assertEquals("SUCCEEDED", state(fx.frame2));
        } finally {
            fx.destroy();
        }
    }

    @Test
    public void theStartBatchWaitsOnTheFrameBeforeTakingStatRows() throws Exception {
        Fixture fx = new Fixture();
        try {
            boolean[] won = raceAgainstSingleFrameWriter(fx, fx.frame1,
                    () -> frameDao.batchUpdateFramesStarted(
                            Arrays.asList(new FrameBooking(fx.frame1, fx.proc1),
                                    new FrameBooking(fx.frame2, fx.proc2))),
                    "UPDATE frame SET str_state = 'EATEN', int_version = int_version + 1, "
                            + "ts_updated = current_timestamp WHERE pk_frame = ?");

            assertFalse(won[0]);
            assertTrue(won[1]);
            assertEquals("EATEN", state(fx.frame1));
            assertEquals(fx.frame1.version + 1, version(fx.frame1));
            assertEquals("RUNNING", state(fx.frame2));
        } finally {
            fx.destroy();
        }
    }

    /**
     * Runs the batch on its own thread and transaction while a second connection holds the first
     * frame's row, then has that connection do what the single-frame trigger path does: take the
     * layer_stat row, move the frame on, commit. With the stat rows taken before the frame rows the
     * batch would already hold layer_stat here and Postgres would abort one side with a deadlock;
     * with frames first the batch is parked on the frame row holding nothing else, the writer
     * commits, and the batch finishes with that frame as a loser.
     */
    private boolean[] raceAgainstSingleFrameWriter(Fixture fx, DispatchFrame held,
            Callable<boolean[]> batch, String moveFrameOn) throws Exception {
        Thread[] worker = new Thread[1];
        ExecutorService pool = Executors.newSingleThreadExecutor(r -> {
            worker[0] = new Thread(r, "batch-under-test");
            return worker[0];
        });
        try (Connection writer = dataSource.getConnection()) {
            writer.setAutoCommit(false);
            execute(writer, "SELECT pk_frame FROM frame WHERE pk_frame = ? FOR UPDATE",
                    held.getFrameId());

            TransactionTemplate tx = new TransactionTemplate(transactionManager);
            Future<boolean[]> result = pool.submit(() -> tx.execute(s -> {
                try {
                    return batch.call();
                } catch (Exception e) {
                    throw new RuntimeException(e);
                }
            }));
            // The batch reaches the held frame row and parks there: its backend shows up
            // in a lock wait on the frame-lock statement.
            awaitParkedOnFrameRow(result, worker);
            assertFalse("the batch waits on the held frame", result.isDone());

            try {
                execute(writer, "UPDATE layer_stat SET int_running_count = int_running_count "
                        + "WHERE pk_layer = ?", held.getLayerId());
                execute(writer, moveFrameOn, held.getFrameId());
                writer.commit();
            } finally {
                // Whatever happened above, let the batch out of its wait and let it finish
                // before the fixture is torn down underneath it.
                if (!writer.isClosed() && !writer.getAutoCommit()) {
                    writer.rollback();
                }
                try {
                    result.get(30, TimeUnit.SECONDS);
                } catch (Exception ignored) {
                    // Reported by the caller's own get(), or irrelevant to a failed assertion.
                }
            }
            return result.get(30, TimeUnit.SECONDS);
        } finally {
            pool.shutdownNow();
        }
    }

    /**
     * Waits until another backend is in a lock wait on the batch's frame-lock statement, so the
     * writer's next steps run against a batch that has really reached the frame row rather than one
     * that has not started yet (which would pass this test for the wrong reason). Polls on its own
     * autocommit connection: inside a transaction pg_stat_activity is a snapshot frozen at first
     * use, so the writer's connection would never see the batch arrive.
     */
    private void awaitParkedOnFrameRow(Future<boolean[]> batch, Thread[] worker) throws Exception {
        long deadline = System.currentTimeMillis() + 15_000;
        try (Connection monitor = dataSource.getConnection();
                PreparedStatement ps = monitor.prepareStatement(
                        "SELECT count(*) FROM pg_stat_activity WHERE wait_event_type = 'Lock' "
                                + "AND query LIKE 'SELECT frame.pk_frame FROM frame JOIN unnest%'")) {
            while (System.currentTimeMillis() < deadline) {
                if (batch.isDone()) {
                    // Finished without parking: surface its result or exception.
                    batch.get();
                    throw new AssertionError("the batch finished without waiting on the frame row");
                }
                try (java.sql.ResultSet rs = ps.executeQuery()) {
                    if (rs.next() && rs.getInt(1) > 0) {
                        return;
                    }
                }
                Thread.sleep(50);
            }
        }
        StringBuilder stack = new StringBuilder();
        if (worker[0] != null) {
            for (StackTraceElement e : worker[0].getStackTrace()) {
                stack.append("\n    at ").append(e);
            }
        }
        throw new AssertionError(
                "the batch never parked on the held frame row; batch thread:" + stack);
    }

    private static void execute(Connection c, String sql, String arg) throws Exception {
        try (PreparedStatement ps = c.prepareStatement(sql)) {
            ps.setString(1, arg);
            ps.execute();
        }
    }

    private QueuedFrameCompletion completion(DispatchFrame frame, VirtualProc proc) {
        FrameCompleteReport report = FrameCompleteReport.newBuilder()
                .setFrame(RunningFrameInfo.newBuilder().setMaxRss(1).build()).setExitStatus(0)
                .build();
        return new QueuedFrameCompletion(report, proc, null, null, null, frame,
                FrameState.SUCCEEDED, 0);
    }

    private String state(DispatchFrame frame) {
        return new JdbcTemplate(dataSource).queryForObject(
                "SELECT str_state FROM frame WHERE pk_frame = ?", String.class, frame.getFrameId());
    }

    private int version(DispatchFrame frame) {
        return new JdbcTemplate(dataSource).queryForObject(
                "SELECT int_version FROM frame WHERE pk_frame = ?", Integer.class,
                frame.getFrameId());
    }

    /** A committed host and job with two frames of one layer, removed in destroy(). */
    private final class Fixture {
        final DispatchHost host;
        final JobDetail job;
        /** The spec's second job, launched with the first and removed with it. */
        final JobDetail sibling;
        final DispatchFrame frame1;
        final DispatchFrame frame2;
        final VirtualProc proc1;
        final VirtualProc proc2;

        Fixture() {
            host = createHost();
            try {
                jobLauncher.testMode = true;
                jobLauncher.launch(
                        new File("src/test/resources/conf/jobspec/jobspec_dispatch_test.xml"));
            } catch (RuntimeException e) {
                // A host left behind would fail every later fixture in this JVM.
                hostDao.deleteHost(host);
                throw e;
            }
            job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_dispatch_test_v1");
            sibling = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_dispatch_test_v2");
            FrameDetail detail1 = frameDao.findFrameDetail(job, "0001-pass_1");
            FrameDetail detail2 = frameDao.findFrameDetail(job, "0002-pass_1");
            frame1 = frameDao.getDispatchFrame(detail1.getId());
            frame2 = frameDao.getDispatchFrame(detail2.getId());
            proc1 = proc(detail1);
            proc2 = proc(detail2);
        }

        private DispatchHost createHost() {
            hostManager.createHost(RenderHost.newBuilder().setName(HOST).setBootTime(1192369572)
                    .setFreeMcp(CueUtil.GB).setFreeMem(53500).setFreeSwap(20760).setLoad(1)
                    .setTotalMcp(CueUtil.GB4).setTotalMem(8173264).setTotalSwap(20960)
                    .setNimbyEnabled(false).setNumProcs(1).setCoresPerProc(100)
                    .addAllTags(ImmutableList.of("mcore", "4core", "8g")).setState(HardwareState.UP)
                    .setFacility("spi").setFreeGpuMem((int) CueUtil.MB512)
                    .setTotalGpuMem((int) CueUtil.MB512).build());
            return hostDao.findDispatchHost(HOST);
        }

        private VirtualProc proc(FrameDetail frame) {
            VirtualProc proc = new VirtualProc();
            proc.allocationId = host.allocationId;
            proc.coresReserved = 100;
            proc.hostId = host.id;
            proc.hostName = host.name;
            proc.jobId = job.id;
            proc.frameId = frame.id;
            proc.layerId = frame.layerId;
            proc.showId = frame.showId;
            return proc;
        }

        void destroy() {
            jobDao.deleteJob(job);
            jobDao.deleteJob(sibling);
            hostDao.deleteHost(host);
        }
    }
}
