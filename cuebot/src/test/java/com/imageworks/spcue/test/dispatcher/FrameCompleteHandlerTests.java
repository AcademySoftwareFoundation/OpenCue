
/*
 * Copyright Contributors to the OpenCue Project
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

import java.io.File;
import java.util.List;
import javax.annotation.Resource;

import org.junit.Before;
import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.FrameCompleteHandler;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.report.FrameCompleteReport;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.grpc.report.RunningFrameInfo;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
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
    LayerDao layerDao;

    @Resource
    Dispatcher dispatcher;

    private static final String HOSTNAME = "beta";

    @Before
    public void setTestMode() {
        dispatcher.setTestMode(true);
    }

    @Before
    public void launchJob() {
        jobLauncher.testMode = true;
        jobLauncher.launch(
                new File("src/test/resources/conf/jobspec/jobspec_gpus_test.xml"));
    }

    @Before
    public void createHost() {
        RenderHost host = RenderHost.newBuilder()
                .setName(HOSTNAME)
                .setBootTime(1192369572)
                .setFreeMcp(76020)
                .setFreeMem((int) CueUtil.GB8)
                .setFreeSwap(20760)
                .setLoad(0)
                .setTotalMcp(195430)
                .setTotalMem(CueUtil.GB8)
                .setTotalSwap(CueUtil.GB2)
                .setNimbyEnabled(false)
                .setNumProcs(40)
                .setCoresPerProc(100)
                .setState(HardwareState.UP)
                .setFacility("spi")
                .putAttributes("SP_OS", "Linux")
                .setNumGpus(8)
                .setFreeGpuMem(CueUtil.GB16 * 8)
                .setTotalGpuMem(CueUtil.GB16 * 8)
                .build();

        hostManager.createHost(host,
                adminManager.findAllocationDetail("spi", "general"));
    }

    public DispatchHost getHost() {
        return hostManager.findDispatchHost(HOSTNAME);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGpuReport() {
        JobDetail job = jobManager.findJobDetail("pipe-default-testuser_test0");
        LayerDetail layer = layerDao.findLayerDetail(job, "layer0");
        jobManager.setJobPaused(job, false);

        DispatchHost host = getHost();
        List<VirtualProc> procs = dispatcher.dispatchHost(host);
        assertEquals(1, procs.size());
        VirtualProc proc = procs.get(0);

        assertEquals(7, host.idleGpus);
        assertEquals(CueUtil.GB16 * 8 - CueUtil.GB, host.idleGpuMemory);

        RunningFrameInfo info = RunningFrameInfo.newBuilder()
                .setJobId(proc.getJobId())
                .setLayerId(proc.getLayerId())
                .setFrameId(proc.getFrameId())
                .setResourceId(proc.getProcId())
                .build();
        FrameCompleteReport report = FrameCompleteReport.newBuilder()
                .setFrame(info)
                .setExitStatus(0)
                .build();
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

        DispatchHost host = getHost();
        List<VirtualProc> procs = dispatcher.dispatchHost(host);
        assertEquals(2, procs.size());

        assertEquals(4, host.idleGpus);
        assertEquals(CueUtil.GB16 * 8 - CueUtil.GB2, host.idleGpuMemory);

        for (VirtualProc proc : procs) {
            RunningFrameInfo info = RunningFrameInfo.newBuilder()
                    .setJobId(proc.getJobId())
                    .setLayerId(proc.getLayerId())
                    .setFrameId(proc.getFrameId())
                    .setResourceId(proc.getProcId())
                    .build();
            FrameCompleteReport report = FrameCompleteReport.newBuilder()
                    .setFrame(info)
                    .setExitStatus(0)
                    .build();
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

        DispatchHost host = getHost();
        List<VirtualProc> procs = dispatcher.dispatchHost(host);
        assertEquals(1, procs.size());

        assertTrue(host.idleGpus == 5 || host.idleGpus == 2);
        assertEquals(CueUtil.GB16 * 8 - CueUtil.GB, host.idleGpuMemory);

        for (VirtualProc proc : procs) {
            RunningFrameInfo info = RunningFrameInfo.newBuilder()
                    .setJobId(proc.getJobId())
                    .setLayerId(proc.getLayerId())
                    .setFrameId(proc.getFrameId())
                    .setResourceId(proc.getProcId())
                    .build();
            FrameCompleteReport report = FrameCompleteReport.newBuilder()
                    .setFrame(info)
                    .setExitStatus(0)
                    .build();
            frameCompleteHandler.handleFrameCompleteReport(report);
        }

        assertEquals(1,
                (jobManager.isLayerComplete(layer1_0) ? 1 : 0) +
                (jobManager.isLayerComplete(layer2_0) ? 1 : 0));
        assertEquals(1,
                (jobManager.isJobComplete(job1) ? 1 : 0) + 
                (jobManager.isJobComplete(job2) ? 1 : 0));
    }
}

