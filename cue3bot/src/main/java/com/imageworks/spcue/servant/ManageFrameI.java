
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

import org.apache.log4j.Logger;
import org.springframework.beans.factory.InitializingBean;

import Ice.Current;

import com.imageworks.common.SpiIce.SpiIceCause;
import com.imageworks.common.SpiIce.SpiIceException;
import com.imageworks.common.spring.remoting.SpiIceExceptionGenericTemplate;
import com.imageworks.common.spring.remoting.SpiIceExceptionMinimalTemplate;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.CueClientIce.Depend;
import com.imageworks.spcue.CueClientIce.FrameInterfacePrx;
import com.imageworks.spcue.CueClientIce.JobInterfacePrx;
import com.imageworks.spcue.CueClientIce.LayerInterfacePrx;
import com.imageworks.spcue.CueClientIce.RenderPartition;
import com.imageworks.spcue.CueClientIce._FrameInterfaceDisp;
import com.imageworks.spcue.CueIce.CheckpointState;
import com.imageworks.spcue.CueIce.CueIceException;
import com.imageworks.spcue.CueIce.DependTarget;
import com.imageworks.spcue.CueIce.RenderPartitionType;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.criteria.FrameSearch;
import com.imageworks.spcue.depend.FrameOnFrame;
import com.imageworks.spcue.depend.FrameOnJob;
import com.imageworks.spcue.depend.FrameOnLayer;
import com.imageworks.spcue.dispatcher.DispatchQueue;
import com.imageworks.spcue.dispatcher.commands.DispatchDropDepends;
import com.imageworks.spcue.dispatcher.commands.DispatchEatFrames;
import com.imageworks.spcue.dispatcher.commands.DispatchKillFrames;
import com.imageworks.spcue.dispatcher.commands.DispatchRetryFrames;
import com.imageworks.spcue.service.DependManager;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.JobManagerSupport;
import com.imageworks.spcue.service.LocalBookingSupport;
import com.imageworks.spcue.service.Whiteboard;

public class ManageFrameI extends _FrameInterfaceDisp implements InitializingBean {

    @SuppressWarnings("unused")
    private static final Logger logger = Logger.getLogger(ManageFrameI.class);

    private final String id;
    private FrameDetail frame;
    private JobManager jobManager;
    private JobManagerSupport jobManagerSupport;
    private FrameDao frameDao;
    private DispatchQueue manageQueue;
    private Whiteboard whiteboard;
    private DependManager dependManager;
    private LocalBookingSupport localBookingSupport;

    public ManageFrameI(Ice.Identity i) {
        this.id = i.name;
    }

    @Override
    public Ice.DispatchStatus __dispatch(IceInternal.Incoming in,
                                         Current current) {
        ServantInterceptor.__dispatch(this, in, current);
        return super.__dispatch(in, current);
    }

    public void afterPropertiesSet() throws Exception {
        setDependManager(jobManagerSupport.getDependManager());
        setJobManager(jobManagerSupport.getJobManager());
        frame = frameDao.getFrameDetail(id);
    }

