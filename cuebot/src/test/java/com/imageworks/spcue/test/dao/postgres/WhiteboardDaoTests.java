
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



package com.imageworks.spcue.test.dao.postgres;

import com.imageworks.spcue.*;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.*;
import com.imageworks.spcue.dao.criteria.*;
import com.imageworks.spcue.dispatcher.DispatchSupport;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.grpc.filter.*;
import com.imageworks.spcue.grpc.host.*;
import com.imageworks.spcue.grpc.job.*;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.*;
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
import java.util.ArrayList;
import java.util.List;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;


@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class WhiteboardDaoTests extends AbstractTransactionalJUnit4SpringContextTests  {
    
    @Autowired
    AllocationDao allocationDao;

    @Autowired
    HostDao hostDao;

    @Autowired
    WhiteboardDao whiteboardDao;

    @Autowired
    ShowDao showDao;

    @Autowired
    FilterDao filterDao;

    @Autowired
    ProcDao procDao;

    @Autowired
    MatcherDao matcherDao;

    @Autowired
    ActionDao actionDao;

    @Autowired
    JobManager jobManager;

    @Autowired
    JobLauncher jobLauncher;

    @Autowired
    GroupDao groupDao;

    @Autowired
    LayerDao layerDao;

    @Autowired
    DependManager dependManager;

    @Autowired
    FrameDao frameDao;

    @Autowired
    HostManager hostManager;

    @Autowired
    CommentManager commentManager;

    @Autowired
    Dispatcher dispatcher;

    @Autowired
    DispatchSupport dispatchSupport;

    @Autowired
    OwnerManager ownerManager;

    @Autowired
    BookingManager bookingManager;

    @Autowired
    ServiceManager serviceManager;

    @Autowired
    FrameSearchFactory frameSearchFactory;

    @Autowired
    HostSearchFactory hostSearchFactory;

    @Autowired
    JobSearchFactory jobSearchFactory;

    @Autowired
    ProcSearchFactory procSearchFactory;

    private static final String HOST = "testest";
    private static final String SHOW = "pipe";

    @Before
    public void testMode() {
        jobLauncher.testMode = true;
    }

    public ShowEntity getShow() {
        return showDao.findShowDetail(SHOW);
    }

    public FilterEntity createFilter() {
        FilterEntity filter = new FilterEntity();
        filter.name = "Default";
        filter.showId = getShow().id;
        filter.type = FilterType.MATCH_ANY;
        filter.enabled = true;
        filterDao.insertFilter(filter);
        return filter;
    }

    public MatcherEntity createMatcher(FilterEntity f) {
        MatcherEntity matcher = new MatcherEntity();
        matcher.filterId = f.id;
        matcher.name = null;
        matcher.showId = getShow().getId();
        matcher.subject = MatchSubject.JOB_NAME;
        matcher.type = MatchType.CONTAINS;
        matcher.value = "testuser";
        matcherDao.insertMatcher(matcher);
        return matcher;
    }

    public ActionEntity createAction(FilterEntity f) {
        ActionEntity a1 = new ActionEntity();
        a1.type = ActionType.PAUSE_JOB;
        a1.filterId = f.getFilterId();
        a1.booleanValue = true;
        a1.name = null;
        a1.valueType = ActionValueType.BOOLEAN_TYPE;
        actionDao.createAction(a1);
        return a1;
    }

    public RenderHost getRenderHost() {

        RenderHost host = RenderHost.newBuilder()
                .setName(HOST)
                .setBootTime(1192369572)
                .setFreeMcp(7602)
                .setFreeMem((int) Dispatcher.MEM_RESERVED_MIN * 4)
                .setFreeSwap(2076)
                .setLoad(1)
                .setTotalMcp(19543)
                .setTotalMem((int) Dispatcher.MEM_RESERVED_MIN * 4)
                .setTotalSwap(2096)
                .setNimbyEnabled(true)
                .setNumProcs(2)
                .setCoresPerProc(400)
                .setState(HardwareState.DOWN)
                .setFacility("spi")
                .putAttributes("freeGpu", String.format("%d", CueUtil.MB512))
                .putAttributes("totalGpu", String.format("%d", CueUtil.MB512))
                .build();
        return host;
    }

    public JobDetail launchJob() {
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        return jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
    }


    @Test
    @Transactional
    @Rollback(true)
    public void getService() {
        whiteboardDao.getService("arnold");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getServices() {
        whiteboardDao.getDefaultServices();
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getServiceOverride() {

        ShowEntity show = getShow();
        ServiceOverrideEntity s = new ServiceOverrideEntity();
        s.name = "test";
        s.minCores = 100;
        s.minMemory = 320000;
        s.tags.add("general");
        s.threadable = false;
        s.showId = show.getId();

        serviceManager.createService(s);
        whiteboardDao.getServiceOverride(getShow(), "test");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getServiceOverrides() {
        whiteboardDao.getServiceOverrides(getShow());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetDepend() {

        List<LightweightDependency> depends = dependManager.getWhatDependsOn(launchJob());
        for (LightweightDependency depend: depends) {
            whiteboardDao.getDepend(depend);
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetDependById() {

        List<LightweightDependency> depends = dependManager.getWhatDependsOn(launchJob());
        for (LightweightDependency depend: depends) {
            whiteboardDao.getDepend(depend);
            whiteboardDao.getDepend(depend.id);
        }
    }


    @Test
    @Transactional
    @Rollback(true)
    public void testGetWhatDependsOnThis() {
        JobDetail job = launchJob();
        assertEquals(1,whiteboardDao.getWhatDependsOnThis(job).getDependsCount());

        LayerInterface layer1 = layerDao.findLayer(job, "pass_1");
        assertEquals(0, whiteboardDao.getWhatDependsOnThis(layer1).getDependsCount());

        LayerInterface layer2 = layerDao.findLayer(job, "pass_1_preprocess");
        assertEquals(1, whiteboardDao.getWhatDependsOnThis(layer2).getDependsCount());

        FrameInterface frame = frameDao.findFrame(job, "0001-pass_1");
        assertEquals(0, whiteboardDao.getWhatDependsOnThis(frame).getDependsCount());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetWhatThisDependsOn() {
        JobDetail job = launchJob();
        assertEquals(0, whiteboardDao.getWhatThisDependsOn(job).getDependsCount());

        LayerInterface layer1 = layerDao.findLayer(job, "pass_1");
        assertEquals(1, whiteboardDao.getWhatThisDependsOn(layer1).getDependsCount());

        LayerInterface layer2 = layerDao.findLayer(job, "pass_1_preprocess");
        assertEquals(0, whiteboardDao.getWhatThisDependsOn(layer2).getDependsCount());

        FrameInterface frame = frameDao.findFrame(job, "0001-pass_1");
        assertEquals(1, whiteboardDao.getWhatThisDependsOn(frame).getDependsCount());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetDepends() {
        JobDetail job = launchJob();
        assertEquals(1,whiteboardDao.getDepends(job).getDependsCount());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetCommentsOnJob() {
        JobDetail job = launchJob();
        assertEquals(0,whiteboardDao.getComments(job).getCommentsCount());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetCommentsOnHost() {

        RenderHost host = getRenderHost();
        DispatchHost hd = hostManager.createHost(host);
        hostDao.updateHostLock(hd, LockState.LOCKED, new Source("TEST"));

        CommentDetail c = new CommentDetail();
        c.message = "you suck";
        c.subject = "a useful message";
        c.user = "testuser";
        c.timestamp = null;

        commentManager.addComment(hd, c);
        assertEquals(1,whiteboardDao.getComments(hd).getCommentsCount());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindFilter() {
        createFilter();
        whiteboardDao.findFilter(getShow(), "Default");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetFilter() {
        whiteboardDao.getFilter(createFilter());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetMatchers() {
        FilterEntity f = createFilter();
        createMatcher(f);
        whiteboardDao.getMatchers(f);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetMatcher() {
        FilterEntity f = createFilter();
        MatcherEntity m = createMatcher(f);
        whiteboardDao.getMatcher(m);
     }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetActions() {
        FilterEntity f = createFilter();
        createAction(f);
        whiteboardDao.getActions(f);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetAction() {
        FilterEntity f = createFilter();
        whiteboardDao.getAction(createAction(f));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetFilters() {
        createFilter();
        whiteboardDao.getFilters(getShow());
   }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetFramesByFrameSearch() {
        JobEntity job = launchJob();
        FrameSearchInterface r = frameSearchFactory.create(job);
        FrameSearchCriteria criteria = r.getCriteria();
        r.setCriteria(criteria.toBuilder()
                .setPage(1)
                .setLimit(5)
                .addLayers("pass_1")
                .build());
        assertEquals(5, whiteboardDao.getFrames(r).getFramesCount());
        for (Frame f: whiteboardDao.getFrames(r).getFramesList()) {
            assertEquals(f.getLayerName(), "pass_1");
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetLayers() {
        JobDetail job = launchJob();
        whiteboardDao.getLayers(job);

        RenderHost host = getRenderHost();
        DispatchHost hd = hostManager.createHost(host);
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1_preprocess");


        VirtualProc proc = new VirtualProc();
        proc.allocationId = null;
        proc.coresReserved = 100;
        proc.hostId = hd.id;
        proc.hostName = host.getName();
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;

        DispatchFrame dframe = frameDao.getDispatchFrame(frame.getId());
        dispatcher.setTestMode(true);
        dispatcher.dispatch(dframe, proc);

        try {
            Thread.sleep(2000);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }

        dframe = frameDao.getDispatchFrame(frame.getId());

        assertTrue(dispatchSupport.stopFrame(dframe, FrameState.SUCCEEDED, 0));
        dispatchSupport.updateUsageCounters(frame, 0);
        whiteboardDao.getLayers(job);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testStopFrameUpdatesLayerMaxRSS() {
        long max_rss = 123456L;

        JobDetail job = launchJob();
        whiteboardDao.getLayers(job);

        RenderHost host = getRenderHost();
        DispatchHost hd = hostManager.createHost(host);
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1_preprocess");


        VirtualProc proc = new VirtualProc();
        proc.allocationId = null;
        proc.coresReserved = 100;
        proc.hostId = hd.id;
        proc.hostName = host.getName();
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;

        DispatchFrame dframe = frameDao.getDispatchFrame(frame.getId());
        dispatcher.setTestMode(true);
        dispatcher.dispatch(dframe, proc);

        try {
            Thread.sleep(2000);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }

        dframe = frameDao.getDispatchFrame(frame.getId());

        // Note use of 4-arg stopFrame here to update max rss.
        assertTrue(dispatchSupport.stopFrame(dframe, FrameState.SUCCEEDED, 0, max_rss));
        dispatchSupport.updateUsageCounters(frame, 0);
        Layer layer = whiteboardDao.getLayer(frame.layerId);
        assertEquals(max_rss, layer.getLayerStats().getMaxRss());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testStopFrameUpdatesJobMaxRSS() {
        long max_rss = 123456L;

        JobDetail job = launchJob();
        whiteboardDao.getLayers(job);

        RenderHost host = getRenderHost();
        DispatchHost hd = hostManager.createHost(host);
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1_preprocess");


        VirtualProc proc = new VirtualProc();
        proc.allocationId = null;
        proc.coresReserved = 100;
        proc.hostId = hd.id;
        proc.hostName = host.getName();
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;

        DispatchFrame dframe = frameDao.getDispatchFrame(frame.getId());
        dispatcher.setTestMode(true);
        dispatcher.dispatch(dframe, proc);

        try {
            Thread.sleep(2000);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }

        dframe = frameDao.getDispatchFrame(frame.getId());

        // Note use of 4-arg stopFrame here to update max rss.
        assertTrue(dispatchSupport.stopFrame(dframe, FrameState.SUCCEEDED, 0, max_rss));
        dispatchSupport.updateUsageCounters(frame, 0);
        Job grpc_job = whiteboardDao.getJob(job.id);
        assertEquals(max_rss, grpc_job.getJobStats().getMaxRss());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetJobs() {
        launchJob();
        JobSearchCriteria r = JobSearchInterface.criteriaFactory();
        r = r.toBuilder().addShows("pipe").build();
        whiteboardDao.getJobs(jobSearchFactory.create(r));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetJobNames() {
        launchJob();
        JobSearchCriteria r = JobSearchInterface.criteriaFactory();
        r = r.toBuilder().addShows("pipe").build();
        whiteboardDao.getJobNames(jobSearchFactory.create(r));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetUpdatedFrames() {
        final JobDetail job = launchJob();
        List<JobInterface> jobs = new ArrayList<JobInterface>();

        jobs.add(new JobInterface() {
            public String getJobId() { return job.getId(); }
            public String getShowId() { return null; }
            public String getId() { return job.getId(); }
            public String getName() { return null; }
            public String getFacilityId() { throw new RuntimeException("not implemented"); }
        });

        whiteboardDao.getUpdatedFrames(job, new ArrayList<LayerInterface>(),
                (int) (System.currentTimeMillis() / 1000));

    }

    @Test(expected=IllegalArgumentException.class)
    @Transactional
    @Rollback(true)
    public void testGetUpdatedFramesFailure() {
        final JobDetail job = launchJob();
        List<JobInterface> jobs = new ArrayList<JobInterface>();

        jobs.add(new JobInterface() {
            public String getJobId() { return job.getId(); }
            public String getShowId() { return null; }
            public String getId() { return job.getId(); }
            public String getName() { return null; }
            public String getFacilityId() { throw new RuntimeException("not implemented"); }
        });

        // this one should fail
        whiteboardDao.getUpdatedFrames(job, new ArrayList<LayerInterface>(),
                (int) (System.currentTimeMillis() / 1000 - 1000000));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindJob() {
        JobDetail job = launchJob();
        whiteboardDao.findJob(job.name);
     }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetJob() {
        JobDetail job = launchJob();
        whiteboardDao.getJob(job.id);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetSubscriptionByID() {
        whiteboardDao.getSubscription("00000000-0000-0000-0000-000000000001");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void findFindSubscription() {
        whiteboardDao.findSubscription("pipe", "spi.general");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetSubscriptions() {
        whiteboardDao.getSubscriptions(getShow());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetSubscriptionsByAllocation() {
        whiteboardDao.getSubscriptions(
                allocationDao.findAllocationEntity("spi", "general"));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetShow() {
        whiteboardDao.getShow(getShow().id);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindShow() {
        whiteboardDao.findShow(getShow().name);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetShows() {
        whiteboardDao.getShows();
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetActiveShows() {
        whiteboardDao.getActiveShows();
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindHost() {

        try {
            HostEntity h = hostManager.findHostDetail(HOST);
            hostManager.deleteHost(h);
        } catch (Exception e) { }

        RenderHost host = getRenderHost();
        DispatchHost hd = hostManager.createHost(host);
        hostDao.updateHostLock(hd, LockState.LOCKED, new Source("TEST"));
        Host h = whiteboardDao.findHost(host.getName());
        assertEquals(host.getName(), h.getName());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetHosts() {
        RenderHost host = getRenderHost();
        DispatchHost hd = hostManager.createHost(host);

        HostSearchCriteria h = HostSearchInterface.criteriaFactory();
        h = h.toBuilder().addHosts(HOST).build();
        assertEquals(1, whiteboardDao.getHosts(hostSearchFactory.create(h)).getHostsCount());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetHostsByAllocation() {
        RenderHost host = getRenderHost();
        AllocationEntity alloc = allocationDao.getAllocationEntity("00000000-0000-0000-0000-000000000006");
        DispatchHost hd = hostManager.createHost(host, alloc);

        HostSearchCriteria h = HostSearchInterface.criteriaFactory();
        h = h.toBuilder().addAllocs(alloc.getName()).build();
        assertEquals(1, whiteboardDao.getHosts(hostSearchFactory.create(h)).getHostsCount());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetAllocation() {
        whiteboardDao.getAllocation("00000000-0000-0000-0000-000000000000");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindAllocation() {
        whiteboardDao.findAllocation("spi.general");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetAllocations() {
        whiteboardDao.getAllocations();
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetRootGroup() {
        whiteboardDao.getRootGroup(getShow());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetGroup() {
        whiteboardDao.getGroup("A0000000-0000-0000-0000-000000000000");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetGroups() {
        whiteboardDao.getGroups(getShow());
        whiteboardDao.getGroup(groupDao.getRootGroupId(getShow()));
        whiteboardDao.getGroups(groupDao.getRootGroupDetail(getShow()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindGroup() {
        whiteboardDao.findGroup("pipe", "pipe");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindFrame() {
        JobDetail job = launchJob();
        whiteboardDao.findFrame(job.name, "pass_1", 1);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindFilterByName() {
        createFilter();
        whiteboardDao.findFilter("pipe", "Default");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindLayer() {
        JobDetail job = launchJob();
        whiteboardDao.findLayer(job.name, "pass_1");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getFrame() {
        JobDetail job = launchJob();
        FrameInterface frame = frameDao.findFrame(job, "0001-pass_1_preprocess");
        assertEquals(1, whiteboardDao.getFrame(frame.getFrameId()).getNumber());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getLayer() {
        JobDetail job = launchJob();
        LayerInterface layer = layerDao.findLayer(job, "pass_1");
        assertEquals(layer.getName(),whiteboardDao.getLayer(layer.getLayerId()).getName());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getHost() {

        RenderHost host = getRenderHost();
        DispatchHost hd = hostManager.createHost(host);

        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1_preprocess");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = null;
        proc.coresReserved = 100;
        proc.hostId = hd.id;
        proc.hostName = host.getName();
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;

        procDao.insertVirtualProc(proc);
        assertEquals(hd.getName(), whiteboardDao.getHost(proc.getHostId()).getName());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getProcs() {
        RenderHost host = getRenderHost();
        DispatchHost hd = hostManager.createHost(host);
        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1_preprocess");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = null;
        proc.coresReserved = 100;
        proc.hostId = hd.id;
        proc.hostName = host.getName();
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;

        procDao.insertVirtualProc(proc);
        assertEquals(1,whiteboardDao.getProcs(proc).getProcsCount());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getProcsBySearch() {
        RenderHost host = getRenderHost();
        DispatchHost hd = hostManager.createHost(host);

        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_dispatch_test.xml"));
        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_dispatch_test_v1");

        /*
         * Book 5 procs.
         */
        for (int i=1; i<6; i++) {
            FrameDetail f = frameDao.findFrameDetail(job, String.format("%04d-pass_1",i));
            VirtualProc proc = new VirtualProc();
            proc.allocationId = null;
            proc.coresReserved = 100;
            proc.hostId = hd.id;
            proc.hostName = host.getName();
            proc.jobId = job.id;
            proc.frameId = f.id;
            proc.layerId = f.layerId;
            proc.showId = f.showId;
            procDao.insertVirtualProc(proc);
        }

        ProcSearchInterface r;

        /*
         * Search for all 5 running procs
         */
        r = procSearchFactory.create();
        ProcSearchCriteria criteria = r.getCriteria();
        r.setCriteria(criteria.toBuilder().addShows("pipe").build());
        assertEquals(5, whiteboardDao.getProcs(r).getProcsCount());

        /*
         * Limit the result to 1 result.
         */
        r = procSearchFactory.create();
        ProcSearchCriteria criteriaA = r.getCriteria();
        r.setCriteria(criteriaA.toBuilder()
                .addShows("pipe")
                .addMaxResults(1)
                .build());
        assertEquals(1, whiteboardDao.getProcs(r).getProcsCount());

        /*
         * Change the first result to 1, which should limit
         * the result to 4.
         */
        r = procSearchFactory.create();
        ProcSearchCriteria criteriaB = r.getCriteria();
        r.setCriteria(criteriaB.toBuilder()
                .addShows("pipe")
                .setFirstResult(2)
                .build());
        assertEquals(4, whiteboardDao.getProcs(r).getProcsCount());

        /*
         * Now try to do the equivalent of a limit/offset
         */
        r = procSearchFactory.create();
        ProcSearchCriteria criteriaC = r.getCriteria();
        r.setCriteria(criteriaC.toBuilder()
                .addShows("pipe")
                .setFirstResult(3)
                .addMaxResults(2)
                .build());
        assertEquals(2, whiteboardDao.getProcs(r).getProcsCount());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getOwner() {
        ownerManager.createOwner("spongebob",
                showDao.findShowDetail("pipe"));
        whiteboardDao.getOwner("spongebob");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getOwnersByShow() {
        RenderHost host = getRenderHost();
        DispatchHost hd = hostManager.createHost(host);

        OwnerEntity owner = ownerManager.createOwner("spongebob",
                showDao.findShowDetail("pipe"));

        ownerManager.takeOwnership(owner, hd);

        assertTrue(whiteboardDao.getOwners(
                showDao.findShowDetail("pipe")).size() != 0);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getDeedsByShow() {

        RenderHost host = getRenderHost();
        DispatchHost hd = hostManager.createHost(host);

        OwnerEntity owner = ownerManager.createOwner("spongebob",
                showDao.findShowDetail("pipe"));

        ownerManager.takeOwnership(owner, hd);
        assertTrue(whiteboardDao.getDeeds(
                showDao.findShowDetail("pipe")).getDeedsCount() != 0);

        assertTrue(whiteboardDao.getDeeds(
                showDao.findShowDetail("pipe")).getDeedsCount() != 0);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getDeedsByOwner() {

        RenderHost host = getRenderHost();
        DispatchHost hd = hostManager.createHost(host);

        OwnerEntity owner = ownerManager.createOwner("spongebob",
                showDao.findShowDetail("pipe"));

        ownerManager.takeOwnership(owner, hd);
        assertTrue(whiteboardDao.getDeeds(
                owner).getDeedsCount() != 0);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getHostsByOwner() {

        RenderHost host = getRenderHost();
        DispatchHost hd = hostManager.createHost(host);

        OwnerEntity owner = ownerManager.createOwner("spongebob",
                showDao.findShowDetail("pipe"));
        ownerManager.takeOwnership(owner, hd);

        assertEquals(1, whiteboardDao.getHosts(owner).getHostsCount());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getOwnerFromDeed() {

        RenderHost host = getRenderHost();
        DispatchHost hd = hostManager.createHost(host);

        OwnerEntity owner = ownerManager.createOwner("spongebob",
                showDao.findShowDetail("pipe"));
        DeedEntity deed = ownerManager.takeOwnership(owner, hd);

        Owner o2 = whiteboardDao.getOwner(deed);

        assertEquals(owner.getName(), o2.getName());
        assertEquals(1, o2.getHostCount());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getOwnerFromHost() {

        RenderHost host = getRenderHost();
        DispatchHost hd = hostManager.createHost(host);

        OwnerEntity owner = ownerManager.createOwner("spongebob",
                showDao.findShowDetail("pipe"));
        ownerManager.takeOwnership(owner, hd);

        Owner o2 = whiteboardDao.getOwner(hd);

        assertEquals(owner.getName(), o2.getName());
        assertEquals(1, o2.getHostCount());
    }


    @Test
    @Transactional
    @Rollback(true)
    public void getRenderPartition() {

        RenderHost host = getRenderHost();
        DispatchHost hd = hostManager.createHost(host);

        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_dispatch_test.xml"));
        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_dispatch_test_v1");

        LocalHostAssignment lba = new LocalHostAssignment(800, 8, CueUtil.GB8, 1);
        bookingManager.createLocalHostAssignment(hd, job, lba);

        whiteboardDao.getRenderPartition(lba);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getRenderPartitionsByHost() {

        RenderHost host = getRenderHost();
        DispatchHost hd = hostManager.createHost(host);

        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_dispatch_test.xml"));
        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_dispatch_test_v1");

        LocalHostAssignment lba = new LocalHostAssignment(800, 8, CueUtil.GB8, 1);
        bookingManager.createLocalHostAssignment(hd, job, lba);

        assertEquals(1, whiteboardDao.getRenderPartitions(hd).getRenderPartitionsCount());

    }

    @Test
    @Transactional
    @Rollback(true)
    public void getFacility() {
        whiteboardDao.getFacilities();
        whiteboardDao.getFacility("spi");
    }
}


