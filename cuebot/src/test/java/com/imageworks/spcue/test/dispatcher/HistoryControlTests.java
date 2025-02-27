
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
public class HistoryControlTests extends TransactionalTest {

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
    private static final String DELETE_HISTORY =
            "DELETE FROM frame_history; " + "DELETE FROM job_history; ";
    private static final String DISABLE_HISTORY = "INSERT INTO " + "config (pk_config,str_key) "
            + "VALUES " + "(uuid_generate_v1(),'DISABLE_HISTORY');";

    @Before
    public void setTestMode() {
        dispatcher.setTestMode(true);
    }

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
    }

    public DispatchHost getHost() {
        return hostManager.findDispatchHost(HOSTNAME);
    }

    public void launchAndDeleteJob() {
        launchJob();

        JobDetail job = jobManager.findJobDetail("pipe-default-testuser_test0");
        LayerDetail layer = layerDao.findLayerDetail(job, "layer0");
        jobManager.setJobPaused(job, false);

        DispatchHost host = getHost();
        List<VirtualProc> procs = dispatcher.dispatchHost(host);
        VirtualProc proc = procs.get(0);

        RunningFrameInfo info = RunningFrameInfo.newBuilder().setJobId(proc.getJobId())
                .setLayerId(proc.getLayerId()).setFrameId(proc.getFrameId())
                .setResourceId(proc.getProcId()).build();
        FrameCompleteReport report =
                FrameCompleteReport.newBuilder().setFrame(info).setExitStatus(0).build();
        frameCompleteHandler.handleFrameCompleteReport(report);

        assertTrue(jobManager.isLayerComplete(layer));
        assertTrue(jobManager.isJobComplete(job));

        jdbcTemplate.update("DELETE FROM job WHERE pk_job=?", job.getId());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testEnabled() {
        jdbcTemplate.update(DELETE_HISTORY);
        assertEquals(Integer.valueOf(0),
                jdbcTemplate.queryForObject("SELECT COUNT(*) FROM job_history", Integer.class));
        assertEquals(Integer.valueOf(0),
                jdbcTemplate.queryForObject("SELECT COUNT(*) FROM frame_history", Integer.class));

        launchAndDeleteJob();

        assertEquals(Integer.valueOf(5),
                jdbcTemplate.queryForObject("SELECT COUNT(*) FROM job_history", Integer.class));
        assertEquals(Integer.valueOf(1),
                jdbcTemplate.queryForObject("SELECT COUNT(*) FROM frame_history", Integer.class));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDisabled() {
        jdbcTemplate.update(DELETE_HISTORY);
        jdbcTemplate.update(DISABLE_HISTORY);

        assertEquals(Integer.valueOf(0),
                jdbcTemplate.queryForObject("SELECT COUNT(*) FROM job_history", Integer.class));
        assertEquals(Integer.valueOf(0),
                jdbcTemplate.queryForObject("SELECT COUNT(*) FROM frame_history", Integer.class));

        launchAndDeleteJob();

        assertEquals(Integer.valueOf(0),
                jdbcTemplate.queryForObject("SELECT COUNT(*) FROM job_history", Integer.class));
        assertEquals(Integer.valueOf(0),
                jdbcTemplate.queryForObject("SELECT COUNT(*) FROM frame_history", Integer.class));
    }
}
