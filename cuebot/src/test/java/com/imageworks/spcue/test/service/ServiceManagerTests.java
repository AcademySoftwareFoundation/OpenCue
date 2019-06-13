
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


import com.google.common.collect.Sets;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.ServiceEntity;
import com.imageworks.spcue.ServiceOverrideEntity;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobSpec;
import com.imageworks.spcue.service.ServiceManager;
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

import static org.hamcrest.MatcherAssert.assertThat;
import static org.hamcrest.Matchers.contains;
import static org.junit.Assert.*;


@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class ServiceManagerTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Autowired
    ServiceManager serviceManager;

    @Autowired
    JobLauncher jobLauncher;

    @Autowired
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
        s.tags.addAll(Sets.newHashSet("general"));
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
        s.tags.addAll(Sets.newHashSet("general"));
        s.showId = "00000000-0000-0000-0000-000000000000";
        serviceManager.createService(s);

        // Check it was overridden
        ServiceEntity newService = serviceManager.getService("arnold", s.showId);
        assertEquals(s, newService);
        assertEquals(400, newService.minCores);
        assertEquals(CueUtil.GB8, newService.minMemory);
        assertEquals(CueUtil.GB2, newService.minGpu);
        assertFalse(newService.threadable);
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

        JobSpec spec = jobLauncher.parse(
                new File("src/test/resources/conf/jobspec/services.xml"));
        jobLauncher.launch(spec);

        ServiceEntity shell = serviceManager.getService("shell");
        ServiceEntity prman = serviceManager.getService("prman");
        ServiceEntity cuda = serviceManager.getService("cuda");
        LayerDetail shellLayer = layerDao.getLayerDetail(
                spec.getJobs().get(0).getBuildableLayers().get(0).layerDetail.id);
        LayerDetail prmanLayer = layerDao.getLayerDetail(
                spec.getJobs().get(0).getBuildableLayers().get(1).layerDetail.id);
        LayerDetail cudaLayer = layerDao.getLayerDetail(
                spec.getJobs().get(0).getBuildableLayers().get(3).layerDetail.id);

        assertEquals(shell.minCores, shellLayer.minimumCores);
        assertEquals(shell.minMemory, shellLayer.minimumMemory);
        assertEquals(shell.minGpu, shellLayer.minimumGpu);
        assertFalse(shellLayer.isThreadable);
        assertEquals(shell.tags, shellLayer.tags);
        assertThat(shellLayer.services, contains("shell", "katana", "unknown"));

        assertEquals(prman.minCores, prmanLayer.minimumCores);
        assertEquals(prman.minMemory, prmanLayer.minimumMemory);
        assertFalse(prmanLayer.isThreadable);
        assertEquals(prman.tags, prmanLayer.tags);
        assertThat(prmanLayer.services, contains("prman", "katana"));

        assertEquals(cuda.minCores, cudaLayer.minimumCores);
        assertEquals(cuda.minMemory, cudaLayer.minimumMemory);
        assertEquals(cuda.minGpu, cudaLayer.minimumGpu);
        assertFalse(cudaLayer.isThreadable);
        assertEquals(cuda.tags, cudaLayer.tags);
        assertThat(cudaLayer.services, contains("cuda"));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testManualOverrideThreading() {

        JobSpec spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/services.xml"));
        jobLauncher.launch(spec);

        assertFalse(
                layerDao.findLayerDetail(
                        spec.getJobs().get(0).detail, "arnold_layer").isThreadable);
    }
}

