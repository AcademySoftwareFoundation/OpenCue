
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
import javax.annotation.Resource;

import com.google.common.collect.Sets;
import org.apache.commons.lang.StringUtils;
import org.junit.Before;
import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.test.context.transaction.TransactionConfiguration;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.ServiceEntity;
import com.imageworks.spcue.ServiceOverrideEntity;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.JobSpec;
import com.imageworks.spcue.service.ServiceManager;
import com.imageworks.spcue.util.CueUtil;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;


@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
@TransactionConfiguration(transactionManager="transactionManager")
public class ServiceManagerTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Resource
    ServiceManager serviceManager;

    @Resource
    JobLauncher jobLauncher;

    @Resource
    JobManager jobManager;

    @Resource
    LayerDao layerDao;

    @Before
    public void setTestMode() {
        jobLauncher.testMode = true;
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetDefaultService() {
        ServiceEntity srv1 = serviceManager.getService("default");
        ServiceEntity srv2 = serviceManager.getDefaultService();

        assertEquals(srv1, srv2);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testCreateService() {
        ServiceEntity s = new ServiceEntity();
        s.name = "dillweed";
        s.minCores = 100;
        s.minMemory = CueUtil.GB4;
        s.minGpu = CueUtil.GB2;
        s.threadable = false;
        s.tags.addAll(Sets.newHashSet(new String[] { "general"}));
        serviceManager.createService(s);

        ServiceEntity newService = serviceManager.getService(s.id);
        assertEquals(s, newService);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testOverrideExistingService() {
        ServiceOverrideEntity s = new ServiceOverrideEntity();
        s.name = "arnold";
        s.minCores = 400;
        s.minMemory = CueUtil.GB8;
        s.minGpu = CueUtil.GB2;
        s.threadable = false;
        s.tags.addAll(Sets.newHashSet(new String[] { "general"}));
        s.showId = "00000000-0000-0000-0000-000000000000";
        serviceManager.createService(s);

        // Check it was overridden
        ServiceEntity newService = serviceManager.getService("arnold", s.showId);
        assertEquals(s, newService);
        assertEquals(400, newService.minCores);
        assertEquals(CueUtil.GB8, newService.minMemory);
        assertEquals(CueUtil.GB2, newService.minGpu);
        assertEquals(false, newService.threadable);
        assertTrue(s.tags.contains("general"));

        serviceManager.deleteService(s);

        // now check the original is back.
        newService = serviceManager.getService("arnold", s.showId);
        assertEquals(100, newService.minCores);
        assertEquals(0, newService.minGpu);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testJobLaunch() {

        JobSpec spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/services.xml"));
        jobLauncher.launch(spec);

        ServiceEntity shell = serviceManager.getService("shell");

        assertEquals(Integer.valueOf(shell.minCores), jdbcTemplate.queryForObject(
                "SELECT int_cores_min FROM layer WHERE pk_layer=?",
                Integer.class, spec.getJobs().get(0).getBuildableLayers().get(0).layerDetail.id));

        assertEquals(Long.valueOf(shell.minMemory), jdbcTemplate.queryForObject(
                "SELECT int_mem_min FROM layer WHERE pk_layer=?",
                Long.class, spec.getJobs().get(0).getBuildableLayers().get(0).layerDetail.id));

        assertEquals(Long.valueOf(shell.minGpu), jdbcTemplate.queryForObject(
                "SELECT int_gpu_min FROM layer WHERE pk_layer=?",
                Long.class, spec.getJobs().get(0).getBuildableLayers().get(0).layerDetail.id));

        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT b_threadable FROM layer WHERE pk_layer=?",
                Integer.class, spec.getJobs().get(0).getBuildableLayers().get(0).layerDetail.id));

        assertEquals(StringUtils.join(shell.tags," | "), jdbcTemplate.queryForObject(
                "SELECT str_tags FROM layer WHERE pk_layer=?",
                String.class, spec.getJobs().get(0).getBuildableLayers().get(0).layerDetail.id));

        assertEquals("shell,katana,unknown", jdbcTemplate.queryForObject(
                "SELECT str_services FROM layer WHERE pk_layer=?",
                String.class, spec.getJobs().get(0).getBuildableLayers().get(0).layerDetail.id));

        ServiceEntity prman = serviceManager.getService("prman");

        assertEquals(Integer.valueOf(prman.minCores), jdbcTemplate.queryForObject(
                "SELECT int_cores_min FROM layer WHERE pk_layer=?",
                Integer.class, spec.getJobs().get(0).getBuildableLayers().get(1).layerDetail.id));

        assertEquals(Long.valueOf(prman.minMemory), jdbcTemplate.queryForObject(
                "SELECT int_mem_min FROM layer WHERE pk_layer=?",
                Long.class, spec.getJobs().get(0).getBuildableLayers().get(1).layerDetail.id));

        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT b_threadable FROM layer WHERE pk_layer=?",
                Integer.class, spec.getJobs().get(0).getBuildableLayers().get(1).layerDetail.id));

        assertEquals(StringUtils.join(prman.tags," | "), jdbcTemplate.queryForObject(
                "SELECT str_tags FROM layer WHERE pk_layer=?",
                String.class, spec.getJobs().get(0).getBuildableLayers().get(1).layerDetail.id));

        assertEquals("prman,katana", jdbcTemplate.queryForObject(
                "SELECT str_services FROM layer WHERE pk_layer=?",
                String.class, spec.getJobs().get(0).getBuildableLayers().get(1).layerDetail.id));

        ServiceEntity cuda = serviceManager.getService("cuda");

        assertEquals(Integer.valueOf(cuda.minCores), jdbcTemplate.queryForObject(
                "SELECT int_cores_min FROM layer WHERE pk_layer=?",
                Integer.class, spec.getJobs().get(0).getBuildableLayers().get(3).layerDetail.id));

        assertEquals(Long.valueOf(cuda.minMemory), jdbcTemplate.queryForObject(
                "SELECT int_mem_min FROM layer WHERE pk_layer=?",
                Long.class, spec.getJobs().get(0).getBuildableLayers().get(3).layerDetail.id));

        assertEquals(Long.valueOf(cuda.minGpu), jdbcTemplate.queryForObject(
                "SELECT int_gpu_min FROM layer WHERE pk_layer=?",
                Long.class, spec.getJobs().get(0).getBuildableLayers().get(3).layerDetail.id));

        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT b_threadable FROM layer WHERE pk_layer=?",
                Integer.class, spec.getJobs().get(0).getBuildableLayers().get(3).layerDetail.id));

        assertEquals(StringUtils.join(cuda.tags," | "), jdbcTemplate.queryForObject(
                "SELECT str_tags FROM layer WHERE pk_layer=?",
                String.class, spec.getJobs().get(0).getBuildableLayers().get(3).layerDetail.id));

        assertEquals("cuda", jdbcTemplate.queryForObject(
                "SELECT str_services FROM layer WHERE pk_layer=?",
                String.class, spec.getJobs().get(0).getBuildableLayers().get(3).layerDetail.id));

    }

    @Test
    @Transactional
    @Rollback(true)
    public void testManualOverrideThreading() {

        JobSpec spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/services.xml"));
        jobLauncher.launch(spec);

        JobDetail job = spec.getJobs().get(0).detail;
        LayerInterface layer = layerDao.findLayer(job, "arnold_layer");

        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT b_threadable FROM layer WHERE pk_layer = ?",
                Integer.class, layer.getLayerId()));
    }
}

