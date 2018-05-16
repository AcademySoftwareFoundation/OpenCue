
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



package com.imageworks.spcue.servant;

import java.util.ArrayList;
import java.util.List;

import org.springframework.beans.factory.InitializingBean;

import Ice.Current;

import com.imageworks.common.SpiIce.SpiIceCause;
import com.imageworks.common.SpiIce.SpiIceException;
import com.imageworks.common.spring.remoting.SpiIceExceptionGenericTemplate;
import com.imageworks.common.spring.remoting.SpiIceExceptionMinimalTemplate;
import com.imageworks.spcue.CommentDetail;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.CueClientIce.*;
import com.imageworks.spcue.CueIce.*;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.criteria.FrameSearch;
import com.imageworks.spcue.depend.JobOnFrame;
import com.imageworks.spcue.depend.JobOnJob;
import com.imageworks.spcue.depend.JobOnLayer;
import com.imageworks.spcue.dispatcher.DispatchQueue;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.commands.*;
import com.imageworks.spcue.service.CommentManager;
import com.imageworks.spcue.service.DependManager;
import com.imageworks.spcue.service.FilterManager;
import com.imageworks.spcue.service.GroupManager;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.JobManagerSupport;
import com.imageworks.spcue.service.LocalBookingSupport;
import com.imageworks.spcue.service.Whiteboard;
import com.imageworks.spcue.util.Convert;
import com.imageworks.util.FileSequence.FrameSet;

public class ManageJobI extends _JobInterfaceDisp implements InitializingBean {

    private Whiteboard whiteboard;
    private JobManager jobManager;
    private GroupManager groupManager;
    private JobManagerSupport jobManagerSupport;
    private JobDao jobDao;
    private DependManager dependManager;
    private CommentManager commentManager;
    private DispatchQueue manageQueue;
    private Dispatcher localDispatcher;
    private LocalBookingSupport localBookingSupport;
    private FilterManager filterManager;

    private final String id;
    private com.imageworks.spcue.Job job;

    public ManageJobI(Ice.Identity i) {
        id = i.name;
    }

    @Override
    public Ice.DispatchStatus __dispatch(IceInternal.Incoming in,
                                         Current current) {
        ServantInterceptor.__dispatch(this, in, current);
        return super.__dispatch(in, current);
    }

    public void afterPropertiesSet() throws Exception {
        setJobManager(jobManagerSupport.getJobManager());
        setDependManager(jobManagerSupport.getDependManager());
        job = jobManager.getJob(id);

    }

