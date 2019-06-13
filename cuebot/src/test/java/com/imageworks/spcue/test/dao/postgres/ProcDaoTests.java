
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

import com.imageworks.spcue.*;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.*;
import com.imageworks.spcue.dao.criteria.*;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.ResourceReservationFailureException;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.host.ProcSearchCriteria;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.util.CueUtil;
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

import static org.junit.Assert.*;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class ProcDaoTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Autowired
    ProcDao procDao;

    @Autowired
    HostDao hostDao;

    @Autowired
    JobManager jobManager;

    @Autowired
    JobLauncher jobLauncher;

    @Autowired
    FrameDao frameDao;

    @Autowired
    LayerDao layerDao;

    @Autowired
    DispatcherDao dispatcherDao;

    @Autowired
    HostManager hostManager;

    @Autowired
    AdminManager adminManager;

    @Autowired
    Dispatcher dispatcher;

    @Autowired
    FrameSearchFactory frameSearchFactory;
    
    @Autowired
    ProcSearchFactory procSearchFactory;

    private static String PK_ALLOC = "00000000-0000-0000-0000-000000000000";

    public DispatchHost createHost() {

        RenderHost host = RenderHost.newBuilder()
                .setName("beta")
                .setBootTime(1192369572)
                .setFreeMcp(76020)
                .setFreeMem(53500)
                .setFreeSwap(20760)
                .setLoad(1)
                .setTotalMcp(195430)
                .setTotalMem((int) CueUtil.GB32)
                .setTotalSwap(20960)
                .setNimbyEnabled(false)
                .setNumProcs(8)
                .setCoresPerProc(100)
                .setState(HardwareState.UP)
                .setFacility("spi")
                .build();

        DispatchHost dh = hostManager.createHost(host);
        hostManager.setAllocation(dh,
                adminManager.findAllocationDetail("spi", "general"));

        return hostDao.findDispatchHost("beta");
    }

    public JobDetail launchJob() {
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        return jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
    }

    @Before
    public void setDispatcherTestMode() {
        dispatcher.setTestMode(true);
        jobLauncher.testMode = true;
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDontVerifyRunningProc() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail fd = frameDao.findFrameDetail(job, "0001-pass_1_preprocess");
        DispatchFrame frame = frameDao.getDispatchFrame(fd.getId());
        VirtualProc proc = VirtualProc.build(host, frame);
        dispatcher.dispatch(frame, proc);

        // Confirm was have a running frame.
        assertEquals("RUNNING", jdbcTemplate.queryForObject(
                "SELECT str_state FROM frame WHERE pk_frame=?",
                String.class, frame.id));

        assertTrue(procDao.verifyRunningProc(proc.getId(), frame.getId()));
        jobManager.shutdownJob(job);

       int result =  jdbcTemplate.update(
                "UPDATE job SET ts_stopped = " +
                "current_timestamp - interval '10' minute " +
                "WHERE pk_job=?", job.id);

        assertEquals(1, result);
        assertFalse(procDao.verifyRunningProc(proc.getId(), frame.getId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertVirtualProc() {

        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;

        procDao.insertVirtualProc(proc);
        procDao.verifyRunningProc(proc.getId(), frame.getId());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDeleteVirtualProc() {

        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;

        procDao.insertVirtualProc(proc);
        procDao.verifyRunningProc(proc.getId(), frame.getId());
        procDao.deleteVirtualProc(proc);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testClearVirtualProcAssignment() {

        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;

        procDao.insertVirtualProc(proc);
        procDao.verifyRunningProc(proc.getId(), frame.getId());
        procDao.clearVirtualProcAssignment(proc);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testClearVirtualProcAssignmentByFrame() {

        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;

        procDao.insertVirtualProc(proc);
        procDao.verifyRunningProc(proc.getId(), frame.getId());
        assertTrue(procDao.clearVirtualProcAssignment(frame));
    }


    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateVirtualProcAssignment() {

        DispatchHost host = createHost();

        JobDetail job = launchJob();
        FrameDetail frame1 = frameDao.findFrameDetail(job, "0001-pass_1");
        FrameDetail frame2 = frameDao.findFrameDetail(job, "0002-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame1.id;
        proc.layerId = frame1.layerId;
        proc.showId = frame1.showId;

        procDao.insertVirtualProc(proc);
        procDao.verifyRunningProc(proc.getId(), frame1.getId());

        proc.frameId = frame2.id;

        procDao.updateVirtualProcAssignment(proc);
        procDao.verifyRunningProc(proc.getId(), frame2.getId());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateProcMemoryUsage() {

        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;

        procDao.insertVirtualProc(proc);
        procDao.verifyRunningProc(proc.getId(), frame.getId());

        procDao.updateProcMemoryUsage(frame, 100, 100, 1000, 1000);

    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetVirtualProc() {
        DispatchHost host = createHost();

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM host WHERE pk_host=?",
                Integer.class, host.id));

        JobDetail job = launchJob();
        FrameDetail fd = frameDao.findFrameDetail(job, "0001-pass_1_preprocess");

        DispatchFrame frame = frameDao.getDispatchFrame(fd.getId());
        VirtualProc proc = VirtualProc.build(host, frame);
        dispatcher.dispatch(frame, proc);

        assertTrue(procDao.verifyRunningProc(proc.getId(), frame.getId()));

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM proc WHERE pk_proc=?",
                Integer.class, proc.id));


        VirtualProc verifyProc = procDao.getVirtualProc(proc.getId());
        assertEquals(host.allocationId, verifyProc.allocationId);
        assertEquals(proc.coresReserved, verifyProc.coresReserved);
        assertEquals(proc.frameId, verifyProc.frameId);
        assertEquals(proc.hostId, verifyProc.hostId);
        assertEquals(proc.id, verifyProc.id);
        assertEquals(proc.jobId, verifyProc.jobId);
        assertEquals(proc.layerId, verifyProc.layerId);
        assertEquals(proc.showId, verifyProc.showId);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindVirtualProc() {

        DispatchHost host = createHost();

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM host WHERE pk_host=?",
                Integer.class, host.id));

        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;
        procDao.insertVirtualProc(proc);

        procDao.findVirtualProc(frame);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindVirtualProcs() {

        DispatchHost host = createHost();

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM host WHERE pk_host=?",
                Integer.class, host.id));

        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;
        procDao.insertVirtualProc(proc);

        assertEquals(1, procDao.findVirtualProcs(HardwareState.UP).size());
        assertEquals(1, procDao.findVirtualProcs(host).size());
        assertEquals(1, procDao.findVirtualProcs(job).size());
        assertEquals(1, procDao.findVirtualProcs(frame).size());
        assertEquals(1, procDao.findVirtualProcs(frameSearchFactory.create(job)).size());
        assertEquals(1, procDao.findVirtualProcs(frameSearchFactory.create((LayerInterface) frame)).size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindOrphanedVirtualProcs() {
        DispatchHost host = createHost();

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM host WHERE pk_host=?",
                Integer.class, host.id));

        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;
        procDao.insertVirtualProc(proc);

        assertEquals(0, procDao.findOrphanedVirtualProcs().size());

        /**
        * This is destructive to running jobs
        */
        jdbcTemplate.update(
        "UPDATE proc SET ts_ping = (current_timestamp - interval '30' day)");

        assertEquals(1, procDao.findOrphanedVirtualProcs().size());
        assertTrue(procDao.isOrphan(proc));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUnbookProc() {

        DispatchHost host = createHost();

        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;
        procDao.insertVirtualProc(proc);

        procDao.unbookProc(proc);
        assertTrue(jdbcTemplate.queryForObject(
                "SELECT b_unbooked FROM proc WHERE pk_proc=?",
                Boolean.class, proc.id));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUnbookVirtualProcs() {

        DispatchHost host = createHost();

        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;
        procDao.insertVirtualProc(proc);


        List<VirtualProc> procs = new ArrayList<VirtualProc>();
        procs.add(proc);

        procDao.unbookVirtualProcs(procs);

        assertTrue(jdbcTemplate.queryForObject(
                "SELECT b_unbooked FROM proc WHERE pk_proc=?",
                Boolean.class, proc.id));
    }


    @Test(expected=ResourceReservationFailureException.class)
    @Transactional
    @Rollback(true)
    public void testIncreaseReservedMemoryFail() {

        DispatchHost host = createHost();
        JobDetail job = launchJob();

        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;
        procDao.insertVirtualProc(proc);

        procDao.increaseReservedMemory(proc, 8173264l * 8);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testIncreaseReservedMemory() {

        DispatchHost host = createHost();
        JobDetail job = launchJob();

        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;
        procDao.insertVirtualProc(proc);

        procDao.increaseReservedMemory(proc, 3145728);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindReservedMemoryOffender() {
        DispatchHost host = createHost();


        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_dispatch_test.xml"));
        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_dispatch_test_v1");
        jobManager.setJobPaused(job, false);

        int i = 1;
        List<DispatchFrame> frames  = dispatcherDao.findNextDispatchFrames(job, host, 6);
        assertEquals(6, frames.size());

        for (DispatchFrame frame: frames) {

            VirtualProc proc = VirtualProc.build(host, frame);
            frame.minMemory = Dispatcher.MEM_RESERVED_DEFAULT;
            dispatcher.dispatch(frame, proc);

            // Increase the memory usage as frames are added
            procDao.updateProcMemoryUsage(frame,
                    1000*i, 1000*i, 1000*i, 1000*i);
            i++;
        }

        // Now compare the last frame which has the highest memory
        // usage to the what is returned by getWorstMemoryOffender
        VirtualProc offender = procDao.getWorstMemoryOffender(host);

        FrameDetail f = frameDao.getFrameDetail(frames.get(5));
        FrameDetail o = frameDao.getFrameDetail(offender);

        assertEquals(f.getName(), o.getName());
        assertEquals(f.id, o.getFrameId());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetReservedMemory() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();

        FrameDetail frameDetail = frameDao.findFrameDetail(job, "0001-pass_1");
        DispatchFrame frame = frameDao.getDispatchFrame(frameDetail.id);

        VirtualProc proc = VirtualProc.build(host, frame);
        proc.frameId = frame.id;
        procDao.insertVirtualProc(proc);

        VirtualProc _proc = procDao.findVirtualProc(frame);
        assertEquals(Long.valueOf(Dispatcher.MEM_RESERVED_DEFAULT), jdbcTemplate.queryForObject(
                        "SELECT int_mem_reserved FROM proc WHERE pk_proc=?",
                        Long.class, _proc.id));
        assertEquals(Dispatcher.MEM_RESERVED_DEFAULT,
                procDao.getReservedMemory(_proc));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetReservedGpu() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();

        FrameDetail frameDetail = frameDao.findFrameDetail(job, "0001-pass_1");
        DispatchFrame frame = frameDao.getDispatchFrame(frameDetail.id);

        VirtualProc proc = VirtualProc.build(host, frame);
        proc.frameId = frame.id;
        procDao.insertVirtualProc(proc);

        VirtualProc _proc = procDao.findVirtualProc(frame);
        assertEquals(Long.valueOf(Dispatcher.GPU_RESERVED_DEFAULT), jdbcTemplate.queryForObject(
                        "SELECT int_gpu_reserved FROM proc WHERE pk_proc=?",
                        Long.class, _proc.id));
        assertEquals(Dispatcher.GPU_RESERVED_DEFAULT,
                procDao.getReservedGpu(_proc));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testBalanceUnderUtilizedProcs() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();

        FrameDetail frameDetail1 = frameDao.findFrameDetail(job, "0001-pass_1");
        DispatchFrame frame1 = frameDao.getDispatchFrame(frameDetail1.id);

        VirtualProc proc1 = VirtualProc.build(host, frame1);
        proc1.frameId = frame1.id;
        procDao.insertVirtualProc(proc1);

        procDao.updateProcMemoryUsage(frame1, 250000, 250000, 250000, 250000);
        layerDao.updateLayerMaxRSS(frame1, 250000, true);

        FrameDetail frameDetail2 = frameDao.findFrameDetail(job, "0002-pass_1");
        DispatchFrame frame2 = frameDao.getDispatchFrame(frameDetail2.id);

        VirtualProc proc2 = VirtualProc.build(host, frame2);
        proc2.frameId = frame2.id;
        procDao.insertVirtualProc(proc2);

        procDao.updateProcMemoryUsage(frame2, 255000, 255000,255000, 255000);
        layerDao.updateLayerMaxRSS(frame2, 255000, true);

        FrameDetail frameDetail3 = frameDao.findFrameDetail(job, "0003-pass_1");
        DispatchFrame frame3 = frameDao.getDispatchFrame(frameDetail3.id);

        VirtualProc proc3 = VirtualProc.build(host, frame3);
        proc3.frameId = frame3.id;
        procDao.insertVirtualProc(proc3);

        procDao.updateProcMemoryUsage(frame3, 3145728, 3145728,3145728, 3145728);
        layerDao.updateLayerMaxRSS(frame3,300000, true);

        procDao.balanceUnderUtilizedProcs(proc3, 100000);
        procDao.increaseReservedMemory(proc3, Dispatcher.MEM_RESERVED_DEFAULT + 100000);

        // Check the target proc
        VirtualProc targetProc = procDao.getVirtualProc(proc3.getId());
        assertEquals( Dispatcher.MEM_RESERVED_DEFAULT+ 100000, targetProc.memoryReserved);

        // Check other procs
        VirtualProc firstProc = procDao.getVirtualProc(proc1.getId());
        assertEquals( Dispatcher.MEM_RESERVED_DEFAULT - 50000 -1 , firstProc.memoryReserved);

        VirtualProc secondProc = procDao.getVirtualProc(proc2.getId());
        assertEquals(Dispatcher.MEM_RESERVED_DEFAULT - 50000 -1, secondProc.memoryReserved);

    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetCurrentShowId() {

        DispatchHost host = createHost();
        JobDetail job = launchJob();

        FrameDetail frameDetail = frameDao.findFrameDetail(job, "0001-pass_1_preprocess");
        DispatchFrame frame = frameDao.getDispatchFrame(frameDetail.id);

        VirtualProc proc = VirtualProc.build(host, frame);
        proc.frameId = frame.id;
        procDao.insertVirtualProc(proc);

        assertEquals(job.getShowId(), procDao.getCurrentShowId(proc));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetCurrentJobId() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();

        FrameDetail frameDetail = frameDao.findFrameDetail(job, "0001-pass_1_preprocess");
        DispatchFrame frame = frameDao.getDispatchFrame(frameDetail.id);

        VirtualProc proc = VirtualProc.build(host, frame);
        proc.frameId = frame.id;
        procDao.insertVirtualProc(proc);

        assertEquals(job.getJobId(), procDao.getCurrentJobId(proc));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetCurrentLayerId() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();

        FrameDetail frameDetail = frameDao.findFrameDetail(job, "0001-pass_1_preprocess");
        DispatchFrame frame = frameDao.getDispatchFrame(frameDetail.id);

        VirtualProc proc = VirtualProc.build(host, frame);
        proc.frameId = frame.id;
        procDao.insertVirtualProc(proc);

        assertEquals(frame.getLayerId(), procDao.getCurrentLayerId(proc));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetCurrentFrameId() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();

        FrameDetail frameDetail = frameDao.findFrameDetail(job, "0001-pass_1_preprocess");
        DispatchFrame frame = frameDao.getDispatchFrame(frameDetail.id);

        VirtualProc proc = VirtualProc.build(host, frame);
        proc.frameId = frame.id;
        procDao.insertVirtualProc(proc);

        assertEquals(frame.getFrameId(), procDao.getCurrentFrameId(proc));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getProcsBySearch() {
        DispatchHost host = createHost();

        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_dispatch_test.xml"));
        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_dispatch_test_v1");

        /*
         * Book 5 procs.
         */
        for (int i=1; i<6; i++) {
            FrameDetail f = frameDao.findFrameDetail(job, String.format("%04d-pass_1",i));
            VirtualProc proc = new VirtualProc();
            proc.allocationId = null;
            proc.coresReserved = 100;
            proc.hostId = host.id;
            proc.hostName = host.name;
            proc.jobId = job.id;
            proc.frameId = f.id;
            proc.layerId = f.layerId;
            proc.showId = f.showId;
            procDao.insertVirtualProc(proc);
        }

        ProcSearchInterface r;

        /*
         * Search for all 5 running procs
         */
        r = procSearchFactory.create();
        r.addSort(new Sort("proc.ts_booked",Direction.ASC));
        ProcSearchCriteria criteriaA = r.getCriteria();
        r.setCriteria(criteriaA.toBuilder().addShows("pipe").build());
        assertEquals(5, procDao.findVirtualProcs(r).size());

        /*
         * Limit the result to 1 result.
         */
        r = procSearchFactory.create();
        ProcSearchCriteria criteriaB = r.getCriteria();
        r.setCriteria(criteriaB.toBuilder().addShows("pipe").addMaxResults(1).build());
        assertEquals(1, procDao.findVirtualProcs(r).size());

        /*
         * Change the first result to 1, which should limt
         * the result to 4.
         */
        r = procSearchFactory.create();
        ProcSearchCriteria criteriaC = r.getCriteria();
        r.setCriteria(criteriaC.toBuilder().addShows("pipe").setFirstResult(2).build());
        r.addSort(new Sort("proc.ts_booked",Direction.ASC));
        assertEquals(4, procDao.findVirtualProcs(r).size());

        /*
         * Now try to do the eqivalent of a limit/offset
         */
        r = procSearchFactory.create();
        ProcSearchCriteria criteriaD = r.getCriteria();
        r.setCriteria(criteriaD.toBuilder()
                .addShows("pipe")
                .setFirstResult(3)
                .addMaxResults(2)
                .build());
        assertEquals(2, procDao.findVirtualProcs(r).size());

    }
}


