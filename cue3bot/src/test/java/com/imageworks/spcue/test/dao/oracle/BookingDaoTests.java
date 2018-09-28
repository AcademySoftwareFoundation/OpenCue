
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



package com.imageworks.spcue.test.dao.oracle;

import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import static org.junit.Assert.*;

import java.io.File;
import java.util.ArrayList;
import java.util.HashMap;

import javax.annotation.Resource;

import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.support.AnnotationConfigContextLoader;

import org.springframework.test.context.transaction.TransactionConfiguration;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.Frame;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.Layer;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.CueClientIce.RenderPartition;
import com.imageworks.spcue.CueGrpc.HardwareState;
import com.imageworks.spcue.CueIce.RenderPartitionType;
import com.imageworks.spcue.CueGrpc.RenderHost;
import com.imageworks.spcue.dao.BookingDao;
import com.imageworks.spcue.dao.DispatcherDao;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dao.ProcDao;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.Whiteboard;
import com.imageworks.spcue.util.CueUtil;


@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
@TransactionConfiguration(transactionManager="transactionManager")
public class BookingDaoTests  extends AbstractTransactionalJUnit4SpringContextTests {

    @Resource
    HostManager hostManager;

    @Resource
    AdminManager adminManager;

    @Resource
    JobLauncher jobLauncher;

    @Resource
    JobManager jobManager;

    @Resource
    HostDao hostDao;

    @Resource
    BookingDao bookingDao;

    @Resource
    DispatcherDao dispatcherDao;

    @Resource
    ProcDao procDao;

    @Resource
    Whiteboard whiteboard;

    public DispatchHost createHost() {
        RenderHost host = RenderHost.newBuilder()
                .setName("test_host")
                .setBootTime(1192369572)
                .setFreeMcp(76020)
                .setFreeMem(53500)
                .setFreeSwap(20760)
                .setLoad(1)
                .setTotalMcp(195430)
                .setTotalMem((int) CueUtil.GB16)
                .setTotalSwap((int) CueUtil.GB16)
                .setNimbyEnabled(false)
                .setNumProcs(2)
                .setCoresPerProc(100)
                .setState(HardwareState.Up)
                .setFacility("spi")
                .addTags("general")
                .putAttributes("freeGpu", String.format("%d", CueUtil.MB512))
                .putAttributes("totalGpu", String.format("%d", CueUtil.MB512))
                .build();
        DispatchHost dh = hostManager.createHost(host);
        hostManager.setAllocation(dh,
                adminManager.findAllocationDetail("spi", "general"));

        return dh;
    }

    public JobDetail launchJob() {
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        JobDetail d = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
        jobManager.setJobPaused(d, false);
        return d;
    }

