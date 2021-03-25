
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

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.criteria.FrameSearchFactory;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.depend.LayerOnLayer;
import com.imageworks.spcue.dispatcher.DispatchSupport;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.DependManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.test.TransactionalTest;
import com.imageworks.spcue.util.CueUtil;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

@ContextConfiguration
public class CoreUnitDispatcherGpusJobTests extends TransactionalTest {

    @Resource
    JobManager jobManager;

    @Resource
    JobLauncher jobLauncher;

    @Resource
    HostManager hostManager;

    @Resource
    AdminManager adminManager;

    @Resource
    Dispatcher dispatcher;

    @Resource
    DispatchSupport dispatchSupport;

    @Resource
    LayerDao layerDao;

    @Resource
    FrameDao frameDao;

    @Resource
    FrameSearchFactory frameSearchFactory;

    @Resource
    DependManager dependManager;

    private static final String HOSTNAME = "beta";

    private static final String CPU_JOB = "pipe-default-testuser_test_cpu";

    private static final String GPU_JOB = "pipe-default-testuser_test_gpu";

    private static final String GPU_OVERBOOK_JOB = "pipe-default-testuser_test_gpu_overbook";

    @Before
    public void launchJob() {
        jobLauncher.testMode = true;
        jobLauncher.launch(
                new File("src/test/resources/conf/jobspec/jobspec_dispatch_gpus_test.xml"));
    }

    @Before
    public void setTestMode() {
        dispatcher.setTestMode(true);
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
                .addTags("test")
                .setState(HardwareState.UP)
                .setFacility("spi")
                .putAttributes("SP_OS", "Linux")
                .setNumGpus(8)
                .setFreeGpuMem(CueUtil.GB32)
                .setTotalGpuMem(CueUtil.GB32)
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
    public void testDispatchHost() {
        DispatchHost host = getHost();

        List<VirtualProc> procs = dispatcher.dispatchHost(host);
        // All jobs are paused. procs should be empty.
        assertTrue(procs.isEmpty());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDispatchCpuJob() {
        JobDetail job = jobManager.findJobDetail(CPU_JOB);
        jobManager.setJobPaused(job, false);

        DispatchHost host = getHost();
        List<VirtualProc> procs = dispatcher.dispatchHost(host, job);
        // Cuebot doesn't dispatch non-GPU job to GPU host. procs should be empty.
        assertTrue(procs.isEmpty());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDispatchGpuJob() {
        JobDetail job = jobManager.findJobDetail(GPU_JOB);
        jobManager.setJobPaused(job, false);

        DispatchHost host = getHost();
        List<VirtualProc> procs = dispatcher.dispatchHost(host, job);

        /*
         * The job contains 4 layers.
         * - test_gpus_0_layer gpus=0 gpu_memory=1
         * - test_gpu_memory_0_layer gpus=1 gpu_memory=0
         * - test_gpus_1_layer gpus=1 gpu_memory=1
         * - test_gpus_4_kayer gpus=4 gpu_memory=7g
         *
         * Cuebot doesn't dispatch test_gpu_memory_0_layer because gpu_memory is 0.
         * Also job_frame_dispatch_max is 2,
         * the procs should be test_gpus_0_layer and test_gpus_1_layer.
         */
        assertEquals(2, procs.size());

        VirtualProc proc0 = procs.get(0);
        LayerDetail layer0 = layerDao.findLayerDetail(job, "test_gpus_0_layer");
        assertEquals(layer0.id, proc0.layerId);
        assertEquals(100, proc0.coresReserved);
        assertEquals(3355443, proc0.memoryReserved);
        assertEquals(0, proc0.gpusReserved);
        assertEquals(1048576, proc0.gpuMemoryReserved);

        VirtualProc proc1 = procs.get(1);
        LayerDetail layer1 = layerDao.findLayerDetail(job, "test_gpus_1_layer");
        assertEquals(layer1.id, proc1.layerId);
        assertEquals(100, proc1.coresReserved);
        assertEquals(3355443, proc1.memoryReserved);
        assertEquals(1, proc1.gpusReserved);
        assertEquals(1048576, proc0.gpuMemoryReserved);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDispatchGpuJobWithDependency() {
        JobDetail job = jobManager.findJobDetail(GPU_JOB);
        LayerDetail dl0 = layerDao.findLayerDetail(job, "test_gpus_0_layer");
        LayerDetail dl1 = layerDao.findLayerDetail(job, "test_gpu_memory_0_layer");
        LayerOnLayer depend = new LayerOnLayer(dl0, dl1);
        dependManager.createDepend(depend);
        jobManager.setJobPaused(job, false);

        DispatchHost host = getHost();
        List<VirtualProc> procs = dispatcher.dispatchHost(host, job);

        /*
         * The job contains 4 layers.
         * - test_gpus_0_layer gpus=0 gpu_memory=1
         * - test_gpu_memory_0_layer gpus=1 gpu_memory=0
         * - test_gpus_1_layer gpus=1 gpu_memory=1
         * - test_gpus_4_kayer gpus=4 gpu_memory=7g
         *
         * Cuebot doesn't dispatch test_gpu_memory_0_layer because gpu_memory is 0.
         * And test_gpus_0_layer depends on test_gpu_memory_0_layer.
         * So the procs should be test_gpus_1_layer and test_gpus_4_layer.
         */
        assertEquals(2, procs.size());

        VirtualProc proc0 = procs.get(0);
        LayerDetail layer0 = layerDao.findLayerDetail(job, "test_gpus_1_layer");
        assertEquals(layer0.id, proc0.layerId);
        assertEquals(100, proc0.coresReserved);
        assertEquals(3355443, proc0.memoryReserved);
        assertEquals(1, proc0.gpusReserved);
        assertEquals(1048576, proc0.gpuMemoryReserved);

        VirtualProc proc1 = procs.get(1);
        LayerDetail layer1 = layerDao.findLayerDetail(job, "test_gpus_4_layer");
        assertEquals(layer1.id, proc1.layerId);
        assertEquals(100, proc1.coresReserved);
        assertEquals(3355443, proc1.memoryReserved);
        assertEquals(4, proc1.gpusReserved);
        assertEquals(7340032, proc1.gpuMemoryReserved);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDispatchGpuOverbookJob() {
        JobDetail job = jobManager.findJobDetail(GPU_OVERBOOK_JOB);
        jobManager.setJobPaused(job, false);

        DispatchHost host = getHost();
        List<VirtualProc> procs = dispatcher.dispatchHost(host, job);

        /*
         * The job contains 2 layers.
         * - test_gpus_6_layer gpus=6 gpu_memory=1
         * - test_gpus_3_layer gpus=3 gpu_memory=1
         * the procs should be only test_gpus_6_layer since host only has 8 GPUs.
         */
        assertEquals(1, procs.size());

        VirtualProc proc0 = procs.get(0);
        LayerDetail layer0 = layerDao.findLayerDetail(job, "test_gpus_6_layer");
        assertEquals(layer0.id, proc0.layerId);
        assertEquals(100, proc0.coresReserved);
        assertEquals(3355443, proc0.memoryReserved);
        assertEquals(6, proc0.gpusReserved);
        assertEquals(1048576, proc0.gpuMemoryReserved);
    }
}

