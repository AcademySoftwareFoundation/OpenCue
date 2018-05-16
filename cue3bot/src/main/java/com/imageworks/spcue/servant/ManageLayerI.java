
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
import java.util.Set;

import org.springframework.beans.factory.InitializingBean;

import Ice.Current;

import com.imageworks.common.SpiIce.SpiIceCause;
import com.imageworks.common.SpiIce.SpiIceException;
import com.imageworks.common.spring.remoting.SpiIceExceptionGenericTemplate;
import com.imageworks.common.spring.remoting.SpiIceExceptionMinimalTemplate;

import com.imageworks.spcue.CueClientIce.*;
import com.imageworks.spcue.depend.FrameByFrame;
import com.imageworks.spcue.depend.LayerOnFrame;
import com.imageworks.spcue.depend.LayerOnJob;
import com.imageworks.spcue.depend.LayerOnLayer;
import com.imageworks.spcue.dispatcher.commands.*;
import com.imageworks.spcue.service.*;

import com.imageworks.spcue.CueIce.CueIceException;
import com.imageworks.spcue.CueIce.DependTarget;
import com.imageworks.spcue.CueIce.Order;
import com.imageworks.spcue.CueIce.RenderPartitionType;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dao.criteria.FrameSearch;
import com.imageworks.spcue.dispatcher.DispatchQueue;

import com.imageworks.spcue.util.Convert;
import com.imageworks.util.FileSequence.FrameSet;

public class ManageLayerI extends _LayerInterfaceDisp implements InitializingBean {

    /**
     *
     */
    private static final long serialVersionUID = 1L;
    private final String id;
    private LayerDetail layer;
    private JobManager jobManager;
    private JobManagerSupport jobManagerSupport;
    private DependManager dependManager;
    private LayerDao layerDao;
    private DispatchQueue manageQueue;
    private Whiteboard whiteboard;
    private LocalBookingSupport localBookingSupport;

    private FrameSearch frameSearch;

    public ManageLayerI(Ice.Identity i) throws SpiIceException {
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
        layer = layerDao.getLayerDetail(id);
        frameSearch = new FrameSearch((com.imageworks.spcue.Layer) layer);
    }

