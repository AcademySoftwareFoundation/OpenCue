
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

import org.springframework.beans.factory.InitializingBean;

import Ice.Current;

import com.imageworks.common.SpiIce.SpiIceException;
import com.imageworks.common.spring.remoting.SpiIceExceptionGenericTemplate;
import com.imageworks.common.spring.remoting.SpiIceExceptionMinimalTemplate;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.CueClientIce.Frame;
import com.imageworks.spcue.CueClientIce.GroupInterfacePrx;
import com.imageworks.spcue.CueClientIce.Host;
import com.imageworks.spcue.CueClientIce.Job;
import com.imageworks.spcue.CueClientIce.JobInterfacePrx;
import com.imageworks.spcue.CueClientIce.Layer;

import com.imageworks.spcue.CueClientIce._ProcInterfaceDisp;
import com.imageworks.spcue.CueIce.EntityNotFoundException;
import com.imageworks.spcue.dao.ProcDao;
import com.imageworks.spcue.dispatcher.RedirectManager;
import com.imageworks.spcue.service.GroupManager;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.JobManagerSupport;
import com.imageworks.spcue.service.Whiteboard;

public class ManageProcI extends _ProcInterfaceDisp implements InitializingBean  {

    private final String id;
    private VirtualProc proc;;
    private ProcDao procDao;
    private Whiteboard whiteboard;
    private JobManagerSupport jobManagerSupport;
    private JobManager jobManager;
    private GroupManager groupManager;
    private RedirectManager redirectManager;

    public ManageProcI(Ice.Identity i) {
        this.id = i.name;
    }

    @Override
    public Ice.DispatchStatus __dispatch(IceInternal.Incoming in,
                                         Current current) {
        ServantInterceptor.__dispatch(this, in, current);
        return super.__dispatch(in, current);
    }

    public void afterPropertiesSet() throws Exception {
        proc = procDao.getVirtualProc(id);
    }

    public Frame getFrame(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Frame>() {
            public Frame throwOnlyIceExceptions() throws SpiIceException {
                try {
                    return whiteboard.getFrame(procDao.getCurrentFrameId(proc));
                } catch (org.springframework.dao.EmptyResultDataAccessException e) {
                    throw new EntityNotFoundException("frame not found", null, null);
                }
            }
        }.execute();
    }

    public Host getHost(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Host>() {
            public Host throwOnlyIceExceptions() throws SpiIceException {
                try {
                    return whiteboard.getHost(proc.getHostId());
                } catch (org.springframework.dao.EmptyResultDataAccessException e) {
                    throw new EntityNotFoundException("host not found",null,null);
                }
            }
        }.execute();
    }

    public Job getJob(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Job>() {
            public Job throwOnlyIceExceptions() throws SpiIceException {
                try {
                    return whiteboard.getJob(procDao.getCurrentJobId(proc));
                } catch (org.springframework.dao.EmptyResultDataAccessException e) {
                    throw new EntityNotFoundException("job not found",null,null);
                }
            }
        }.execute();
    }

    @Override
    public Layer getLayer(Current arg0) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Layer>() {
            public Layer throwOnlyIceExceptions() throws SpiIceException {
                try {
                    return whiteboard.getLayer(procDao.getCurrentLayerId(proc));
                } catch (org.springframework.dao.EmptyResultDataAccessException e) {
                    throw new EntityNotFoundException("layer not found",null,null);
                }
            }
        }.execute();
    }

    public void kill(final Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                jobManagerSupport.unbookProc(procDao.getVirtualProc(proc.getProcId()),
                        true, new Source(__current));
            }
        }.execute();
    }

    public void unbook(final boolean kill, final Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                procDao.unbookProc(proc);
                if (kill) {
                    jobManagerSupport.unbookProc(procDao.getVirtualProc(proc.getProcId()),
                            true, new Source(__current));
                }
            }
        }.execute();
    }

    @Override
    public boolean redirectToGroup(
            final GroupInterfacePrx proxy,
            final boolean kill,
            final Current __current) throws SpiIceException {

        return new SpiIceExceptionGenericTemplate<Boolean>() {
            public Boolean throwOnlyIceExceptions() throws SpiIceException {

            VirtualProc p = procDao.getVirtualProc(proc.getId());
            com.imageworks.spcue.Group g = groupManager.getGroup(
                    proxy.ice_getIdentity().name);
            return redirectManager.addRedirect(p, g, kill,
                    new Source(__current));
            }

        }.execute();
    }

    @Override
    public boolean redirectToJob(
            final JobInterfacePrx proxy,
            final boolean kill,
            final Current __current) throws SpiIceException {

        return new SpiIceExceptionGenericTemplate<Boolean>() {
            public Boolean throwOnlyIceExceptions() throws SpiIceException {
                VirtualProc p = procDao.getVirtualProc(proc.getId());
                com.imageworks.spcue.Job j =
                    jobManager.getJob(proxy.ice_getIdentity().name);
                return redirectManager.addRedirect(p, j, kill,
                        new Source(__current));
            }
        }.execute();
    }

    @Override
    public boolean clearRedirect(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Boolean>() {
            public Boolean throwOnlyIceExceptions() throws SpiIceException {
                procDao.setUnbookState(proc, false);
                return redirectManager.removeRedirect(proc);
            }
        }.execute();
    }

    public ProcDao getProcDao() {
        return procDao;
    }

    public void setProcDao(ProcDao procDao) {
        this.procDao = procDao;
    }

    public Whiteboard getWhiteboard() {
        return whiteboard;
    }

    public void setWhiteboard(Whiteboard whiteboard) {
        this.whiteboard = whiteboard;
    }

    public JobManagerSupport getJobManagerSupport() {
        return jobManagerSupport;
    }

    public void setJobManagerSupport(JobManagerSupport jobManagerSupport) {
        this.jobManagerSupport = jobManagerSupport;
    }

    public JobManager getJobManager() {
        return jobManager;
    }

    public void setJobManager(JobManager jobManager) {
        this.jobManager = jobManager;
    }

    public GroupManager getGroupManager() {
        return groupManager;
    }

    public void setGroupManager(GroupManager groupManager) {
        this.groupManager = groupManager;
    }

    public RedirectManager getRedirectManager() {
        return redirectManager;
    }

    public void setRedirectManager(RedirectManager redirectManager) {
        this.redirectManager = redirectManager;
    }
}

