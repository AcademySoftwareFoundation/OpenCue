
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

package com.imageworks.spcue.test.dispatcher;

import java.io.File;
import java.util.List;
import javax.annotation.Resource;
import java.util.LinkedHashSet;

import org.junit.Before;
import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.DispatchJob;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.ServiceOverrideEntity;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.DispatchSupport;
import com.imageworks.spcue.dispatcher.FrameCompleteHandler;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.report.FrameCompleteReport;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.grpc.report.RunningFrameInfo;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.ServiceManager;
import com.imageworks.spcue.test.TransactionalTest;
import com.imageworks.spcue.util.CueUtil;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

@ContextConfiguration
public class FrameCompleteHandlerTests extends TransactionalTest {

    @Resource
    AdminManager adminManager;

    @Resource
    FrameCompleteHandler frameCompleteHandler;

    @Resource
    HostManager hostManager;

    @Resource
    JobLauncher jobLauncher;

    @Resource
    JobManager jobManager;

    @Resource
    FrameDao frameDao;

    @Resource
    LayerDao layerDao;

    @Resource
    Dispatcher dispatcher;

    @Resource
    DispatchSupport dispatchSupport;

    @Resource
    ServiceManager serviceManager;

    private static final String HOSTNAME = "beta";
    private static final String HOSTNAME2 = "zeta";

    @Before
    public void setTestMode() {

        dispatcher.setTestMode(true);
    }

    @Before
    public void launchJob() {
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_gpus_test.xml"));
    }

    @Before
    public void createHost() {
        RenderHost host = RenderHost.newBuilder().setName(HOSTNAME).setBootTime(1192369572)
                // The minimum amount of free space in the temporary directory to book a host.
                .setFreeMcp(CueUtil.GB).setFreeMem((int) CueUtil.GB8).setFreeSwap(20760).setLoad(0)
                .setTotalMcp(CueUtil.GB4).setTotalMem(CueUtil.GB8).setTotalSwap(CueUtil.GB2)
                .setNimbyEnabled(false).setNumProcs(40).setCoresPerProc(100)
                .setState(HardwareState.UP).setFacility("spi").putAttributes("SP_OS", "Linux")
                .setNumGpus(8).setFreeGpuMem(CueUtil.GB16 * 8).setTotalGpuMem(CueUtil.GB16 * 8)
                .build();

        hostManager.createHost(host, adminManager.findAllocationDetail("spi", "general"));

        RenderHost host2 = RenderHost.newBuilder().setName(HOSTNAME2).setBootTime(1192369572)
                // The minimum amount of free space in the temporary directory to book a host.
                .setFreeMcp(CueUtil.GB).setFreeMem((int) CueUtil.GB4).setFreeSwap((int) CueUtil.GB4)
                .setLoad(0).setTotalMcp(CueUtil.GB4).setTotalMem((int) CueUtil.GB8)
                .setTotalSwap((int) CueUtil.GB8).setNimbyEnabled(false).setNumProcs(8)
                .setCoresPerProc(100).setState(HardwareState.UP).setFacility("spi")
                .putAttributes("SP_OS", "Linux").build();

        hostManager.createHost(host2, adminManager.findAllocationDetail("spi", "general"));
    }

