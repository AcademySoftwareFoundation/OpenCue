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
import java.util.Collections;
import java.util.List;
import java.util.Map;
import javax.annotation.Resource;

import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.HistoricalDao;
import com.imageworks.spcue.dao.HistoricalDao.FrameHistoryBacklog;
import com.imageworks.spcue.dao.HistoricalDao.FrameHistoryDrain;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.test.AssumingPostgresEngine;
import com.imageworks.spcue.util.CueUtil;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

/**
 * Covers the frame_history queue: the trigger that enqueues events on frame state changes and
 * frame_history_drain(), which applies them to frame_history.
 *
 * Drains here run in wait mode, or with the drain lock already held by the test transaction, so the
 * background drainer cannot make a try-lock miss.
 */
@Transactional
@ContextConfiguration(classes = TestAppConfig.class, loader = AnnotationConfigContextLoader.class)
public class FrameHistoryQueueTests extends AbstractTransactionalJUnit4SpringContextTests {

    @Autowired
    @Rule
    public AssumingPostgresEngine assumingPostgresEngine;

    @Resource
    private JobManager jobManager;

    @Resource
    private JobLauncher jobLauncher;

    @Resource
    private HostManager hostManager;

    @Resource
    private FrameDao frameDao;

    @Resource
    private HistoricalDao historicalDao;

    private static final String HOST = "frame-history-host";
    private static final long DRAIN_LOCK_KEY = 19829062061618036L;

    private JobDetail job;
    private FrameInterface frame;

    @Before
    public void setUp() {
        jdbcTemplate.update("DELETE FROM frame_history_queue");

        RenderHost host = RenderHost.newBuilder().setName(HOST).setBootTime(1192369572)
                .setFreeMcp(CueUtil.GB).setFreeMem(53500).setFreeSwap(20760).setLoad(1)
                .setTotalMcp(CueUtil.GB4).setTotalMem(8173264).setTotalSwap(20960)
                .setNimbyEnabled(false).setNumProcs(1).setCoresPerProc(100)
                .setState(HardwareState.UP).setFacility("spi").build();
        hostManager.createHost(host);

        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
        frame = frameDao.findFrame(job, "0001-pass_1_preprocess");
    }

    private void startFrame() {
        jdbcTemplate.update(
                "UPDATE frame SET str_state='RUNNING', str_host=?, ts_started=current_timestamp "
                        + "WHERE pk_frame=?",
                HOST, frame.getFrameId());
    }

    private void stopFrame(String state, int exitStatus, long maxRss) {
        jdbcTemplate.update("UPDATE frame SET str_state=?, int_exit_status=?, int_mem_max_used=? "
                + "WHERE pk_frame=?", state, exitStatus, maxRss, frame.getFrameId());
    }

    private Map<String, Object> drain(int limit, boolean safe) {
        return jdbcTemplate.queryForMap(
                "SELECT drained, skipped, merged FROM frame_history_drain(?, true, ?)", limit,
                safe);
    }

    private List<Map<String, Object>> history() {
        return jdbcTemplate.queryForList(
                "SELECT * FROM frame_history WHERE pk_frame=? ORDER BY int_ts_stopped DESC",
                frame.getFrameId());
    }

    private int queueSize() {
        return jdbcTemplate.queryForObject("SELECT COUNT(*) FROM frame_history_queue",
                Integer.class);
    }

    @Test
    @Rollback(true)
    public void testFrameUpdateQueuesEventsInsteadOfWritingHistory() {
        startFrame();
        stopFrame("SUCCEEDED", 0, 1234);

        assertEquals(0, history().size());
        List<Map<String, Object>> events = jdbcTemplate.queryForList(
                "SELECT * FROM frame_history_queue WHERE pk_frame=? ORDER BY id",
                frame.getFrameId());
        assertEquals(2, events.size());

        Map<String, Object> start = events.get(0);
        assertEquals("S", start.get("str_event"));
        assertEquals(job.getJobId(), start.get("pk_job"));
        assertEquals(frame.getLayerId(), start.get("pk_layer"));
        assertEquals(HOST, start.get("str_host"));
        assertEquals(jdbcTemplate.queryForObject("SELECT pk_alloc FROM host WHERE str_name=?",
                String.class, HOST), start.get("pk_alloc"));

        Map<String, Object> stop = events.get(1);
        assertEquals("E", stop.get("str_event"));
        assertEquals(1234L, ((Number) stop.get("int_mem_max_used")).longValue());
        assertEquals(0L, ((Number) stop.get("int_exit_status")).longValue());
    }

