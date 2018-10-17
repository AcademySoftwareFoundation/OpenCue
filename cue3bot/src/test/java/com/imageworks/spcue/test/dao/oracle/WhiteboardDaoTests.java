
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

import static org.junit.Assert.*;

import javax.annotation.Resource;

import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.transaction.TransactionConfiguration;
import org.springframework.transaction.annotation.Transactional;

import java.io.File;
import java.util.ArrayList;
import java.util.List;

import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.ActionDetail;

import com.imageworks.spcue.AllocationEntity;
import com.imageworks.spcue.CommentDetail;
import com.imageworks.spcue.Deed;
import com.imageworks.spcue.Department;
import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.FilterDetail;
import com.imageworks.spcue.Frame;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.HostDetail;
import com.imageworks.spcue.Job;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.Layer;
import com.imageworks.spcue.LightweightDependency;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.MatcherDetail;
import com.imageworks.spcue.Owner;
import com.imageworks.spcue.Point;
import com.imageworks.spcue.ServiceOverride;
import com.imageworks.spcue.Show;
import com.imageworks.spcue.ShowDetail;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.TaskDetail;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.CueClientIce.Host;
import com.imageworks.spcue.CueClientIce.HostSearchCriteria;
import com.imageworks.spcue.CueClientIce.JobSearchCriteria;

import com.imageworks.spcue.dao.*;
import com.imageworks.spcue.dao.criteria.FrameSearch;
import com.imageworks.spcue.dao.criteria.HostSearch;
import com.imageworks.spcue.dao.criteria.JobSearch;
import com.imageworks.spcue.dao.criteria.ProcSearch;
import com.imageworks.spcue.dispatcher.DispatchSupport;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.service.BookingManager;
import com.imageworks.spcue.service.CommentManager;
import com.imageworks.spcue.service.DependManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.DepartmentManager;
import com.imageworks.spcue.service.OwnerManager;
import com.imageworks.spcue.service.ServiceManager;
import com.imageworks.spcue.test.AssumingOracleEngine;
import com.imageworks.spcue.util.CueUtil;
import com.imageworks.spcue.CueIce.ActionType;
import com.imageworks.spcue.CueIce.ActionValueType;
import com.imageworks.spcue.CueIce.FilterType;
import com.imageworks.spcue.CueIce.FrameState;
import com.imageworks.spcue.CueIce.LockState;
import com.imageworks.spcue.CueIce.MatchSubject;
import com.imageworks.spcue.CueIce.MatchType;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.report.RenderHost;


