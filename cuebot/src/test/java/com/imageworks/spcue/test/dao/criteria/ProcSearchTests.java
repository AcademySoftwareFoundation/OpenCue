
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

package com.imageworks.spcue.test.dao.criteria;

import com.google.common.collect.ImmutableList;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.GroupDetail;
import com.imageworks.spcue.Inherit;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.WhiteboardDao;
import com.imageworks.spcue.dao.criteria.ProcSearchFactory;
import com.imageworks.spcue.dao.criteria.ProcSearchInterface;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.host.Proc;
import com.imageworks.spcue.grpc.host.ProcSearchCriteria;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.grpc.show.Show;
import com.imageworks.spcue.service.*;
import org.junit.Before;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import java.io.File;
import java.util.List;
import java.util.stream.Collectors;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotEquals;

@Transactional
@ContextConfiguration(classes= TestAppConfig.class, loader= AnnotationConfigContextLoader.class)
public class ProcSearchTests extends AbstractTransactionalJUnit4SpringContextTests {

    private static final String FIRST_HOST = "beta01";
    private static final String SECOND_HOST = "beta02";
    private static final String FIRST_JOB = "pipe-dev.cue-testuser_shell_dispatch_test_v1";
    private static final String SECOND_JOB = "pipe-dev.cue-testuser_shell_dispatch_test_v2";
    private static final String DEFAULT_GROUP_NAME = "pipe";
    private static final String NEW_GROUP_NAME = "arbitrary-group-name";

    @Autowired
    ProcSearchFactory procSearchFactory;

    @Autowired
    JobLauncher jobLauncher;

    @Autowired
    AdminManager adminManager;

    @Autowired
    HostManager hostManager;

    @Autowired
    Dispatcher dispatcher;

    @Autowired
    JobManager jobManager;

    @Autowired
    WhiteboardDao whiteboardDao;

    @Autowired
    GroupManager groupManager;

    @Before
    public void setTestMode() {
        dispatcher.setTestMode(true);
    }

    @Test
    @Transactional
    @Rollback
    public void testGetCriteria() {
        ProcSearchCriteria criteria = ProcSearchInterface.criteriaFactory();

        ProcSearchInterface procSearch = procSearchFactory.create(criteria);

        assertEquals(criteria, procSearch.getCriteria());
    }

    @Test
    @Transactional
    @Rollback
    public void testSetCriteria() {
        ProcSearchCriteria criteria = ProcSearchInterface.criteriaFactory()
                .toBuilder()
                .addHosts("test-host")
                .build();
        ProcSearchInterface procSearch = procSearchFactory.create();

        // Ensure we can distinguish between the default and non-default criteria.
        assertNotEquals(criteria, procSearch.getCriteria());

        procSearch.setCriteria(criteria);

        assertEquals(criteria, procSearch.getCriteria());
    }

    @Test
    @Transactional
    @Rollback
    public void testNotJobs() {
        createHostsJobsAndProcs();

        JobDetail firstJob = jobManager.findJobDetail(FIRST_JOB);
        ProcSearchInterface procSearch = procSearchFactory.create();
        procSearch.notJobs(ImmutableList.of(firstJob));

        List<Proc> foundProcs = whiteboardDao.getProcs(procSearch).getProcsList();

        assertEquals(1, foundProcs.size());
        assertThat(
                foundProcs.stream().map(Proc::getJobName).collect(Collectors.toList()))
                .containsOnly(SECOND_JOB);
    }

    @Test
    @Transactional
    @Rollback
    public void testNotGroups() {
        createHostsJobsAndProcs();

        JobDetail firstJob = jobManager.findJobDetail(FIRST_JOB);
        GroupDetail newGroup = createGroup(whiteboardDao.getShow(firstJob.getShowId()));
        Inherit[] emptyInherits = {};
        groupManager.reparentJob(firstJob, newGroup, emptyInherits);

        ProcSearchInterface procSearch = procSearchFactory.create();
        procSearch.notGroups(ImmutableList.of(newGroup));

        List<Proc> foundProcs = whiteboardDao.getProcs(procSearch).getProcsList();

        assertEquals(1, foundProcs.size());
        assertThat(
                foundProcs.stream().map(Proc::getGroupName).collect(Collectors.toList()))
                .containsOnly(DEFAULT_GROUP_NAME);
    }

    @Test
    @Transactional
    @Rollback
    public void testFilterByHost() {
        createHostsJobsAndProcs();

        ProcSearchInterface procSearch = procSearchFactory.create();
        procSearch.filterByHost(hostManager.findDispatchHost(FIRST_HOST));

        List<Proc> foundProcs = whiteboardDao.getProcs(procSearch).getProcsList();

        assertEquals(1, foundProcs.size());
        assertThat(
                foundProcs.stream().map(
                        proc -> hostManager.getVirtualProc(proc.getId()).hostName)
                        .collect(Collectors.toList()))
                .containsOnly(FIRST_HOST);
    }

    // TODO: test by duration range

    private void createHostsJobsAndProcs() {
        createHosts();
        launchJobs();

        DispatchHost firstHost = hostManager.findDispatchHost(FIRST_HOST);
        DispatchHost secondHost = hostManager.findDispatchHost(SECOND_HOST);
        JobDetail firstJob = jobManager.findJobDetail(FIRST_JOB);
        JobDetail secondJob = jobManager.findJobDetail(SECOND_JOB);

        dispatcher.dispatchHost(firstHost, firstJob);
        dispatcher.dispatchHost(secondHost, secondJob);
    }

    private void launchJobs() {
        ClassLoader classLoader = getClass().getClassLoader();
        jobLauncher.testMode = true;
        File file = new File(
                classLoader.getResource("conf/jobspec/jobspec_dispatch_test.xml").getFile());
        jobLauncher.launch(file);
    }

    private RenderHost.Builder buildRenderHost() {
        return RenderHost.newBuilder()
                .setBootTime(1192369572)
                .setFreeMcp(76020)
                .setFreeMem(53500)
                .setFreeSwap(20760)
                .setLoad(1)
                .setTotalMcp(195430)
                .setTotalMem(8173264)
                .setTotalSwap(20960)
                .setNimbyEnabled(false)
                .setNumProcs(1)
                .setCoresPerProc(100)
                .addTags("test")
                .setState(HardwareState.UP)
                .setFacility("spi")
                .putAttributes("SP_OS", "Linux");
    }

    private void createHosts() {
        RenderHost host1 = buildRenderHost()
                .setName(FIRST_HOST)
                .build();
        RenderHost host2 = buildRenderHost()
                .setName(SECOND_HOST)
                .build();

        hostManager.createHost(host1,
                adminManager.findAllocationDetail("spi", "general"));
        hostManager.createHost(host2,
                adminManager.findAllocationDetail("spi", "general"));
    }

    private GroupDetail createGroup(Show show) {
        GroupDetail newGroupDetail = new GroupDetail();
        newGroupDetail.name = NEW_GROUP_NAME;
        newGroupDetail.showId = show.getId();
        groupManager.createGroup(newGroupDetail, null);
        return groupManager.getGroupDetail(
                whiteboardDao.findGroup(show.getName(), NEW_GROUP_NAME).getId());
    }
}