    public List<Frame> getFrames(final FrameSearchCriteria s, Current __current)
            throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Frame>>() {
            public List<Frame> throwOnlyIceExceptions()  {
                return whiteboard.getFrames(new FrameSearch(job, s));
            }
        }.execute();
    }

    public List<Layer> getLayers(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Layer>>() {
            public List<Layer> throwOnlyIceExceptions()  {
                return whiteboard.getLayers(job);
            }
        }.execute();
    }

    public void kill(final Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                manageQueue.execute(new DispatchJobComplete(job,
                        new Source(__current), true, jobManagerSupport));
            }
        }.execute();
    }

    public void pause(Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                jobManager.setJobPaused(job, true);
            }
        }.execute();
    }

    public void resume(Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                jobManager.setJobPaused(job, false);
            }
        }.execute();
    }

    public void setMaxCores(final float val, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                jobDao.updateMaxCores(job, Convert.coresToWholeCoreUnits(val));
            }
        }.execute();
    }

    public void setMinCores(final float val, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                jobDao.updateMinCores(job, Convert.coresToWholeCoreUnits(val));
            }
        }.execute();
    }

    public void setPriority(final int val, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                jobDao.updatePriority(job, val);
            }
        }.execute();
    }

    public Job getCurrent(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Job>() {
            public Job throwOnlyIceExceptions()  {
                return whiteboard.getJob(job.getId());
            }
        }.execute();
    }

    public void eatFrames(final FrameSearchCriteria req, final Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                manageQueue.execute(
                        new DispatchEatFrames(new FrameSearch(job, req),
                                new Source(__current), jobManagerSupport));
            }
        }.execute();
    }

    public void killFrames(final FrameSearchCriteria req, final Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                manageQueue.execute(new DispatchKillFrames(
                        new FrameSearch(job, req),
                        new Source(__current), jobManagerSupport));
            }
        }.execute();
    }

    public void markDoneFrames(final FrameSearchCriteria req, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                manageQueue.execute(new DispatchSatisfyDepends(new FrameSearch(job, req), jobManagerSupport));
            }
        }.execute();
    }

    public void retryFrames(final FrameSearchCriteria req, final Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                manageQueue.execute(
                        new DispatchRetryFrames(new FrameSearch(job, req),
                                new Source(__current), jobManagerSupport));
            }
        }.execute();
    }

    public void setAutoEat(final boolean value, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                jobDao.updateAutoEat(job, value);
            }
        }.execute();
    }

    public Depend createDependencyOnFrame(final FrameInterfacePrx proxy, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Depend>(){
            public Depend throwOnlyIceExceptions() {
                JobOnFrame depend = new JobOnFrame(job,
                        jobManager.getFrameDetail(
                                proxy.ice_getIdentity().name));
                dependManager.createDepend(depend);
                return whiteboard.getDepend(depend);
            }
        }.execute();
    }

    public Depend createDependencyOnJob(final JobInterfacePrx proxy, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Depend>(){
            public Depend throwOnlyIceExceptions() {
                JobOnJob depend = new JobOnJob(job,
                        jobManager.getJobDetail(proxy.ice_getIdentity().name));
                dependManager.createDepend(depend);
                return whiteboard.getDepend(depend);
            }
        }.execute();
    }

    public Depend createDependencyOnLayer(final LayerInterfacePrx proxy, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Depend>(){
            public Depend throwOnlyIceExceptions() {
                JobOnLayer depend = new JobOnLayer(job,
                        jobManager.getLayerDetail(proxy.ice_getIdentity().name));
                dependManager.createDepend(depend);
                return whiteboard.getDepend(depend);
            }
        }.execute();
    }

    public List<Depend> getWhatDependsOnThis(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Depend>>(){
            public List<Depend> throwOnlyIceExceptions() {
                return whiteboard.getWhatDependsOnThis(job);
            }
        }.execute();
    }

    public List<Depend> getWhatThisDependsOn(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Depend>>(){
            public List<Depend> throwOnlyIceExceptions() {
                return whiteboard.getWhatThisDependsOn(job);
            }
        }.execute();
    }

    public List<Depend> getDepends(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Depend>>(){
            public List<Depend> throwOnlyIceExceptions() {
                return whiteboard.getDepends(job);
            }
        }.execute();
    }

    public UpdatedFrameCheckResult getUpdatedFrames(final int lastCheck, final List<LayerInterfacePrx> layerFilter, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<UpdatedFrameCheckResult>() {
            public UpdatedFrameCheckResult throwOnlyIceExceptions() {
                return whiteboard.getUpdatedFrames(job,
                        ServantUtil.convertLayerProxyList(layerFilter), lastCheck);
            }
        }.execute();
    }

    public void setMaxRetries(final int maxRetries, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                jobDao.updateMaxFrameRetries(job,maxRetries);
            }
        }.execute();
    }

    public void addComment(final CommentData newComment, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                CommentDetail c = new CommentDetail();
                c.message = newComment.message;
                c.subject = newComment.subject;
                c.user = newComment.user;
                c.timestamp = null;
                commentManager.addComment(job, c);
            }
        }.execute();
    }

    public List<Comment> getComments(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Comment>>(){
            public List<Comment> throwOnlyIceExceptions() {
                return whiteboard.getComments(job);
            }
        }.execute();
    }

    public void dropDepends(final DependTarget target, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                manageQueue.execute(new DispatchDropDepends(job, target, dependManager));
            }
        }.execute();
    }

    public void setGroup(final GroupInterfacePrx proxy, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                jobDao.updateParent(job,
                        groupManager.getGroupDetail(proxy.ice_getIdentity().name));
            }
        }.execute();
    }

    public void markAsWaiting(final FrameSearchCriteria req, final Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                jobManagerSupport.markFramesAsWaiting(new FrameSearch(job, req),
                        new Source(__current));
            }
        }.execute();
    }

    public void reorderFrames(final String range, final Order order, Current __current)
            throws SpiIceException {

        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                manageQueue.execute(new DispatchReorderFrames(job, new FrameSet(range), order, jobManagerSupport));
            }
        }.execute();
    }

    public void staggerFrames(final String range, final int stagger, Current __current)
            throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                manageQueue.execute(new DispatchStaggerFrames(job, range, stagger, jobManagerSupport));
            }
        }.execute();
    }

    @Override
    public RenderPartition addRenderPartition(
            final String host,
            final int threads,
            final int maxCores,
            final long maxMemory,
            final long maxGpu,
            final Current __current) throws SpiIceException {

        return new CueIceExceptionTemplate<RenderPartition>() {
            public RenderPartition throwOnlyIceExceptions() throws CueIceException {

                LocalHostAssignment lha = new LocalHostAssignment();
                lha.setJobId(id);
                lha.setThreads(threads);
                lha.setMaxCoreUnits(maxCores * 100);
                lha.setMaxMemory(maxMemory);
                lha.setMaxGpu(maxGpu);
                lha.setType(RenderPartitionType.JobPartition);

                if (localBookingSupport.bookLocal(job, host,
                        __current.ctx.get("username"), lha)) {
                    return whiteboard.getRenderPartition(lha);
                }

                throw new CueIceException("Failed to find suitable frames.",
                        new String[]{}, new ArrayList<SpiIceCause>());
            }
        }.execute();
    }

    @Override
    public void runFilters(final Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                JobDetail jobDetail = jobManager.getJobDetail(job.getJobId());
                filterManager.runFiltersOnJob(jobDetail);
            }
        }.execute();
    }

    public JobManager getJobManager() {
        return jobManager;
    }

    public void setJobManager(JobManager jobManager) {
        this.jobManager = jobManager;
    }

    public Whiteboard getWhiteboard() {
        return whiteboard;
    }

    public void setWhiteboard(Whiteboard whiteboard) {
        this.whiteboard = whiteboard;
    }

    public DispatchQueue getManageQueue() {
        return manageQueue;
    }

    public void setManageQueue(DispatchQueue dispatchQueue) {
        this.manageQueue = dispatchQueue;
    }

    public DependManager getDependManager() {
        return dependManager;
    }

    public void setDependManager(DependManager dependManager) {
        this.dependManager = dependManager;
    }

    public JobDao getJobDao() {
        return jobDao;
    }

    public void setJobDao(JobDao jobDao) {
        this.jobDao = jobDao;
    }

    public CommentManager getCommentManager() {
        return commentManager;
    }

    public void setCommentManager(CommentManager commentManager) {
        this.commentManager = commentManager;
    }

    public JobManagerSupport getJobManagerSupport() {
        return jobManagerSupport;
    }

    public void setJobManagerSupport(JobManagerSupport jobManagerSupport) {
        this.jobManagerSupport = jobManagerSupport;
    }

    public GroupManager getGroupManager() {
        return groupManager;
    }

    public void setGroupManager(GroupManager groupManager) {
        this.groupManager = groupManager;
    }

    public Dispatcher getLocalDispatcher() {
        return localDispatcher;
    }

    public void setLocalDispatcher(Dispatcher localDispatcher) {
        this.localDispatcher = localDispatcher;
    }

    public LocalBookingSupport getLocalBookingSupport() {
        return localBookingSupport;
    }

    public void setLocalBookingSupport(LocalBookingSupport localBookingSupport) {
        this.localBookingSupport = localBookingSupport;
    }

    public FilterManager getFilterManager() {
        return filterManager;
    }

    public void setFilterManager(FilterManager filterManager) {
        this.filterManager = filterManager;
    }
}

