
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



package com.imageworks.spcue.test.dao.postgres;

import com.google.common.collect.ImmutableList;
import com.imageworks.spcue.*;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dao.ProcDao;
import com.imageworks.spcue.dao.criteria.FrameSearchFactory;
import com.imageworks.spcue.dao.criteria.FrameSearchInterface;
import com.imageworks.spcue.depend.FrameOnFrame;
import com.imageworks.spcue.dispatcher.DispatchSupport;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.job.CheckpointState;
import com.imageworks.spcue.grpc.job.FrameSearchCriteria;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.DependManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.test.context.transaction.AfterTransaction;
import org.springframework.test.context.transaction.BeforeTransaction;
import org.springframework.transaction.annotation.Transactional;

import java.io.File;
import java.util.Map;

import static org.junit.Assert.*;


@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class FrameDaoTests extends AbstractTransactionalJUnit4SpringContextTests  {
    
    @Autowired
    FrameDao frameDao;

    @Autowired
    JobManager jobManager;

    @Autowired
    JobLauncher jobLauncher;

    @Autowired
    HostDao hostDao;

    @Autowired
    ProcDao procDao;

    @Autowired
    HostManager hostManager;

    @Autowired
    DependManager dependManager;

    @Autowired
    DispatchSupport dispatchSupport;

    @Autowired
    FrameSearchFactory frameSearchFactory;

    private static final String HOST = "beta";

    public DispatchHost createHost() {
        return hostDao.findDispatchHost(HOST);
    }

    @BeforeTransaction
    public void create() {

        RenderHost host = RenderHost.newBuilder()
                .setName(HOST)
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
                .addAllTags(ImmutableList.of("mcore", "4core", "8g"))
                .setState(HardwareState.UP)
                .setFacility("spi")
                .putAttributes("freeGpu", "512")
                .putAttributes("totalGpu", "512")
                .build();

        hostManager.createHost(host);
    }

    @AfterTransaction
    public void destroy() {
        jdbcTemplate.update(
            "DELETE FROM host WHERE str_name=?",HOST);
    }

    public JobDetail launchJob() {
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        return jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testCheckRetries() {
        JobDetail job = launchJob();
        frameDao.checkRetries(frameDao.findFrame(job,"0001-pass_1"));
        // TODO: check to see if it actually works
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetFrameDetail() {
        JobDetail job = launchJob();
        FrameInterface f = frameDao.findFrame(job, "0001-pass_1");
        FrameDetail frame = frameDao.getFrameDetail(f);
        frame = frameDao.getFrameDetail(f.getFrameId());
        assertEquals("0001-pass_1", frame.name);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindFrameDetail() {
        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");
        assertEquals("0001-pass_1", frame.name);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetFrame() {
        JobDetail job = launchJob();
        FrameInterface f = frameDao.findFrame(job, "0001-pass_1");
        FrameInterface frame = frameDao.getFrame(f.getFrameId());
        assertEquals("0001-pass_1", frame.getName());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetFrameByLayer() {
        JobDetail job = launchJob();
        FrameInterface f = frameDao.findFrame(job, "0001-pass_1");
        FrameInterface f2 = frameDao.findFrame((LayerInterface) f, 1);

        assertEquals(f.getFrameId(), f2.getFrameId());
        assertEquals(f.getLayerId(), f2.getLayerId());
        assertEquals(f.getJobId(), f2.getJobId());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindFrame() {
        JobDetail job = launchJob();
        FrameInterface f = frameDao.findFrame(job, "0001-pass_1");
        assertEquals(f.getName(),"0001-pass_1");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindFrames() {
        JobDetail job = launchJob();
        FrameSearchInterface r = frameSearchFactory.create(job);
        FrameSearchCriteria criteria = r.getCriteria();
        r.setCriteria(criteria.toBuilder()
                .addFrames("0001-pass_1")
                .build());
        assertEquals(1, frameDao.findFrames(r).size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindFrameDetails() {
        JobDetail job = launchJob();
        FrameSearchInterface r = frameSearchFactory.create(job);
        FrameSearchCriteria criteria = r.getCriteria();
        r.setCriteria(criteria.toBuilder()
                .addFrames("0001-pass_1")
                .build());
        assertEquals(1, frameDao.findFrameDetails(r).size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testgetOrphanedFrames() {
        assertEquals(0, frameDao.getOrphanedFrames().size());

        JobDetail job = launchJob();
        FrameInterface f = frameDao.findFrame(job, "0001-pass_1");

        /*
         * Update the first frame to the orphan state, which is a frame
         * that is in the running state, has no corresponding proc entry
         * and has not been updated in the last 5 min.
         */
        jdbcTemplate.update(
                "UPDATE frame SET str_state = 'RUNNING', " +
                "ts_updated = current_timestamp - interval '301' second WHERE pk_frame = ?",
                f.getFrameId());

        assertEquals(1, frameDao.getOrphanedFrames().size());
        assertTrue(frameDao.isOrphan(f));

    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateFrameState() {
        JobDetail job = launchJob();
        FrameInterface f = frameDao.findFrame(job, "0001-pass_1");
        assertTrue(frameDao.updateFrameState(f, FrameState.RUNNING));

        assertEquals(FrameState.RUNNING.toString(),
                jdbcTemplate.queryForObject(
                "SELECT str_state FROM frame WHERE pk_frame=?",
                String.class,
                f.getFrameId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFailUpdateFrameState() {
        JobDetail job = launchJob();
        FrameInterface f = frameDao.findFrame(job, "0001-pass_1");

        /** Change the version so the update fails **/
        jdbcTemplate.update(
                "UPDATE frame SET int_version = int_version + 1 WHERE pk_frame=?",
                f.getFrameId());

        assertEquals(false, frameDao.updateFrameState(f, FrameState.RUNNING));
    }


    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateFrameStarted() {

        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1_preprocess");
        DispatchFrame fd = frameDao.getDispatchFrame(frame.getId());
        VirtualProc proc = new VirtualProc();
        proc.allocationId = host.allocationId;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;

        assertEquals(FrameState.WAITING, frame.state);

        procDao.insertVirtualProc(proc);
        procDao.verifyRunningProc(proc.getId(), frame.getId());
        frameDao.updateFrameStarted(proc, fd);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateFrameStopped() {

        DispatchHost host = createHost();
        JobDetail job = launchJob();

        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1_preprocess");
        DispatchFrame fd = frameDao.getDispatchFrame(frame.getId());

        assertEquals("0001-pass_1_preprocess",frame.getName());
        assertEquals(FrameState.WAITING,frame.state);

        VirtualProc proc = new VirtualProc();
        proc.allocationId = host.allocationId;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;

        procDao.insertVirtualProc(proc);
        procDao.verifyRunningProc(proc.getId(), frame.getId());

        frameDao.updateFrameStarted(proc, fd);

        try {
            Thread.sleep(1001);
        } catch (InterruptedException e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
        }

        DispatchFrame fd2 = frameDao.getDispatchFrame(frame.getId());
        assertTrue(frameDao.updateFrameStopped(fd2, FrameState.DEAD, 1, 1000l));

        assertEquals(FrameState.DEAD.toString(),jdbcTemplate.queryForObject(
                "SELECT str_state FROM frame WHERE pk_frame=?",
                String.class, frame.getFrameId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateFrameFixed() {

        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1_preprocess");
        DispatchFrame fd = frameDao.getDispatchFrame(frame.getId());

        assertEquals("0001-pass_1_preprocess",frame.getName());
        assertEquals(FrameState.WAITING,frame.state);

        VirtualProc proc = new VirtualProc();
        proc.allocationId = host.allocationId;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;

        procDao.insertVirtualProc(proc);
        procDao.verifyRunningProc(proc.getId(), frame.getId());
        frameDao.updateFrameStarted(proc, fd);

        try {
            Thread.sleep(1001);
        } catch (InterruptedException e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
        }
        frameDao.updateFrameState(frame, FrameState.WAITING);
        frameDao.updateFrameFixed(proc, frame);

        assertEquals(FrameState.RUNNING.toString(),
                jdbcTemplate.queryForObject(
                "SELECT str_state FROM frame WHERE pk_frame=?",
                String.class, frame.getFrameId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetDispatchFrame() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = host.allocationId;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;

        procDao.insertVirtualProc(proc);
        procDao.verifyRunningProc(proc.getId(), frame.getId());

        DispatchFrame dframe = frameDao.getDispatchFrame(frame.id);
        assertEquals(dframe.id, frame.id);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testMarkFrameAsWaiting() {
        JobDetail job = launchJob();

        FrameInterface f = frameDao.findFrameDetail(job, "0001-pass_1");
        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT int_depend_count FROM frame WHERE pk_frame=?",
                Integer.class, f.getFrameId()));

        frameDao.markFrameAsWaiting(f);
        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT int_depend_count FROM frame WHERE pk_frame=?",
                Integer.class, f.getFrameId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testMarkFrameAsDepend() {
        JobDetail job = launchJob();

        FrameInterface f = frameDao.findFrameDetail(job, "0001-pass_1");
        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT int_depend_count FROM frame WHERE pk_frame=?",
                Integer.class, f.getFrameId()));

        assertTrue(jdbcTemplate.queryForObject(
                "SELECT b_active FROM depend WHERE pk_layer_depend_er=?",
                Boolean.class, f.getLayerId()));

        frameDao.markFrameAsWaiting(f);
        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT int_depend_count FROM frame WHERE pk_frame=?",
                Integer.class, f.getFrameId()));

        /*
         * Need to grab new version of frame
         * object once the state has changed.
         */
        f = frameDao.findFrameDetail(job, "0001-pass_1");

        frameDao.markFrameAsDepend(f);
        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT int_depend_count FROM frame WHERE pk_frame=?",
                Integer.class, f.getFrameId()));
    }

    @Test(expected=org.springframework.dao.EmptyResultDataAccessException.class)
    @Transactional
    @Rollback(true)
    public void testFindLongestFrame() {
        JobDetail job = launchJob();
        frameDao.findLongestFrame(job);
    }

    @Test(expected=org.springframework.dao.EmptyResultDataAccessException.class)
    @Transactional
    @Rollback(true)
    public void testFindShortestFrame() {
        JobDetail job = launchJob();
        frameDao.findShortestFrame(job);
    }

    @Test(expected=org.springframework.dao.EmptyResultDataAccessException.class)
    @Transactional
    @Rollback(true)
    public void findHighestMemoryFrame() {
        JobDetail job = launchJob();
        frameDao.findHighestMemoryFrame(job);
    }

    @Test(expected=org.springframework.dao.EmptyResultDataAccessException.class)
    @Transactional
    @Rollback(true)
    public void findLowestMemoryFrame() {
        JobDetail job = launchJob();
        frameDao.findLowestMemoryFrame(job);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetDependentFrames() {
        JobDetail job = launchJob();
        FrameInterface frame_a = frameDao.findFrame(job, "0001-pass_1");
        FrameInterface frame_b = frameDao.findFrame(job, "0002-pass_1");

        dependManager.createDepend(new FrameOnFrame(
                frame_a, frame_b));

        assertEquals(1, frameDao.getDependentFrames(
                dependManager.getWhatDependsOn(frame_b).get(0)).size(),1);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetResourceUsage() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = host.allocationId;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;

        procDao.insertVirtualProc(proc);
        procDao.verifyRunningProc(proc.getId(), frame.getId());

        DispatchFrame dframe = frameDao.getDispatchFrame(frame.id);
        frameDao.getResourceUsage(dframe);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateFrameCleared() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = host.allocationId;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;

        procDao.insertVirtualProc(proc);
        procDao.verifyRunningProc(proc.getId(), frame.getId());

        /*
         * Only frames without active procs can be cleared.
         */

        DispatchFrame dframe = frameDao.getDispatchFrame(frame.id);
        assertFalse(frameDao.updateFrameCleared(dframe));

        dispatchSupport.unbookProc(proc);
        assertTrue(frameDao.updateFrameCleared(dframe));

    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetStaleCheckpoints() {

        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1_preprocess");

        assertEquals(0, frameDao.getStaleCheckpoints(300).size());
        jdbcTemplate.update("UPDATE frame SET str_state = ?, " +
                "ts_stopped = current_timestamp - interval '400' second WHERE pk_frame = ?",
                FrameState.CHECKPOINT.toString(), frame.getFrameId());
        assertEquals(1, frameDao.getStaleCheckpoints(300).size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testSetCheckpointState() {

        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1_preprocess");

        frameDao.updateFrameCheckpointState(frame, CheckpointState.ENABLED);

        String state = jdbcTemplate.queryForObject(
                "SELECT str_checkpoint_state FROM frame WHERE pk_frame=?",
                String.class, frame.getFrameId());

        assertEquals(CheckpointState.ENABLED.toString(), state);

        /**
         * To set a checkpoint complete the frame state must be in the checkpoint state.
         */
        frameDao.updateFrameState(frame, FrameState.CHECKPOINT);
        jdbcTemplate.update(
                "UPDATE frame SET ts_started=current_timestamp, ts_stopped=current_timestamp + INTERVAL '20' second WHERE pk_frame=?",
                frame.getFrameId());

        assertTrue(frameDao.updateFrameCheckpointState(frame, CheckpointState.COMPLETE));
        Map<String, Object> result = jdbcTemplate.queryForMap(
                "SELECT int_checkpoint_count FROM frame WHERE pk_frame=?",
                frame.getFrameId());

        Integer checkPointCount = (Integer) result.get("int_checkpoint_count");
        assertEquals(1, checkPointCount.intValue());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testIsFrameComplete() {

        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1_preprocess");

        frameDao.updateFrameState(frame, FrameState.EATEN);
        assertTrue(frameDao.isFrameComplete(frame));

        frame = frameDao.findFrameDetail(job, "0001-pass_1_preprocess");
        frameDao.updateFrameState(frame, FrameState.SUCCEEDED);
        assertTrue(frameDao.isFrameComplete(frame));

        frame = frameDao.findFrameDetail(job, "0001-pass_1_preprocess");
        frameDao.updateFrameState(frame, FrameState.WAITING);
        assertFalse(frameDao.isFrameComplete(frame));
    }
}
