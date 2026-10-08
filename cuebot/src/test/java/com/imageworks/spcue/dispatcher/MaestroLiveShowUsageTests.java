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
import java.util.Collections;
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
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dao.ProcDao;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.util.CueUtil;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

/**
 * The show_cores and running_frames gauges are read from the proc table, so they count every live
 * proc of a Maestro show no matter who booked it, and only Maestro's shows.
 */
@Transactional
@ContextConfiguration(classes = TestAppConfig.class, loader = AnnotationConfigContextLoader.class)
public class MaestroLiveShowUsageTests extends AbstractTransactionalJUnit4SpringContextTests {

    @Resource
    JobLauncher jobLauncher;
    @Resource
    JobManager jobManager;
    @Resource
    HostManager hostManager;
    @Resource
    AdminManager adminManager;
    @Resource
    HostDao hostDao;
    @Resource
    FrameDao frameDao;
    @Resource
    ProcDao procDao;
    @Resource
    Maestro maestro;
    @Resource
    ConfigurableEnvironment springEnv;

    private static final String HOSTNAME = "beta";
    private static final String JOB = "pipe-dev.cue-testuser_shell_dispatch_test_v1";
    private static final String MODE_SOURCE = "liveShowUsageMode";

    private JobDetail job;
    private DispatchHost host;

    @Before
    public void setUp() {
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_dispatch_test.xml"));
        job = jobManager.findJobDetail(JOB);

        RenderHost rh = RenderHost.newBuilder().setName(HOSTNAME).setBootTime(1192369572)
                .setFreeMcp(CueUtil.GB).setFreeMem(53500).setFreeSwap(20760).setLoad(1)
                .setTotalMcp(CueUtil.GB4).setTotalMem(8173264).setTotalSwap(20960)
                .setNimbyEnabled(false).setNumProcs(2).setCoresPerProc(100).addTags("test")
                .setState(HardwareState.UP).setFacility("spi").putAttributes("SP_OS", "Linux")
                .build();
        hostManager.createHost(rh, adminManager.findAllocationDetail("spi", "general"));
        host = hostDao.findDispatchHost(HOSTNAME);
    }

    @After
    public void restoreMode() {
        springEnv.getPropertySources().remove(MODE_SOURCE);
    }

    private void setMode(String mode) {
        springEnv.getPropertySources().remove(MODE_SOURCE);
        springEnv.getPropertySources().addFirst(new MapPropertySource(MODE_SOURCE,
                Collections.singletonMap("maestro.enabled", mode)));
    }

    private void insertProc(String frameName, int coresReserved) {
        FrameDetail frame = frameDao.findFrameDetail(job, frameName);
        VirtualProc proc = new VirtualProc();
        proc.allocationId = host.getAllocationId();
        proc.coresReserved = coresReserved;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;
        procDao.insertVirtualProc(proc);
    }

    private MaestroMetrics.TickStats read() {
        MaestroMetrics.TickStats stats = new MaestroMetrics.TickStats();
        maestro.readLiveShowUsage(stats);
        return stats;
    }

    @Test
    public void facilityModeCountsEveryProc() {
        setMode("facility");
        insertProc("0001-pass_1", 100);
        insertProc("0002-pass_1", 100);

        MaestroMetrics.TickStats stats = read();

        assertEquals(2.0, stats.coresByShow.get("pipe"), 1e-9);
        assertEquals(2, stats.runningFrames);
    }

    @Test
    public void managedModeSkipsUnmanagedShows() {
        setMode("managed");
        jdbcTemplate.update("UPDATE show SET b_scheduler_managed = false WHERE pk_show = ?",
                job.getShowId());
        insertProc("0001-pass_1", 100);

        MaestroMetrics.TickStats stats = read();

        assertTrue(stats.coresByShow.isEmpty());
        assertEquals(0, stats.runningFrames);
    }

    @Test
    public void managedModeCountsManagedShows() {
        setMode("managed");
        jdbcTemplate.update("UPDATE show SET b_scheduler_managed = true WHERE pk_show = ?",
                job.getShowId());
        insertProc("0001-pass_1", 100);

        MaestroMetrics.TickStats stats = read();

        assertEquals(1.0, stats.coresByShow.get("pipe"), 1e-9);
        assertEquals(1, stats.runningFrames);
    }
}