    public void eatFrames(final Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                manageQueue.execute(new DispatchEatFrames(frameSearch,
                        new Source(__current), jobManagerSupport));
            }
        }.execute();
    }

    public List<Frame> getFrames(final FrameSearchCriteria r, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Frame>>(){
            public List<Frame> throwOnlyIceExceptions() {
                r.layers.clear();
                return whiteboard.getFrames(new FrameSearch(layer, r));
            }
        }.execute();
    }

    public void killFrames(final Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                manageQueue.execute(new DispatchKillFrames(frameSearch,
                        new Source(__current), jobManagerSupport));
            }
        }.execute();
    }

    public void markdoneFrames(Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                manageQueue.execute(new DispatchSatisfyDepends(layer, jobManagerSupport));
            }
        }.execute();
    }

    public void retryFrames(final Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                manageQueue.execute(new DispatchRetryFrames(frameSearch,
                        new Source(__current), jobManagerSupport));
            }
        }.execute();
    }

    public void setNumCores(final int cores, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                layerDao.updateLayerMinCores(layer, cores);
            }
        }.execute();
    }

    public void setTags(final Set<String> tags, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                layerDao.updateLayerTags(layer, tags);
            }
        }.execute();
    }

    public void setMinCores(final float cores, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                jobManager.setLayerMinCores(layer, Convert.coresToCoreUnits(cores));
            }
        }.execute();
    }

    public void setMinMemory(final long memory, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                layerDao.updateLayerMinMemory(layer, memory);
            }
        }.execute();
    }

    public void setMinGpu(final long gpu, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                layerDao.updateLayerMinGpu(layer, gpu);
            }
        }.execute();
    }

    public Depend createDependencyOnFrame(final FrameInterfacePrx proxy, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Depend>(){
            public Depend throwOnlyIceExceptions() {
                LayerOnFrame depend = new LayerOnFrame(layer,
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
                LayerOnJob depend = new LayerOnJob(layer,
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
                LayerOnLayer depend = new LayerOnLayer(layer,
                        jobManager.getLayerDetail(
                                proxy.ice_getIdentity().name));
                dependManager.createDepend(depend);
                return whiteboard.getDepend(depend);
            }
        }.execute();
    }

    public Depend createFrameByFrameDependency(final LayerInterfacePrx proxy, boolean anyFrame, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Depend>(){
            public Depend throwOnlyIceExceptions() {
                FrameByFrame depend = new FrameByFrame(layer,
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
                return whiteboard.getWhatDependsOnThis(layer);
            }
        }.execute();
    }

    public List<Depend> getWhatThisDependsOn(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Depend>>(){
            public List<Depend> throwOnlyIceExceptions() {
                return whiteboard.getWhatThisDependsOn(layer);
            }
        }.execute();
    }

    public void dropDepends(final DependTarget target,Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                manageQueue.execute(new DispatchDropDepends(layer, target, dependManager));
            }
        }.execute();
    }

    public void reorderFrames(final String range, final Order order, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                manageQueue.execute(new DispatchReorderFrames(layer, new FrameSet(range), order, jobManagerSupport));
            }
        }.execute();
    }

    public void staggerFrames(final String range, final int stagger, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                manageQueue.execute(new DispatchStaggerFrames(layer, range, stagger, jobManagerSupport));
            }
        }.execute();
    }

    @Override
    public void setThreadable(final boolean threadable, Current arg1) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                layerDao.updateThreadable(layer, threadable);
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
                lha.setThreads(threads);
                lha.setMaxCoreUnits(maxCores * 100);
                lha.setMaxMemory(maxMemory);
                lha.setMaxGpu(maxGpu);
                lha.setType(RenderPartitionType.LayerPartition);

                if (localBookingSupport.bookLocal(layer, host,
                        __current.ctx.get("username"), lha)) {
                    return whiteboard.getRenderPartition(lha);
                }

                throw new CueIceException("Failed to find suitable frames.",
                        new String[]{}, new ArrayList<SpiIceCause>());

            }
        }.execute();
    }

    @Override
    public void registerOutputPath(final String spec, Current arg1)
            throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                jobManager.registerLayerOutput(layer, spec);
            }
        }.execute();
    }

    @Override
    public List<String> getOutputPaths(Current arg0) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<String>>(){
            public List<String> throwOnlyIceExceptions() {
                return jobManager.getLayerOutputs(layer);
            }
        }.execute();
    }

    @Override
    public void enableMemoryOptimizer(final boolean state, Current arg1)
            throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                jobManager.enableMemoryOptimizer(layer, state);
            }
        }.execute();
    }

    @Override
    public void setMaxCores(final float cores, Current arg1) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                jobManager.setLayerMaxCores(layer, Convert.coresToWholeCoreUnits(cores));
            }
        }.execute();
    }

    public DependManager getDependManager() {
        return dependManager;
    }

    public void setDependManager(DependManager dependManager) {
        this.dependManager = dependManager;
    }

    public DispatchQueue getManageQueue() {
        return manageQueue;
    }

    public void setManageQueue(DispatchQueue dispatchQueue) {
        this.manageQueue = dispatchQueue;
    }

    public JobManager getJobManager() {
        return jobManager;
    }

    public void setJobManager(JobManager jobManager) {
        this.jobManager = jobManager;
    }

    public LayerDetail getLayer() {
        return layer;
    }

    public void setLayer(LayerDetail layer) {
        this.layer = layer;
    }

    public Whiteboard getWhiteboard() {
        return whiteboard;
    }

    public void setWhiteboard(Whiteboard whiteboard) {
        this.whiteboard = whiteboard;
    }

    public LayerDao getLayerDao() {
        return layerDao;
    }

    public void setLayerDao(LayerDao layerDao) {
        this.layerDao = layerDao;
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

