
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

package com.imageworks.spcue.test.dao.postgres;

import java.io.File;
import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Set;
import javax.annotation.Resource;

import org.jdom.Document;
import org.jdom.Element;
import org.jdom.input.SAXBuilder;
import org.jdom.output.XMLOutputter;
import org.junit.After;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.DispatcherDao;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.GroupManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.test.AssumingPostgresEngine;
import com.imageworks.spcue.util.CueUtil;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

@Transactional
@ContextConfiguration(classes = TestAppConfig.class, loader = AnnotationConfigContextLoader.class)
public class DispatcherDaoFifoTests extends AbstractTransactionalJUnit4SpringContextTests {

    @Autowired
    @Rule
    public AssumingPostgresEngine assumingPostgresEngine;

    @Resource
    DispatcherDao dispatcherDao;

    @Resource
    HostDao hostDao;

    @Resource
    JobManager jobManager;

    @Resource
    HostManager hostManager;

    @Resource
    AdminManager adminManager;

    @Resource
    GroupManager groupManager;

    @Resource
    Dispatcher dispatcher;

    @Resource
    JobLauncher jobLauncher;

    private static final String HOSTNAME = "beta";

    public DispatchHost getHost() {
        return hostDao.findDispatchHost(HOSTNAME);
    }

    private void launchJobs(int count) throws Exception {
        Document docTemplate = new SAXBuilder(true)
                .build(new File("src/test/resources/conf/jobspec/jobspec_simple.xml"));
        docTemplate.getDocType().setSystemID("http://localhost:8080/spcue/dtd/cjsl-1.12.dtd");
        Element root = docTemplate.getRootElement();
        Element jobTemplate = root.getChild("job");
        Element depends = root.getChild("depends");
        assertEquals(jobTemplate.getAttributeValue("name"), "test");
        root.removeContent(jobTemplate);
        root.removeContent(depends);

        long t = System.currentTimeMillis();
        for (int i = 0; i < count; i++) {
            Document doc = (Document) docTemplate.clone();
            root = doc.getRootElement();
            Element job = (Element) jobTemplate.clone();
            job.setAttribute("name", "job" + i);
            root.addContent(job);
            root.addContent((Element) depends.clone());
            jobLauncher.launch(new XMLOutputter().outputString(doc));

            // Force to set incremental ts_started to the jobs
            // because current_timestamp is not updated during test.
            jdbcTemplate.update("UPDATE job SET ts_started = ? WHERE str_name = ?",
                    new Timestamp(t + i), "pipe-default-testuser_job" + i);
        }
    }

    @Before
    public void launchJob() {
        dispatcherDao.setSchedulingMode(DispatcherDao.SchedulingMode.FIFO);

        dispatcher.setTestMode(true);
        jobLauncher.testMode = true;
    }

    @After
    public void resetFifoScheduling() {
        dispatcherDao.setSchedulingMode(DispatcherDao.SchedulingMode.PRIORITY_ONLY);
    }

    @Before
    public void createHost() {
        RenderHost host = RenderHost.newBuilder().setName(HOSTNAME).setBootTime(1192369572)
                // The minimum amount of free space in the temporary directory to book a host.
                .setFreeMcp(CueUtil.GB).setFreeMem(53500).setFreeSwap(20760).setLoad(1)
                .setTotalMcp(CueUtil.GB4).setTotalMem(8173264).setTotalSwap(20960)
                .setNimbyEnabled(false).setNumProcs(2).setCoresPerProc(100).addTags("test")
                .setState(HardwareState.UP).setFacility("spi").putAttributes("SP_OS", "Linux")
                .build();

        hostManager.createHost(host, adminManager.findAllocationDetail("spi", "general"));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFifoSchedulingEnabled() {
        assertEquals(dispatcherDao.getSchedulingMode(), DispatcherDao.SchedulingMode.FIFO);
        dispatcherDao.setSchedulingMode(DispatcherDao.SchedulingMode.PRIORITY_ONLY);
        assertEquals(dispatcherDao.getSchedulingMode(), DispatcherDao.SchedulingMode.PRIORITY_ONLY);
        dispatcherDao.setSchedulingMode(DispatcherDao.SchedulingMode.FIFO);
        assertEquals(dispatcherDao.getSchedulingMode(), DispatcherDao.SchedulingMode.FIFO);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testAllSorted() throws Exception {
        int count = 10;
        launchJobs(count);

        Set<String> jobs = dispatcherDao.findDispatchJobs(getHost(), count);
        assertEquals(count, jobs.size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testPortionSorted() throws Exception {
        int count = 100;
        launchJobs(count);

        int portion = 19;
        Set<String> jobs = dispatcherDao.findDispatchJobs(getHost(), (portion + 1) / 10);
        assertEquals(portion, jobs.size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFifoSchedulingDisabled() throws Exception {
        dispatcherDao.setSchedulingMode(DispatcherDao.SchedulingMode.PRIORITY_ONLY);

        int count = 10;
        launchJobs(count);

        Set<String> jobs = dispatcherDao.findDispatchJobs(getHost(), count);
        assertEquals(count, jobs.size());

        List<String> sortedJobs = new ArrayList<String>(jobs);
        Collections.sort(sortedJobs,
                Comparator.comparing(jobId -> jobManager.getJob(jobId).getName()));

        for (int i = 0; i < count; i++) {
            assertEquals("pipe-default-testuser_job" + i,
                    jobManager.getJob(sortedJobs.get(i)).getName());
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGroup() throws Exception {
        int count = 10;
        launchJobs(count);

        JobDetail job = jobManager.findJobDetail("pipe-default-testuser_job0");
        assertNotNull(job);

        Set<String> jobs =
                dispatcherDao.findDispatchJobs(getHost(), groupManager.getGroupDetail(job));
        assertEquals(count, jobs.size());
    }
}