@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
@TransactionConfiguration(transactionManager="transactionManager")
public class WhiteboardDaoTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Autowired
    @Rule
    public AssumingOracleEngine assumingOracleEngine;

    @Resource
    AllocationDao allocationDao;

    @Resource
    HostDao hostDao;

    @Resource
    WhiteboardDao whiteboardDao;

    @Resource
    ShowDao showDao;

    @Resource
    FilterDao filterDao;

    @Resource
    ProcDao procDao;

    @Resource
    MatcherDao matcherDao;

    @Resource
    ActionDao actionDao;

    @Resource
    JobManager jobManager;

    @Resource
    JobLauncher jobLauncher;

    @Resource
    GroupDao groupDao;

    @Resource
    LayerDao layerDao;

    @Resource
    JobDao jobDao;

    @Resource
    DepartmentDao departmentDao;

    @Resource
    DependManager dependManager;

    @Resource
    FrameDao frameDao;

    @Resource
    PointDao pointDao;

    @Resource
    HostManager hostManager;

    @Resource
    CommentManager commentManager;

    @Resource
    DepartmentManager departmentManager;

    @Resource
    Dispatcher dispatcher;

    @Resource
    DispatchSupport dispatchSupport;

    @Resource
    OwnerManager ownerManager;

    @Resource
    BookingManager bookingManager;

    @Resource
    ServiceManager serviceManager;

    private static final String HOST = "testest";
    private static final String SHOW = "pipe";

    @Before
    public void testMode() {
        jobLauncher.testMode = true;
    }

    public ShowDetail getShow() {
        return showDao.findShowDetail(SHOW);
    }

    public FilterDetail createFilter() {
        FilterDetail filter = new FilterDetail();
        filter.name = "Default";
        filter.showId = getShow().id;
        filter.type = FilterType.MatchAny;
        filter.enabled = true;
        filterDao.insertFilter(filter);
        return filter;
    }

    public MatcherDetail createMatcher(FilterDetail f) {
        MatcherDetail matcher = new MatcherDetail();
        matcher.filterId = f.id;
        matcher.name = null;
        matcher.showId = getShow().getId();
        matcher.subject = MatchSubject.JobName;
        matcher.type = MatchType.Contains;
        matcher.value = "testuser";
        matcherDao.insertMatcher(matcher);
        return matcher;
    }

    public ActionDetail createAction(FilterDetail f) {
        ActionDetail a1 = new ActionDetail();
        a1.type = ActionType.PauseJob;
        a1.filterId = f.getFilterId();
        a1.booleanValue = true;
        a1.name = null;
        a1.valueType = ActionValueType.BooleanType;
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

        Show show = getShow();
        ServiceOverride s = new ServiceOverride();
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
        assertEquals(1,whiteboardDao.getWhatDependsOnThis(job).size());

        Layer layer1 = layerDao.findLayer(job, "pass_1");
        assertEquals(0, whiteboardDao.getWhatDependsOnThis(layer1).size());

        Layer layer2 = layerDao.findLayer(job, "pass_1_preprocess");
        assertEquals(1, whiteboardDao.getWhatDependsOnThis(layer2).size());

        Frame frame = frameDao.findFrame(job, "0001-pass_1");
        assertEquals(0, whiteboardDao.getWhatDependsOnThis(frame).size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetWhatThisDependsOn() {
        JobDetail job = launchJob();
        assertEquals(0, whiteboardDao.getWhatThisDependsOn(job).size());

        Layer layer1 = layerDao.findLayer(job, "pass_1");
        assertEquals(1, whiteboardDao.getWhatThisDependsOn(layer1).size());

        Layer layer2 = layerDao.findLayer(job, "pass_1_preprocess");
        assertEquals(0, whiteboardDao.getWhatThisDependsOn(layer2).size());

        Frame frame = frameDao.findFrame(job, "0001-pass_1");
        assertEquals(1, whiteboardDao.getWhatThisDependsOn(frame).size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetDepends() {
        JobDetail job = launchJob();
        assertEquals(1,whiteboardDao.getDepends(job).size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetCommentsOnJob() {
        JobDetail job = launchJob();
        assertEquals(0,whiteboardDao.getComments(job).size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetCommentsOnHost() {

        RenderHost host = getRenderHost();
        DispatchHost hd = hostManager.createHost(host);
        hostDao.updateHostLock(hd, LockState.Locked, new Source("TEST"));

        CommentDetail c = new CommentDetail();
        c.message = "you suck";
        c.subject = "a useful message";
        c.user = "testuser";
        c.timestamp = null;

        commentManager.addComment(hd, c);
        assertEquals(1,whiteboardDao.getComments(hd).size());
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
        FilterDetail f = createFilter();
        createMatcher(f);
        whiteboardDao.getMatchers(f);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetMatcher() {
        FilterDetail f = createFilter();
        MatcherDetail m = createMatcher(f);
        whiteboardDao.getMatcher(m);
     }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetActions() {
        FilterDetail f = createFilter();
        createAction(f);
        whiteboardDao.getActions(f);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetAction() {
        FilterDetail f = createFilter();
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
        Job job = launchJob();
        FrameSearch r = new FrameSearch(job);
        r.getCriteria().page = 1;
        r.getCriteria().limit = 5;
        r.getCriteria().layers.add("pass_1");
        assertEquals(5, whiteboardDao.getFrames(r).size());
        for (com.imageworks.spcue.CueClientIce.Frame f: whiteboardDao.getFrames(r)) {
            assertEquals(f.data.layerName,"pass_1");
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

        assertTrue(dispatchSupport.stopFrame(dframe, FrameState.Succeeded, 0));
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
        assertTrue(dispatchSupport.stopFrame(dframe, FrameState.Succeeded, 0, max_rss));
        dispatchSupport.updateUsageCounters(frame, 0);
        com.imageworks.spcue.CueClientIce.Layer layer = whiteboardDao.getLayer(frame.layerId);
        assertEquals(max_rss, layer.stats.maxRss);
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
        assertTrue(dispatchSupport.stopFrame(dframe, FrameState.Succeeded, 0, max_rss));
        dispatchSupport.updateUsageCounters(frame, 0);
        com.imageworks.spcue.CueClientIce.Job ice_job = whiteboardDao.getJob(job.id);
        assertEquals(max_rss, ice_job.stats.maxRss);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetJobs() {
        launchJob();
        JobSearchCriteria r = JobSearch.criteriaFactory();
        r.shows.add("pipe");
        whiteboardDao.getJobs(new JobSearch(r));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetJobNames() {
        launchJob();
        JobSearchCriteria r = JobSearch.criteriaFactory();
        r.shows.add("pipe");
        whiteboardDao.getJobNames(new JobSearch(r));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetUpdatedFrames() {
        final JobDetail job = launchJob();
        List<Job> jobs = new ArrayList<Job>();

        jobs.add(new Job() {
            public String getJobId() { return job.getId(); }
            public String getShowId() { return null; }
            public String getId() { return job.getId(); }
            public String getName() { return null; }
            public String getFacilityId() { throw new RuntimeException("not implemented"); }
        });

        whiteboardDao.getUpdatedFrames(job, new ArrayList<Layer>(),
                (int) (System.currentTimeMillis() / 1000));

    }

    @Test(expected=IllegalArgumentException.class)
    @Transactional
    @Rollback(true)
    public void testGetUpdatedFramesFailure() {
        final JobDetail job = launchJob();
        List<Job> jobs = new ArrayList<Job>();

        jobs.add(new Job() {
            public String getJobId() { return job.getId(); }
            public String getShowId() { return null; }
            public String getId() { return job.getId(); }
            public String getName() { return null; }
            public String getFacilityId() { throw new RuntimeException("not implemented"); }
        });

        // this one should fail
        whiteboardDao.getUpdatedFrames(job, new ArrayList<Layer>(),
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
            HostDetail h = hostManager.findHostDetail(HOST);
            hostManager.deleteHost(h);
        } catch (Exception e) { }

        RenderHost host = getRenderHost();
        DispatchHost hd = hostManager.createHost(host);
        hostDao.updateHostLock(hd, LockState.Locked, new Source("TEST"));
        Host h = whiteboardDao.findHost(host.getName());
        assertEquals(host.getName(), h.data.name);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetHosts() {
        RenderHost host = getRenderHost();
        DispatchHost hd = hostManager.createHost(host);

        HostSearchCriteria h = HostSearch.criteriaFactory();
        h.hosts.add(HOST);
        assertEquals(1, whiteboardDao.getHosts(new HostSearch(h)).size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetHostsByAllocation() {
        RenderHost host = getRenderHost();
        AllocationEntity alloc = allocationDao.getAllocationEntity("00000000-0000-0000-0000-000000000006");
        DispatchHost hd = hostManager.createHost(host, alloc);

        HostSearchCriteria h = HostSearch.criteriaFactory();
        h.allocs.add(alloc.getName());
        assertEquals(1, whiteboardDao.getHosts(new HostSearch(h)).size());
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
    public void testGetDepartment() {
        Show show = showDao.findShowDetail("pipe");
        Department dept = departmentDao.getDefaultDepartment();

        com.imageworks.spcue.CueClientIce.Department d =
            whiteboardDao.getDepartment(show, dept.getName());

        assertEquals("pipe.Unknown", d.data.name);
        assertEquals("Unknown",d.data.dept);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetDepartments() {
        Show show = showDao.findShowDetail("pipe");
        whiteboardDao.getDepartments(show);
    }


    @Test
    @Transactional
    @Rollback(true)
    public void testGetDepartmentNames() {
        assertTrue(whiteboardDao.getDepartmentNames().size() > 0);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetTasks() {
        whiteboardDao.getTasks(showDao.findShowDetail("pipe"),
                departmentDao.getDefaultDepartment());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetTask() {
        Point p = pointDao.getPointConfigDetail(
                showDao.findShowDetail("pipe"),
                departmentDao.getDefaultDepartment());

        TaskDetail t = new TaskDetail(p,"dev.cue");
        departmentManager.createTask(t);

        whiteboardDao.getTask(showDao.findShowDetail("pipe"),
                departmentDao.getDefaultDepartment(), "dev.cue");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getFrame() {
        JobDetail job = launchJob();
        Frame frame = frameDao.findFrame(job, "0001-pass_1_preprocess");
        assertEquals(1, whiteboardDao.getFrame(frame.getFrameId()).data.number);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getLayer() {
        JobDetail job = launchJob();
        Layer layer = layerDao.findLayer(job, "pass_1");
        assertEquals(layer.getName(),whiteboardDao.getLayer(layer.getLayerId()).data.name);
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
        assertEquals(hd.getName(), whiteboardDao.getHost(proc.getHostId()).data.name);
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
        assertEquals(1,whiteboardDao.getProcs(proc).size());
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

        ProcSearch r;

        /*
         * Search for all 5 running procs
         */
        r = new ProcSearch();
        r.getCriteria().shows.add("pipe");
        assertEquals(5, whiteboardDao.getProcs(r).size());

        /*
         * Limit the result to 1 result.
         */
        r = new ProcSearch();
        r.getCriteria().shows.add("pipe");
        r.getCriteria().maxResults = new int[] { 1 };
        assertEquals(1, whiteboardDao.getProcs(r).size());

        /*
         * Change the first result to 1, which should limit
         * the result to 4.
         */
        r = new ProcSearch();
        r.getCriteria().shows.add("pipe");
        r.getCriteria().firstResult = 2;
        assertEquals(4, whiteboardDao.getProcs(r).size());

        /*
         * Now try to do the equivalent of a limit/offset
         */
        r = new ProcSearch();
        r.getCriteria().shows.add("pipe");
        r.getCriteria().firstResult = 3;
        r.getCriteria().maxResults = new int[] { 2 };
        assertEquals(2, whiteboardDao.getProcs(r).size());
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

        Owner owner = ownerManager.createOwner("spongebob",
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

        Owner owner = ownerManager.createOwner("spongebob",
                showDao.findShowDetail("pipe"));

        ownerManager.takeOwnership(owner, hd);
        assertTrue(whiteboardDao.getDeeds(
                showDao.findShowDetail("pipe")).size() != 0);

        assertTrue(whiteboardDao.getDeeds(
                showDao.findShowDetail("pipe")).size() != 0);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getDeedsByOwner() {

        RenderHost host = getRenderHost();
        DispatchHost hd = hostManager.createHost(host);

        Owner owner = ownerManager.createOwner("spongebob",
                showDao.findShowDetail("pipe"));

        ownerManager.takeOwnership(owner, hd);
        assertTrue(whiteboardDao.getDeeds(
                owner).size() != 0);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getHostsByOwner() {

        RenderHost host = getRenderHost();
        DispatchHost hd = hostManager.createHost(host);

        Owner owner = ownerManager.createOwner("spongebob",
                showDao.findShowDetail("pipe"));
        ownerManager.takeOwnership(owner, hd);

        assertEquals(1, whiteboardDao.getHosts(owner).size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getOwnerFromDeed() {

        RenderHost host = getRenderHost();
        DispatchHost hd = hostManager.createHost(host);

        Owner owner = ownerManager.createOwner("spongebob",
                showDao.findShowDetail("pipe"));
        Deed deed = ownerManager.takeOwnership(owner, hd);

        com.imageworks.spcue.CueClientIce.Owner o2 =
            whiteboardDao.getOwner(deed);

        assertEquals(owner.getName(), o2.name);
        assertEquals(1, o2.hostCount);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getOwnerFromHost() {

        RenderHost host = getRenderHost();
        DispatchHost hd = hostManager.createHost(host);

        Owner owner = ownerManager.createOwner("spongebob",
                showDao.findShowDetail("pipe"));
        ownerManager.takeOwnership(owner, hd);

        com.imageworks.spcue.CueClientIce.Owner o2 =
            whiteboardDao.getOwner(hd);

        assertEquals(owner.getName(), o2.name);
        assertEquals(1, o2.hostCount);
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

        assertEquals(1, whiteboardDao.getRenderPartitions(hd).size());

    }

    @Test
    @Transactional
    @Rollback(true)
    public void getFacility() {
        whiteboardDao.getFacilities();
        whiteboardDao.getFacility("spi");
    }
}