    @Test
    @Rollback(true)
    public void testDrainAppliesStartAndStop() {
        startFrame();
        stopFrame("SUCCEEDED", 0, 1234);

        Map<String, Object> result = drain(100, false);
        assertEquals(2, result.get("drained"));
        assertEquals(0, result.get("skipped"));
        assertEquals(1, result.get("merged"));
        assertEquals(0, queueSize());

        List<Map<String, Object>> rows = history();
        assertEquals(1, rows.size());
        Map<String, Object> row = rows.get(0);
        assertEquals("RUNNING", row.get("str_state"));
        assertEquals(HOST, row.get("str_host"));
        assertEquals(1234L, ((Number) row.get("int_mem_max_used")).longValue());
        assertEquals(0, ((Number) row.get("int_exit_status")).intValue());
        assertEquals(0, ((Number) row.get("int_checkpoint_count")).intValue());
        int started = ((Number) row.get("int_ts_started")).intValue();
        int stopped = ((Number) row.get("int_ts_stopped")).intValue();
        assertEquals(true, started > 0 && stopped >= started);
    }

    @Test
    @Rollback(true)
    public void testDrainKeepsRetriesInOrder() {
        startFrame();
        stopFrame("WAITING", 1, 10);
        startFrame();

        // The first run is merged; the second start stays open.
        assertEquals(1, drain(100, false).get("merged"));

        List<Map<String, Object>> rows = history();
        assertEquals(2, rows.size());
        assertEquals(1, ((Number) rows.get(0).get("int_exit_status")).intValue());
        assertEquals(0, ((Number) rows.get(1).get("int_ts_stopped")).intValue());
    }

    @Test
    @Rollback(true)
    public void testExit299DiscardsOpenRun() {
        startFrame();
        drain(100, false);
        assertEquals(1, history().size());

        stopFrame("WAITING", 299, 0);
        assertEquals("X",
                jdbcTemplate.queryForObject(
                        "SELECT str_event FROM frame_history_queue WHERE pk_frame=?", String.class,
                        frame.getFrameId()));
        drain(100, false);
        assertEquals(0, history().size());
    }

    @Test
    @Rollback(true)
    public void testDrainRespectsLimitOldestFirst() {
        startFrame();
        stopFrame("SUCCEEDED", 0, 1);

        Map<String, Object> result = drain(1, false);
        assertEquals(1, result.get("drained"));
        assertEquals(0, result.get("merged"));
        assertEquals("E", jdbcTemplate.queryForObject("SELECT str_event FROM frame_history_queue",
                String.class));
        assertEquals(1, history().size());
        assertEquals(0, ((Number) history().get(0).get("int_ts_stopped")).intValue());

        drain(1, false);
        assertEquals(0, queueSize());
        assertEquals(true, ((Number) history().get(0).get("int_ts_stopped")).intValue() > 0);
    }

    @Test
    @Rollback(true)
    public void testDrainSkipsOrphanedStart() {
        jdbcTemplate.update(
                "INSERT INTO frame_history_queue "
                        + "(str_event, pk_frame, int_ts, pk_layer, pk_job, str_name, int_cores, "
                        + "int_mem_reserved, int_gpus, int_gpu_mem_reserved) "
                        + "VALUES ('S', ?, 1, ?, ?, 'orphan', 100, 0, 0, 0)",
                frame.getFrameId(), frame.getLayerId(), "00000000-0000-0000-0000-000000000000");

        Map<String, Object> result = drain(100, false);
        assertEquals(1, result.get("drained"));
        assertEquals(1, result.get("skipped"));
        assertEquals(0, queueSize());
        assertEquals(0, history().size());
    }

    @Test
    @Rollback(true)
    public void testSafeModeDropsFailingEventAndAppliesTheRest() {
        // frame.int_exit_status is wider than frame_history.int_exit_status, so this run cannot
        // be applied.
        startFrame();
        stopFrame("DEAD", 100000, 1);
        startFrame();

        Map<String, Object> result = drain(100, true);
        assertEquals(3, result.get("drained"));
        assertEquals(1, result.get("skipped"));
        assertEquals(0, queueSize());

        List<Map<String, Object>> rows = history();
        assertEquals(1, rows.size());
        assertEquals(HOST, rows.get(0).get("str_host"));
    }

