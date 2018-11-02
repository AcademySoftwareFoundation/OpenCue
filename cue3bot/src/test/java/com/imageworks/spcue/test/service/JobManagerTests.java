
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



package com.imageworks.spcue.test.service;

import java.io.File;
import java.util.List;
import java.util.Map;
import javax.annotation.Resource;

import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.test.context.transaction.AfterTransaction;
import org.springframework.test.context.transaction.BeforeTransaction;
import org.springframework.test.context.transaction.TransactionConfiguration;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.DispatcherDao;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dao.criteria.FrameSearch;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.job.FrameSearchCriteria;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.job.Order;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.JobManagerSupport;
import com.imageworks.spcue.service.JobSpec;
import com.imageworks.spcue.util.CueUtil;
import com.imageworks.spcue.util.FrameSet;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
@TransactionConfiguration(transactionManager="transactionManager")
public class JobManagerTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Resource
    JobManager jobManager;

    @Resource
    JobLauncher jobLauncher;

    @Resource
    JobManagerSupport jobManagerSupport;

    @Resource
    HostManager hostManager;

    @Resource
    AdminManager adminManager;

    @Resource
    LayerDao layerDao;

    @Resource
    HostDao hostDao;

    @Resource
    DispatcherDao dispatcherDao;

    @Resource
    FrameDao frameDao;

    private static final String JOB1 = "pipe-dev.cue-testuser_shell_dispatch_test_v1";
    private static final String JOB2 = "pipe-dev.cue-testuser_shell_dispatch_test_v2";
    private static final String JOB3 = "pipe-dev.cue-testuser_shell_v1";

    public JobDetail getJob1() {
        return jobManager.findJobDetail(JOB1);
    }

    public JobDetail getJob2() {
        return jobManager.findJobDetail(JOB2);
    }


    public JobDetail getJob3() {
        return jobManager.findJobDetail(JOB3);
    }

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
                .setState(HardwareState.UP)
                .setFacility("spi")
                .addTags("general")
                .build();

        DispatchHost dh = hostManager.createHost(host);
        hostManager.setAllocation(dh,
                adminManager.findAllocationDetail("spi", "general"));

        return dh;
    }


    @BeforeTransaction
    public void init() {
        jobLauncher.testMode = true;

        jdbcTemplate.update(
                "UPDATE job SET ts_stopped=systimestamp WHERE str_name IN  (?,?,?)", JOB1, JOB2, JOB3);

        jdbcTemplate.update(
            "DELETE FROM job WHERE str_name IN (?,?,?)", JOB1, JOB2, JOB3);

        JobSpec spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/jobspec_dispatch_test.xml"));
        jobLauncher.launch(spec);
        jdbcTemplate.update(
                "UPDATE job SET b_paused=1 WHERE str_name='pipe-dev.cue-testuser_shell_dispatch_test_v2' OR str_name='pipe-dev.cue-testuser_shell_dispatch_test_v1'");

        spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        jobLauncher.launch(spec);
        jdbcTemplate.update(
            "UPDATE job SET b_paused=1 WHERE str_name='pipe-dev.cue-testuser_shell_v1'");
    }

    @AfterTransaction
    public void destroy() {

        jdbcTemplate.update(
                "UPDATE job SET ts_stopped=systimestamp WHERE str_name IN  (?,?,?)", JOB1, JOB2, JOB3);

        jdbcTemplate.update(
                "DELETE FROM job WHERE str_name IN (?,?,?)", JOB1, JOB2, JOB3);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testLaunchAutoEatJob() {
        JobSpec spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/autoeat.xml"));
        jobLauncher.launch(spec);
        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT b_autoeat FROM job WHERE pk_job=?",
                Integer.class, spec.getJobs().get(0).detail.id));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testLaunchJob() {

        JobDetail job1 = getJob1();

        assertEquals(Long.valueOf(CueUtil.GB2), jdbcTemplate.queryForObject(
                "SELECT int_mem_min FROM layer WHERE pk_job=? AND str_name='pass_1'",
                Long.class, job1.id));
        assertEquals(Long.valueOf(100), jdbcTemplate.queryForObject(
                "SELECT int_cores_min FROM layer WHERE pk_job=? AND str_name='pass_1'",
                Long.class, job1.id));

        // check some job_stats values
        assertEquals(Integer.valueOf(20), jdbcTemplate.queryForObject(
                "SELECT int_frame_count FROM job WHERE " +
                "job.str_visible_name =?",
                Integer.class, "pipe-dev.cue-testuser_shell_dispatch_test_v1"));

        assertEquals(Integer.valueOf(10), jdbcTemplate.queryForObject(
                "SELECT int_waiting_count FROM job, job_stat WHERE " +
                "job.pk_job = job_stat.pk_job AND job.str_visible_name =?",
                Integer.class, "pipe-dev.cue-testuser_shell_dispatch_test_v2"));

        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT int_depend_count FROM job, job_stat WHERE " +
                "job.pk_job = job_stat.pk_job AND job.str_visible_name =?",
                Integer.class, "pipe-dev.cue-testuser_shell_dispatch_test_v1"));


        JobDetail job3 = getJob3();

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT int_waiting_count FROM job, job_stat WHERE " +
                "job.pk_job = job_stat.pk_job AND job.str_visible_name =?",
                Integer.class, job3.getName()));

        assertEquals(Integer.valueOf(10), jdbcTemplate.queryForObject(
                "SELECT int_depend_count FROM job, job_stat WHERE " +
                "job.pk_job = job_stat.pk_job AND job.str_visible_name =?",
                Integer.class, job3.getName()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testShutdownRelaunchJob() {
        JobDetail job1 = getJob1();
        JobDetail job2 = getJob2();
        logger.info("job detail: " + job2.getName());
        logger.info("job state " + job2.state.toString());

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM job WHERE pk_job=?",
                Integer.class, job1.id));

        jobManager.shutdownJob(job1);
        jobManager.shutdownJob(job2);

        assertEquals("FINISHED", jdbcTemplate.queryForObject(
                "SELECT str_state FROM job WHERE pk_job=?",String.class, job1.id));

        assertEquals(null, jdbcTemplate.queryForObject(
                "SELECT str_visible_name FROM job WHERE pk_job=?",String.class, job1.id));

        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_dispatch_test.xml"));

        getJob1();
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testShutdownJob() {
        JobDetail job = getJob1();
        logger.info("job detail: " + job.getName());
        logger.info("job state " + job.state.toString());

        assertEquals(Integer.valueOf(1),jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM job WHERE pk_job=?",
                Integer.class, job.id));

        jobManager.shutdownJob(getJob1());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testAutoNameJob() {
        JobSpec spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/jobspec_autoname.xml"));
        jobLauncher.launch(spec);

        assertEquals(spec.conformJobName("autoname") ,jdbcTemplate.queryForObject(
                "SELECT str_visible_name FROM job WHERE str_state='PENDING' AND str_name=?",String.class,
                spec.conformJobName("autoname")));
    }


    @Test
    @Transactional
    @Rollback(true)
    public void testShowAlias() {
        JobSpec spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/show_alias.xml"));
        jobLauncher.launch(spec);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testMisNamedJob() {
        JobSpec spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/jobspec_misnamed.xml"));
        assertEquals("pipe-dev.cue-testuser_pipe_dev.cue_testuser_blah_blah_v1",spec.getJobs().get(0).detail.name);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testMisNamedJob2() {
        JobSpec spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/jobspec_misnamed.xml"));

        assertEquals(spec.conformJobName("blah_____blah_v1"),
                                         "pipe-dev.cue-testuser_blah_blah_v1");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testPostFrameJobLaunch() {

        JobSpec spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/jobspec_postframes.xml"));
        jobLauncher.launch(spec);

        String pk_job = jdbcTemplate.queryForObject(
                "SELECT pk_job FROM job WHERE pk_job=? AND str_state='PENDING'",
                String.class, spec.getJobs().get(0).detail.id);

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM job_post WHERE pk_job=?",
                Integer.class, pk_job));

        String pk_post_job = jdbcTemplate.queryForObject(
                "SELECT pk_post_job FROM job_post WHERE pk_job=?",
                String.class, pk_job);

        assertEquals("PENDING", jdbcTemplate.queryForObject(
                "SELECT str_state FROM job WHERE pk_job=?",
                String.class, pk_job));

       assertTrue(jobManager.shutdownJob(jobManager.getJob(pk_job)));

       assertEquals("FINISHED", jdbcTemplate.queryForObject(
               "SELECT str_state FROM job WHERE pk_job=?",
               String.class, pk_job));

        assertEquals(pk_post_job, jdbcTemplate.queryForObject(
                "SELECT pk_job FROM job WHERE pk_job=?",
                String.class, pk_post_job));

        assertEquals("PENDING", jdbcTemplate.queryForObject(
                "SELECT str_state FROM job WHERE pk_job=?",
                String.class, pk_post_job));
    }


    @Test
    @Transactional
    @Rollback(true)
    public void testReorderLayerFirst() {

        JobDetail job = getJob1();
        LayerInterface layer = layerDao.findLayer(job, "pass_2");

        jobManager.reorderLayer(layer, new FrameSet("5-10"), Order.FIRST);

        assertEquals(Integer.valueOf(-6), jdbcTemplate.queryForObject(
                "SELECT int_dispatch_order FROM frame WHERE str_name=? AND pk_job=?",
                Integer.class, "0005-pass_2", job.id));
        assertEquals(Integer.valueOf(-5), jdbcTemplate.queryForObject(
                "SELECT int_dispatch_order FROM frame WHERE str_name=? AND pk_job=?",
                Integer.class, "0006-pass_2",job.id));
        assertEquals(Integer.valueOf(-4), jdbcTemplate.queryForObject(
                "SELECT int_dispatch_order FROM frame WHERE str_name=? AND pk_job=?",
                Integer.class, "0007-pass_2", job.id));
        assertEquals(Integer.valueOf(-3), jdbcTemplate.queryForObject(
                "SELECT int_dispatch_order FROM frame WHERE str_name=? AND pk_job=?",
                Integer.class, "0008-pass_2",job.id));
        assertEquals(Integer.valueOf(-2), jdbcTemplate.queryForObject(
                "SELECT int_dispatch_order FROM frame WHERE str_name=? AND pk_job=?",
                Integer.class, "0009-pass_2", job.id));
        assertEquals(Integer.valueOf(-1), jdbcTemplate.queryForObject(
                "SELECT int_dispatch_order FROM frame WHERE str_name=? AND pk_job=?",
                Integer.class, "0010-pass_2",job.id));
        assertEquals(Integer.valueOf(3), jdbcTemplate.queryForObject(
                "SELECT int_dispatch_order FROM frame WHERE str_name=? AND pk_job=?",
                Integer.class, "0004-pass_2", job.id));
        assertEquals(Integer.valueOf(2), jdbcTemplate.queryForObject(
                "SELECT int_dispatch_order FROM frame WHERE str_name=? AND pk_job=?",
                Integer.class, "0003-pass_2",job.id));
        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT int_dispatch_order FROM frame WHERE str_name=? AND pk_job=?",
                Integer.class, "0002-pass_2", job.id));
        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT int_dispatch_order FROM frame WHERE str_name=? AND pk_job=?",
                Integer.class, "0001-pass_2",job.id));

        DispatchHost host = createHost();
        jobManager.setJobPaused(job, false);

        String[] order = new String[] {
                "0005-pass_2","0006-pass_2","0007-pass_2","0008-pass_2",
                "0009-pass_2","0010-pass_2","0001-pass_1","0001-pass_2"
        };

        for (String f: order) {
            DispatchFrame frame =  dispatcherDao.findNextDispatchFrame(job, host);
            jdbcTemplate.update("UPDATE frame SET str_state=? WHERE pk_frame=?",
                    FrameState.SUCCEEDED.toString(),frame.getFrameId());
            assertEquals(f,frame.getName());
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testReorderLayerLast() {

        JobDetail job = getJob1();
        LayerInterface layer = layerDao.findLayer(job, "pass_1");

        jobManager.reorderLayer(layer, new FrameSet("1-5"), Order.LAST);

        assertEquals(Integer.valueOf(11), jdbcTemplate.queryForObject(
                "SELECT int_dispatch_order FROM frame WHERE str_name=? AND pk_job=?",
                Integer.class, "0001-pass_1", job.id));
        assertEquals(Integer.valueOf(12), jdbcTemplate.queryForObject(
                "SELECT int_dispatch_order FROM frame WHERE str_name=? AND pk_job=?",
                Integer.class, "0002-pass_1",job.id));
        assertEquals(Integer.valueOf(13), jdbcTemplate.queryForObject(
                "SELECT int_dispatch_order FROM frame WHERE str_name=? AND pk_job=?",
                Integer.class, "0003-pass_1", job.id));
        assertEquals(Integer.valueOf(14), jdbcTemplate.queryForObject(
                "SELECT int_dispatch_order FROM frame WHERE str_name=? AND pk_job=?",
                Integer.class, "0004-pass_1",job.id));
        assertEquals(Integer.valueOf(15), jdbcTemplate.queryForObject(
                "SELECT int_dispatch_order FROM frame WHERE str_name=? AND pk_job=?",
                Integer.class, "0005-pass_1", job.id));

        DispatchHost host = createHost();
        jobManager.setJobPaused(job, false);

        String[] order = new String[] {
                "0001-pass_2","0002-pass_2","0003-pass_2","0004-pass_2",
                "0005-pass_2","0006-pass_1","0006-pass_2","0007-pass_1"
        };

        for (String f: order) {
            DispatchFrame frame =  dispatcherDao.findNextDispatchFrame(job, host);
            jdbcTemplate.update("UPDATE frame SET str_state=? WHERE pk_frame=?",
                    FrameState.SUCCEEDED.toString(),frame.getFrameId());
            assertEquals(f,frame.getName());
        }

    }

    @Test
    @Transactional
    @Rollback(true)
    public void testReorderLayerReverse() {

        JobDetail job = getJob1();
        LayerInterface layer = layerDao.findLayer(job, "pass_1");

        jobManager.reorderLayer(layer, new FrameSet("1-5"), Order.REVERSE);

        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT int_dispatch_order FROM frame WHERE str_name=? AND pk_job=?",
                Integer.class, "0005-pass_1", job.id));
        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT int_dispatch_order FROM frame WHERE str_name=? AND pk_job=?",
                Integer.class, "0004-pass_1",job.id));
        assertEquals(Integer.valueOf(2), jdbcTemplate.queryForObject(
                "SELECT int_dispatch_order FROM frame WHERE str_name=? AND pk_job=?",
                Integer.class, "0003-pass_1", job.id));
        assertEquals(Integer.valueOf(3), jdbcTemplate.queryForObject(
                "SELECT int_dispatch_order FROM frame WHERE str_name=? AND pk_job=?",
                Integer.class, "0002-pass_1",job.id));
        assertEquals(Integer.valueOf(4), jdbcTemplate.queryForObject(
                "SELECT int_dispatch_order FROM frame WHERE str_name=? AND pk_job=?",
                Integer.class, "0001-pass_1", job.id));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testStaggerLayer() {

        JobDetail job = getJob1();
        LayerInterface layer = layerDao.findLayer(job, "pass_1");
        FrameSet staggeredFrameSet = new FrameSet("1-10:2");
        jobManager.staggerLayer(layer,"1-10",2);

        for (int i=0; i < staggeredFrameSet.size(); i++) {
            assertEquals(Integer.valueOf(staggeredFrameSet.get(i)), jdbcTemplate.queryForObject(
                    "SELECT int_number FROM frame WHERE str_name=? AND pk_job=?",
                    Integer.class, CueUtil.buildFrameName(layer, staggeredFrameSet.get(i)), layer.getJobId()));
        }

    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetLayers() {
        JobDetail job = getJob1();
        jobManager.getLayerDetails(job);
        jobManager.getLayers(job);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void eatLayer() {
        JobInterface job = getJob1();
        LayerInterface layer = layerDao.findLayer(job, "pass_1");
        FrameSearch r = new FrameSearch(layer);
        FrameSearchCriteria criteria = r.getCriteria();
        r.setCriteria(criteria.toBuilder()
                .setPage(1)
                .setLimit(5)
                .build());
        jobManagerSupport.eatFrames(r, new Source());

        List<Map<String,Object>> frames = jdbcTemplate.queryForList(
                "SELECT str_state FROM frame WHERE pk_layer=?",
                layer.getLayerId());

        for (Map<String,Object> m: frames) {
            assertEquals("EATEN", (String) m.get("str_state"));
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void optimizeLayer() {
        JobInterface job = getJob3();
        LayerInterface layer = layerDao.findLayer(job, "pass_1");

        assertEquals(Long.valueOf(Dispatcher.MEM_RESERVED_DEFAULT), jdbcTemplate.queryForObject(
                "SELECT int_mem_min FROM layer WHERE pk_layer=?",
                Long.class, layer.getLayerId()));

        assertEquals("general", jdbcTemplate.queryForObject(
                "SELECT str_tags FROM layer WHERE pk_layer=?",
                String.class, layer.getLayerId()));

        /*
         * Make sure the layer is optimizable.
         */
        jdbcTemplate.update("UPDATE layer_stat SET int_succeeded_count = 5 WHERE pk_layer=?",
                layer.getLayerId());

        jdbcTemplate.update(
                "UPDATE layer_usage SET layer_usage.int_core_time_success = 3500 * 5" +
                "WHERE pk_layer=?", layer.getLayerId());

        // Test to make sure our optimization
        jobManager.optimizeLayer(layer, 100, CueUtil.MB512, 120);

        assertEquals(Long.valueOf(CueUtil.MB512 + CueUtil.MB256), jdbcTemplate.queryForObject(
                "SELECT int_mem_min FROM layer WHERE pk_layer=?",
                Long.class, layer.getLayerId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testIsLayerThreadable() {
        JobInterface job = getJob3();
        LayerInterface layer = layerDao.findLayer(job, "pass_1");

        assertFalse(jobManager.isLayerThreadable(layer));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetLayer() {
        JobInterface job = getJob3();
        LayerInterface layer = layerDao.findLayer(job, "pass_1");
        assertEquals(layer, jobManager.getLayer(layer.getId()));
    }


    @Test
    @Transactional
    @Rollback(true)
    public void testFindFrame() {
        JobInterface job = getJob3();
        LayerInterface layer = layerDao.findLayer(job, "pass_1");

        FrameInterface frame = jobManager.findFrame(layer, 1);
        assertEquals("0001-pass_1", frame.getName());
    }




}