    public DispatchHost getHost(String hostname) {
        return hostManager.findDispatchHost(hostname);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGpuReport() {
        JobDetail job = jobManager.findJobDetail("pipe-default-testuser_test0");
        LayerDetail layer = layerDao.findLayerDetail(job, "layer0");
        jobManager.setJobPaused(job, false);

        DispatchHost host = getHost(HOSTNAME);
        List<VirtualProc> procs = dispatcher.dispatchHost(host);
        assertEquals(1, procs.size());
        VirtualProc proc = procs.get(0);

        assertEquals(7, host.idleGpus);
        assertEquals(CueUtil.GB16 * 8 - CueUtil.GB, host.idleGpuMemory);

        RunningFrameInfo info = RunningFrameInfo.newBuilder().setJobId(proc.getJobId())
                .setLayerId(proc.getLayerId()).setFrameId(proc.getFrameId())
                .setResourceId(proc.getProcId()).build();
        FrameCompleteReport report =
                FrameCompleteReport.newBuilder().setFrame(info).setExitStatus(0).build();
        frameCompleteHandler.handleFrameCompleteReport(report);

        assertTrue(jobManager.isLayerComplete(layer));
        assertTrue(jobManager.isJobComplete(job));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGpuReportMultiple() {
        JobDetail job0 = jobManager.findJobDetail("pipe-default-testuser_test0");
        LayerDetail layer0_0 = layerDao.findLayerDetail(job0, "layer0");
        jobManager.setJobPaused(job0, false);

        JobDetail job1 = jobManager.findJobDetail("pipe-default-testuser_test1");
        LayerDetail layer1_0 = layerDao.findLayerDetail(job1, "layer0");
        jobManager.setJobPaused(job1, false);

        DispatchHost host = getHost(HOSTNAME);
        List<VirtualProc> procs = dispatcher.dispatchHost(host);
        assertEquals(2, procs.size());

        assertEquals(4, host.idleGpus);
        assertEquals(CueUtil.GB16 * 8 - CueUtil.GB2, host.idleGpuMemory);

        for (VirtualProc proc : procs) {
            RunningFrameInfo info = RunningFrameInfo.newBuilder().setJobId(proc.getJobId())
                    .setLayerId(proc.getLayerId()).setFrameId(proc.getFrameId())
                    .setResourceId(proc.getProcId()).build();
            FrameCompleteReport report =
                    FrameCompleteReport.newBuilder().setFrame(info).setExitStatus(0).build();
            frameCompleteHandler.handleFrameCompleteReport(report);
        }

        assertTrue(jobManager.isLayerComplete(layer0_0));
        assertTrue(jobManager.isJobComplete(job0));
        assertTrue(jobManager.isLayerComplete(layer1_0));
        assertTrue(jobManager.isJobComplete(job1));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGpuReportOver() {
        JobDetail job1 = jobManager.findJobDetail("pipe-default-testuser_test1");
        LayerDetail layer1_0 = layerDao.findLayerDetail(job1, "layer0");
        jobManager.setJobPaused(job1, false);

        JobDetail job2 = jobManager.findJobDetail("pipe-default-testuser_test2");
        LayerDetail layer2_0 = layerDao.findLayerDetail(job2, "layer0");
        jobManager.setJobPaused(job2, false);

        DispatchHost host = getHost(HOSTNAME);
        List<VirtualProc> procs = dispatcher.dispatchHost(host);
        assertEquals(1, procs.size());

        assertTrue(host.idleGpus == 5 || host.idleGpus == 2);
        assertEquals(CueUtil.GB16 * 8 - CueUtil.GB, host.idleGpuMemory);

        for (VirtualProc proc : procs) {
            RunningFrameInfo info = RunningFrameInfo.newBuilder().setJobId(proc.getJobId())
                    .setLayerId(proc.getLayerId()).setFrameId(proc.getFrameId())
                    .setResourceId(proc.getProcId()).build();
            FrameCompleteReport report =
                    FrameCompleteReport.newBuilder().setFrame(info).setExitStatus(0).build();
            frameCompleteHandler.handleFrameCompleteReport(report);
        }

        assertEquals(1, (jobManager.isLayerComplete(layer1_0) ? 1 : 0)
                + (jobManager.isLayerComplete(layer2_0) ? 1 : 0));
        assertEquals(1, (jobManager.isJobComplete(job1) ? 1 : 0)
                + (jobManager.isJobComplete(job2) ? 1 : 0));
    }

    private void executeDepend(FrameState frameState, int exitStatus, int dependCount,
            FrameState dependState) {
        JobDetail job = jobManager.findJobDetail("pipe-default-testuser_test_depend");
        LayerDetail layerFirst = layerDao.findLayerDetail(job, "layer_first");
        LayerDetail layerSecond = layerDao.findLayerDetail(job, "layer_second");
        FrameDetail frameFirst = frameDao.findFrameDetail(job, "0000-layer_first");
        FrameDetail frameSecond = frameDao.findFrameDetail(job, "0000-layer_second");

        assertEquals(1, frameSecond.dependCount);
        assertEquals(FrameState.DEPEND, frameSecond.state);

        jobManager.setJobPaused(job, false);

        DispatchHost host = getHost(HOSTNAME);
        List<VirtualProc> procs = dispatcher.dispatchHost(host);
        assertEquals(1, procs.size());
        VirtualProc proc = procs.get(0);
        assertEquals(job.getId(), proc.getJobId());
        assertEquals(layerFirst.getId(), proc.getLayerId());
        assertEquals(frameFirst.getId(), proc.getFrameId());

        RunningFrameInfo info = RunningFrameInfo.newBuilder().setJobId(proc.getJobId())
                .setLayerId(proc.getLayerId()).setFrameId(proc.getFrameId())
                .setResourceId(proc.getProcId()).build();
        FrameCompleteReport report =
                FrameCompleteReport.newBuilder().setFrame(info).setExitStatus(exitStatus).build();

        DispatchJob dispatchJob = jobManager.getDispatchJob(proc.getJobId());
        DispatchFrame dispatchFrame = jobManager.getDispatchFrame(report.getFrame().getFrameId());
        FrameDetail frameDetail = jobManager.getFrameDetail(report.getFrame().getFrameId());
        dispatchSupport.stopFrame(dispatchFrame, frameState, report.getExitStatus(),
                report.getFrame().getMaxRss());
        frameCompleteHandler.handlePostFrameCompleteOperations(proc, report, dispatchJob,
                dispatchFrame, frameState, frameDetail);

        assertTrue(jobManager.isLayerComplete(layerFirst));
        assertFalse(jobManager.isLayerComplete(layerSecond));

        frameSecond = frameDao.findFrameDetail(job, "0000-layer_second");
        assertEquals(dependCount, frameSecond.dependCount);
        assertEquals(dependState, frameSecond.state);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDependOnSuccess() {
        assertTrue(frameCompleteHandler.getSatisfyDependOnlyOnFrameSuccess());
        executeDepend(FrameState.SUCCEEDED, 0, 0, FrameState.WAITING);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDependOnFailure() {
        assertTrue(frameCompleteHandler.getSatisfyDependOnlyOnFrameSuccess());
        executeDepend(FrameState.EATEN, -1, 1, FrameState.DEPEND);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDependOnSuccessSatifyOnAny() {
        frameCompleteHandler.setSatisfyDependOnlyOnFrameSuccess(false);
        assertFalse(frameCompleteHandler.getSatisfyDependOnlyOnFrameSuccess());
        executeDepend(FrameState.SUCCEEDED, 0, 0, FrameState.WAITING);
        frameCompleteHandler.setSatisfyDependOnlyOnFrameSuccess(true);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDependOnFailureSatisfyOnAny() {
        frameCompleteHandler.setSatisfyDependOnlyOnFrameSuccess(false);
        assertFalse(frameCompleteHandler.getSatisfyDependOnlyOnFrameSuccess());
        executeDepend(FrameState.EATEN, -1, 0, FrameState.WAITING);
        frameCompleteHandler.setSatisfyDependOnlyOnFrameSuccess(true);
    }

    private void executeMinMemIncrease(int expected, boolean override) {
        if (override) {
            ServiceOverrideEntity soe = new ServiceOverrideEntity();
            soe.showId = "00000000-0000-0000-0000-000000000000";
            soe.name = "apitest";
            soe.threadable = false;
            soe.minCores = 10;
            soe.minMemory = (int) CueUtil.GB2;
            soe.tags = new LinkedHashSet<>();
            soe.tags.add("general");
            soe.minMemoryIncrease = (int) CueUtil.GB8;

            serviceManager.createService(soe);
        }

        String jobName = "pipe-default-testuser_min_mem_test";
        JobDetail job = jobManager.findJobDetail(jobName);
        LayerDetail layer = layerDao.findLayerDetail(job, "test_layer");
        FrameDetail frame = frameDao.findFrameDetail(job, "0000-test_layer");
        jobManager.setJobPaused(job, false);

        DispatchHost host = getHost(HOSTNAME2);
        List<VirtualProc> procs = dispatcher.dispatchHost(host);
        assertEquals(1, procs.size());
        VirtualProc proc = procs.get(0);
        assertEquals(job.getId(), proc.getJobId());
        assertEquals(layer.getId(), proc.getLayerId());
        assertEquals(frame.getId(), proc.getFrameId());

        RunningFrameInfo info = RunningFrameInfo.newBuilder().setJobId(proc.getJobId())
                .setLayerId(proc.getLayerId()).setFrameId(proc.getFrameId())
                .setResourceId(proc.getProcId()).build();
        FrameCompleteReport report = FrameCompleteReport.newBuilder().setFrame(info)
                .setExitStatus(Dispatcher.EXIT_STATUS_MEMORY_FAILURE).build();

        DispatchJob dispatchJob = jobManager.getDispatchJob(proc.getJobId());
        DispatchFrame dispatchFrame = jobManager.getDispatchFrame(report.getFrame().getFrameId());
        FrameDetail frameDetail = jobManager.getFrameDetail(report.getFrame().getFrameId());
        dispatchSupport.stopFrame(dispatchFrame, FrameState.DEAD, report.getExitStatus(),
                report.getFrame().getMaxRss());
        frameCompleteHandler.handlePostFrameCompleteOperations(proc, report, dispatchJob,
                dispatchFrame, FrameState.WAITING, frameDetail);

        assertFalse(jobManager.isLayerComplete(layer));

        JobDetail ujob = jobManager.findJobDetail(jobName);
        LayerDetail ulayer = layerDao.findLayerDetail(ujob, "test_layer");
        assertEquals(expected, ulayer.getMinimumMemory());
    }

    private void executeMinMemIncreaseDocker(int expected, boolean override) {
        if (override) {
            ServiceOverrideEntity soe = new ServiceOverrideEntity();
            soe.showId = "00000000-0000-0000-0000-000000000000";
            soe.name = "apitest";
            soe.threadable = false;
            soe.minCores = 10;
            soe.minMemory = (int) CueUtil.GB2;
            soe.tags = new LinkedHashSet<>();
            soe.tags.add("general");
            soe.minMemoryIncrease = (int) CueUtil.GB8;

            serviceManager.createService(soe);
        }

        String jobName = "pipe-default-testuser_min_mem_test";
        JobDetail job = jobManager.findJobDetail(jobName);
        LayerDetail layer = layerDao.findLayerDetail(job, "test_layer");
        FrameDetail frame = frameDao.findFrameDetail(job, "0000-test_layer");
        jobManager.setJobPaused(job, false);

        DispatchHost host = getHost(HOSTNAME2);
        List<VirtualProc> procs = dispatcher.dispatchHost(host);
        assertEquals(1, procs.size());
        VirtualProc proc = procs.get(0);
        assertEquals(job.getId(), proc.getJobId());
        assertEquals(layer.getId(), proc.getLayerId());
        assertEquals(frame.getId(), proc.getFrameId());

        RunningFrameInfo info = RunningFrameInfo.newBuilder().setJobId(proc.getJobId())
                .setLayerId(proc.getLayerId()).setFrameId(proc.getFrameId())
                .setResourceId(proc.getProcId()).build();
        FrameCompleteReport report = FrameCompleteReport.newBuilder().setFrame(info)
                .setExitStatus(Dispatcher.DOCKER_EXIT_STATUS_MEMORY_FAILURE).build();

        DispatchJob dispatchJob = jobManager.getDispatchJob(proc.getJobId());
        DispatchFrame dispatchFrame = jobManager.getDispatchFrame(report.getFrame().getFrameId());
        FrameDetail frameDetail = jobManager.getFrameDetail(report.getFrame().getFrameId());
        dispatchSupport.stopFrame(dispatchFrame, FrameState.DEAD, report.getExitStatus(),
                report.getFrame().getMaxRss());
        frameCompleteHandler.handlePostFrameCompleteOperations(proc, report, dispatchJob,
                dispatchFrame, FrameState.WAITING, frameDetail);

        assertFalse(jobManager.isLayerComplete(layer));

        JobDetail ujob = jobManager.findJobDetail(jobName);
        LayerDetail ulayer = layerDao.findLayerDetail(ujob, "test_layer");
        assertEquals(expected, ulayer.getMinimumMemory());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testMinMemIncrease() {
        executeMinMemIncrease(6291456, false);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testMinMemIncreaseShowOverride() {
        executeMinMemIncrease(10485760, true);
    }
}