    @Test
    @Rollback(true)
    public void testDrainTruncatesLongHostName() {
        // frame.str_host is wider than frame_history.str_host.
        String longHost = String.join("", Collections.nCopies(100, "h"));
        jdbcTemplate.update("UPDATE frame SET str_state='RUNNING', str_host=? WHERE pk_frame=?",
                longHost, frame.getFrameId());

        Map<String, Object> result = drain(100, false);
        assertEquals(1, result.get("drained"));
        assertEquals(0, result.get("skipped"));
        assertEquals(longHost.substring(0, 64), history().get(0).get("str_host"));
    }

    @Test
    @Rollback(true)
    public void testDisableHistorySkipsQueue() {
        jdbcTemplate.update(
                "INSERT INTO config (pk_config, str_key) VALUES (uuid_generate_v1(), 'DISABLE_HISTORY')");
        startFrame();
        stopFrame("SUCCEEDED", 0, 1);
        assertEquals(0, queueSize());
    }

    @Test
    @Rollback(true)
    public void testDaoDrainAndBacklog() {
        FrameHistoryBacklog empty = historicalDao.getFrameHistoryBacklog();
        assertEquals(0, empty.depth);
        assertEquals(0, empty.oldestAgeSeconds);

        startFrame();
        stopFrame("SUCCEEDED", 0, 1);
        FrameHistoryBacklog backlog = historicalDao.getFrameHistoryBacklog();
        assertEquals(2, backlog.depth);

        // Holding the lock in this transaction makes the DAO's try-lock re-entrant.
        jdbcTemplate.queryForObject("SELECT pg_advisory_xact_lock(?)::text", String.class,
                DRAIN_LOCK_KEY);
        FrameHistoryDrain result = historicalDao.drainFrameHistory(100, false);
        assertEquals(2, result.drained);
        assertEquals(0, result.skipped);
        assertEquals(1, history().size());
        assertEquals(0, historicalDao.getFrameHistoryBacklog().depth);
    }

    @Test
    @Rollback(true)
    public void testDrainHandlesEndWithoutOpenRun() {
        jdbcTemplate.update(
                "INSERT INTO frame_history_queue "
                        + "(str_event, pk_frame, int_ts, int_mem_max_used, int_gpu_mem_max_used, "
                        + "int_exit_status, int_checkpoint_count) VALUES ('E', ?, 1, 0, 0, 0, 0)",
                frame.getFrameId());

        Map<String, Object> result = drain(100, false);
        assertEquals(1, result.get("drained"));
        assertEquals(0, result.get("skipped"));
        assertEquals(0, history().size());
        assertNull(
                jdbcTemplate.queryForObject("SELECT max(id) FROM frame_history_queue", Long.class));
    }

    @Test
    @Rollback(true)
    public void testStartThenDiscardInOneBatchWritesNothing() {
        startFrame();
        stopFrame("WAITING", 299, 0);

        Map<String, Object> result = drain(100, false);
        assertEquals(2, result.get("drained"));
        assertEquals(0, result.get("skipped"));
        assertEquals(0, result.get("merged"));
        assertEquals(0, queueSize());
        assertEquals(0, history().size());
    }

    @Test
    @Rollback(true)
    public void testMergedRunMatchesSeparateApply() {
        String columns = "str_event, pk_frame, int_ts, pk_layer, pk_job, str_name, str_host, "
                + "pk_alloc, int_cores, int_mem_reserved, int_gpus, int_gpu_mem_reserved, "
                + "int_mem_max_used, int_gpu_mem_max_used, int_exit_status, int_checkpoint_count";
        startFrame();
        stopFrame("DEAD", 1, 4321);
        List<Map<String, Object>> events = jdbcTemplate
                .queryForList("SELECT " + columns + " FROM frame_history_queue ORDER BY id");

        // One event per batch: start and end are applied as INSERT then UPDATE.
        drain(1, false);
        drain(1, false);
        Map<String, Object> separate = historyWithoutKeys();

        jdbcTemplate.update("DELETE FROM frame_history WHERE pk_frame=?", frame.getFrameId());
        for (Map<String, Object> ev : events) {
            jdbcTemplate.update(
                    "INSERT INTO frame_history_queue (" + columns
                            + ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    ev.values().toArray());
        }
        Map<String, Object> result = drain(100, false);
        assertEquals(1, result.get("merged"));

        assertEquals(separate, historyWithoutKeys());
    }

    private Map<String, Object> historyWithoutKeys() {
        List<Map<String, Object>> rows = history();
        assertEquals(1, rows.size());
        Map<String, Object> row = rows.get(0);
        row.remove("pk_frame_history");
        row.remove("dt_last_modified");
        return row;
    }
}