    public void eat(final Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                manageQueue.execute(new DispatchEatFrames(new FrameSearch(frame),
                        new Source(__current),jobManagerSupport));
            }
        }.execute();
    }

    public void kill(final Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                manageQueue.execute(new DispatchKillFrames(new FrameSearch(frame),
                        new Source(__current), jobManagerSupport));
            }
        }.execute();
    }

    public void retry(final Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                manageQueue.execute(new DispatchRetryFrames(new FrameSearch(frame),
                        new Source(__current), jobManagerSupport));
            }
        }.execute();
    }

    public Depend createDependencyOnFrame(final FrameInterfacePrx proxy, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Depend>(){
            public Depend throwOnlyIceExceptions() {
                FrameOnFrame depend = new FrameOnFrame(frame,
                        jobManager.getFrameDetail(proxy.ice_getIdentity().name));
                dependManager.createDepend(depend);
                return whiteboard.getDepend(depend);
            }
        }.execute();
    }

    public Depend createDependencyOnJob(final JobInterfacePrx proxy, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Depend>(){
            public Depend throwOnlyIceExceptions() {
                FrameOnJob depend = new FrameOnJob(frame,
                        jobManager.getJobDetail(
                                proxy.ice_getIdentity().name));
                dependManager.createDepend(depend);
                return whiteboard.getDepend(depend);
            }
        }.execute();
    }

    public Depend createDependencyOnLayer(final LayerInterfacePrx proxy, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Depend>(){
            public Depend throwOnlyIceExceptions() {
                FrameOnLayer depend = new FrameOnLayer(frame,
                        jobManager.getLayerDetail(
                                proxy.ice_getIdentity().name));
                dependManager.createDepend(depend);
                return whiteboard.getDepend(depend);
            }
        }.execute();
    }

    public List<Depend> getWhatDependsOnThis(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Depend>>(){
            public List<Depend> throwOnlyIceExceptions() {
                return whiteboard.getWhatDependsOnThis(frame);
            }
        }.execute();
    }

    public List<Depend> getWhatThisDependsOn(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Depend>>(){
            public List<Depend> throwOnlyIceExceptions() {
                return whiteboard.getWhatThisDependsOn(frame);
            }
        }.execute();
    }

    public void markAsDepend(Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                jobManager.markFrameAsDepend(frame);
            }
        }.execute();
    }

    public void markAsWaiting(Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                jobManager.markFrameAsWaiting(frame);
            }
        }.execute();
    }

    public void dropDepends(final DependTarget target, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                manageQueue.execute(new DispatchDropDepends(frame, target, dependManager));
            }
        }.execute();
    }

    @Override
    public RenderPartition addRenderPartition(
            final String hostname,
            final int threads,
            final int maxCores,
            final long maxMemory,
            final long maxGpu,
            final Current __current) throws SpiIceException {

        return new CueIceExceptionTemplate<RenderPartition>() {
            public RenderPartition throwOnlyIceExceptions() throws CueIceException {

                LocalHostAssignment lha = new LocalHostAssignment();
                lha.setFrameId(frame.id);
                lha.setThreads(threads);
                lha.setMaxCoreUnits(maxCores * 100);
                lha.setMaxMemory(maxMemory);
                lha.setMaxGpu(maxGpu);
                lha.setType(RenderPartitionType.FramePartition);

                if (localBookingSupport.bookLocal(frame, hostname,
                        __current.ctx.get("username"), lha)) {
                    return whiteboard.getRenderPartition(lha);
                }

                throw new CueIceException("Failed to find suitable frames.",
                        new String[]{}, new ArrayList<SpiIceCause>());
            }
        }.execute();
    }

    @Override
    public void setCheckpointState(final CheckpointState arg0, Current arg1)
            throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                jobManager.updateCheckpointState(frame, arg0);
            }
        }.execute();
    }

    public JobManager getJobManager() {
        return jobManager;
    }

    public void setJobManager(JobManager jobManager) {
        this.jobManager = jobManager;
    }

    public DispatchQueue getManageQueue() {
        return manageQueue;
    }

    public void setManageQueue(DispatchQueue dispatchQueue) {
        this.manageQueue = dispatchQueue;
    }

    public FrameDao getFrameDao() {
        return frameDao;
    }

    public void setFrameDao(FrameDao frameDao) {
        this.frameDao = frameDao;
    }

    public Whiteboard getWhiteboard() {
        return whiteboard;
    }

    public void setWhiteboard(Whiteboard whiteboard) {
        this.whiteboard = whiteboard;
    }

    public DependManager getDependManager() {
        return dependManager;
    }

    public void setDependManager(DependManager dependManager) {
        this.dependManager = dependManager;
    }

    public JobManagerSupport getJobManagerSupport() {
        return jobManagerSupport;
    }

    public void setJobManagerSupport(JobManagerSupport jobManagerSupport) {
        this.jobManagerSupport = jobManagerSupport;
    }

    public LocalBookingSupport getLocalBookingSupport() {
        return localBookingSupport;
    }

    public void setLocalBookingSupport(LocalBookingSupport localBookingSupport) {
        this.localBookingSupport = localBookingSupport;
    }
}