    @Test
    @Transactional
    @Rollback(true)
    public void insertLocalJobAssignment() {

        DispatchHost h = createHost();
        JobDetail j = launchJob();

        LocalHostAssignment lja = new LocalHostAssignment();
        lja.setMaxCoreUnits(200);
        lja.setMaxMemory(CueUtil.GB4);
        lja.setMaxGpu(1);
        lja.setThreads(2);

        bookingDao.insertLocalHostAssignment(h, j, lja);


        assertEquals(Integer.valueOf(2), jdbcTemplate.queryForObject(
                "SELECT int_threads FROM host_local WHERE pk_job=?",
                Integer.class, j.getJobId()));

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT int_gpu_max FROM host_local WHERE pk_job=?",
                Integer.class, j.getJobId()));

        assertEquals(Integer.valueOf(200), jdbcTemplate.queryForObject(
                "SELECT int_cores_max FROM host_local WHERE pk_job=?",
                Integer.class, j.getJobId()));

        assertEquals(Long.valueOf(CueUtil.GB4), jdbcTemplate.queryForObject(
                "SELECT int_mem_max FROM host_local WHERE pk_job=?",
                Long.class, j.getJobId()));

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT int_gpu_max FROM host_local WHERE pk_job=?",
                Integer.class, j.getJobId()));

        assertEquals(Integer.valueOf(200), jdbcTemplate.queryForObject(
                "SELECT int_cores_idle FROM host_local WHERE pk_job=?",
                Integer.class, j.getJobId()));

        assertEquals(Long.valueOf(CueUtil.GB4), jdbcTemplate.queryForObject(
                "SELECT int_mem_idle FROM host_local WHERE pk_job=?",
                Long.class, j.getJobId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void insertLocalLayerAssignment() {

        DispatchHost h = createHost();
        JobDetail j = launchJob();
        Layer layer = jobManager.getLayers(j).get(0);

        LocalHostAssignment lja = new LocalHostAssignment();
        lja.setMaxCoreUnits(200);
        lja.setMaxMemory(CueUtil.GB4);
        lja.setMaxGpu(1);
        lja.setThreads(2);

        bookingDao.insertLocalHostAssignment(h, layer, lja);

        assertEquals(layer.getLayerId(), jdbcTemplate.queryForObject(
                "SELECT pk_layer FROM host_local WHERE pk_host_local=?",
                String.class, lja.getId()));

        assertEquals(RenderPartitionType.LayerPartition.toString(),
                jdbcTemplate.queryForObject(
                "SELECT str_type FROM host_local WHERE pk_host_local=?",
                String.class, lja.getId()));

        assertEquals(Integer.valueOf(2), jdbcTemplate.queryForObject(
                "SELECT int_threads FROM host_local WHERE pk_job=?",
                Integer.class, j.getJobId()));

        assertEquals(Integer.valueOf(200), jdbcTemplate.queryForObject(
                "SELECT int_cores_max FROM host_local WHERE pk_job=?",
                Integer.class, j.getJobId()));

        assertEquals(Long.valueOf(CueUtil.GB4), jdbcTemplate.queryForObject(
                "SELECT int_mem_max FROM host_local WHERE pk_job=?",
                Long.class, j.getJobId()));

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT int_gpu_max FROM host_local WHERE pk_job=?",
                Integer.class, j.getJobId()));

        assertEquals(Integer.valueOf(200), jdbcTemplate.queryForObject(
                "SELECT int_cores_idle FROM host_local WHERE pk_job=?",
                Integer.class, j.getJobId()));

        assertEquals(Long.valueOf(CueUtil.GB4), jdbcTemplate.queryForObject(
                "SELECT int_mem_idle FROM host_local WHERE pk_job=?",
                Long.class, j.getJobId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void insertLocalFrameAssignment() {

        DispatchHost h = createHost();
        JobDetail j = launchJob();
        Layer layer = jobManager.getLayers(j).get(0);
        Frame frame = jobManager.findFrame(layer, 1);

        LocalHostAssignment lja = new LocalHostAssignment();
        lja.setMaxCoreUnits(200);
        lja.setMaxMemory(CueUtil.GB4);
        lja.setMaxGpu(1);
        lja.setThreads(2);

        bookingDao.insertLocalHostAssignment(h, frame, lja);

        assertEquals(frame.getFrameId(), jdbcTemplate.queryForObject(
                "SELECT pk_frame FROM host_local WHERE pk_host_local=?",
                String.class, lja.getId()));

        assertEquals(RenderPartitionType.FramePartition.toString(),
                jdbcTemplate.queryForObject(
                "SELECT str_type FROM host_local WHERE pk_host_local=?",
                String.class, lja.getId()));

        assertEquals(Integer.valueOf(2), jdbcTemplate.queryForObject(
                "SELECT int_threads FROM host_local WHERE pk_job=?",
                Integer.class, j.getJobId()));

        assertEquals(Integer.valueOf(200), jdbcTemplate.queryForObject(
                "SELECT int_cores_max FROM host_local WHERE pk_job=?",
                Integer.class, j.getJobId()));

        assertEquals(Long.valueOf(CueUtil.GB4), jdbcTemplate.queryForObject(
                "SELECT int_mem_max FROM host_local WHERE pk_job=?",
                Long.class, j.getJobId()));

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT int_gpu_max FROM host_local WHERE pk_job=?",
                Integer.class, j.getJobId()));

        assertEquals(Integer.valueOf(200), jdbcTemplate.queryForObject(
                "SELECT int_cores_idle FROM host_local WHERE pk_job=?",
                Integer.class, j.getJobId()));

        assertEquals(Long.valueOf(CueUtil.GB4), jdbcTemplate.queryForObject(
                "SELECT int_mem_idle FROM host_local WHERE pk_job=?",
                Long.class, j.getJobId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetLocalJobAssignment() {

        DispatchHost h = createHost();
        JobDetail j = launchJob();

        LocalHostAssignment lja = new LocalHostAssignment();
        lja.setMaxCoreUnits(200);
        lja.setMaxMemory(CueUtil.GB4);
        lja.setThreads(2);
        lja.setMaxGpu(1);

        bookingDao.insertLocalHostAssignment(h, j, lja);

        LocalHostAssignment lja2 = bookingDao.getLocalJobAssignment(h.getHostId(),
                                                                    j.getJobId());

        assertEquals(lja.getMaxCoreUnits(), lja2.getMaxCoreUnits());
        assertEquals(lja.getMaxMemory(), lja2.getMaxMemory());
        assertEquals(lja.getMaxGpu(), lja2.getMaxGpu());
        assertEquals(lja.getThreads(), lja2.getThreads());

    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetRenderPartition() {

        DispatchHost h = createHost();
        JobDetail j = launchJob();

        LocalHostAssignment lja = new LocalHostAssignment();
        lja.setMaxCoreUnits(200);
        lja.setMaxMemory(CueUtil.GB4);
        lja.setThreads(2);
        lja.setMaxGpu(1);

        bookingDao.insertLocalHostAssignment(h, j, lja);

        LocalHostAssignment lja2 = bookingDao.getLocalJobAssignment(h.getHostId(),
                                                                    j.getJobId());

        assertEquals(lja.getMaxCoreUnits(), lja2.getMaxCoreUnits());
        assertEquals(lja.getMaxMemory(), lja2.getMaxMemory());
        assertEquals(lja.getThreads(), lja2.getThreads());
        assertEquals(lja.getMaxGpu(), lja2.getMaxGpu());

        RenderPartition rp = whiteboard.getRenderPartition(lja2);

        assertEquals(lja2.getMaxCoreUnits(), rp.maxCores);
        assertEquals(lja2.getMaxMemory(), rp.maxMemory);
        assertEquals(lja2.getThreads(), rp.threads);
        logger.info("--------------------");
        logger.info(lja2.getMaxGpu());
        logger.info(rp.maxGpu);
        assertEquals(lja2.getMaxGpu(), rp.maxGpu);
        assertEquals(h.getName(), rp.host);
        assertEquals(j.getName(), rp.job);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetProcs() {

        DispatchHost h = createHost();
        JobDetail j = launchJob();

        LocalHostAssignment lja = new LocalHostAssignment();
        lja.setMaxCoreUnits(200);
        lja.setMaxMemory(CueUtil.GB4);
        lja.setThreads(2);
        lja.setMaxGpu(1);

        bookingDao.insertLocalHostAssignment(h, j, lja);

        assertEquals(0, procDao.findVirtualProcs(lja).size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void updateMaxCores() {

        DispatchHost h = createHost();
        JobDetail j = launchJob();

        LocalHostAssignment lja = new LocalHostAssignment();
        lja.setMaxCoreUnits(200);
        lja.setMaxMemory(CueUtil.GB4);
        lja.setThreads(2);
        lja.setMaxGpu(1);

        bookingDao.insertLocalHostAssignment(h, j, lja);
        assertTrue(bookingDao.updateMaxCores(lja, 100));
        assertEquals(Integer.valueOf(100), jdbcTemplate.queryForObject(
                "SELECT int_cores_max FROM host_local WHERE pk_host=?",
                Integer.class, h.getHostId()));

        LocalHostAssignment lj2 = bookingDao.getLocalJobAssignment(lja.id);

        assertEquals(100, lj2.getIdleCoreUnits());
        assertEquals(100, lj2.getMaxCoreUnits());

        bookingDao.updateMaxCores(lja, 200);

        lj2 = bookingDao.getLocalJobAssignment(lja.id);

        assertEquals(200, lj2.getIdleCoreUnits());
        assertEquals(200, lj2.getMaxCoreUnits());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void updateMaxMemory() {

        DispatchHost h = createHost();
        JobDetail j = launchJob();

        LocalHostAssignment lja = new LocalHostAssignment();
        lja.setMaxCoreUnits(200);
        lja.setMaxMemory(CueUtil.GB4);
        lja.setThreads(2);
        lja.setMaxGpu(1);

        bookingDao.insertLocalHostAssignment(h, j, lja);
        bookingDao.updateMaxMemory(lja, CueUtil.GB2);

        LocalHostAssignment lj2 = bookingDao.getLocalJobAssignment(lja.id);

        assertEquals(CueUtil.GB2, lj2.getIdleMemory());
        assertEquals(CueUtil.GB2, lj2.getMaxMemory());

        bookingDao.updateMaxMemory(lja, CueUtil.GB4);

        lj2 = bookingDao.getLocalJobAssignment(lja.id);

        assertEquals(CueUtil.GB4, lj2.getIdleMemory());
        assertEquals(CueUtil.GB4, lj2.getMaxMemory());
}

    @Test
    @Transactional
    @Rollback(true)
    public void updateMaxGpu() {

        DispatchHost h = createHost();
        JobDetail j = launchJob();

        LocalHostAssignment lja = new LocalHostAssignment();
        lja.setMaxCoreUnits(200);
        lja.setMaxMemory(CueUtil.GB4);
        lja.setThreads(2);
        lja.setMaxGpu(1);

        bookingDao.insertLocalHostAssignment(h, j, lja);
        bookingDao.updateMaxMemory(lja, CueUtil.GB2);

        LocalHostAssignment lj2 = bookingDao.getLocalJobAssignment(lja.id);

        assertEquals(CueUtil.GB2, lj2.getIdleMemory());
        assertEquals(CueUtil.GB2, lj2.getMaxMemory());
        assertEquals(1, lj2.getMaxGpu());

        bookingDao.updateMaxGpu(lja, 2);

        lj2 = bookingDao.getLocalJobAssignment(lja.id);

        assertEquals(CueUtil.GB2, lj2.getIdleMemory());
        assertEquals(CueUtil.GB2, lj2.getMaxMemory());
        assertEquals(2, lj2.getMaxGpu());
    }
}

