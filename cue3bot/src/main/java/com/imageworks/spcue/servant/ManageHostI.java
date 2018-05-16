
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

import com.imageworks.common.SpiIce.SpiIceException;
import com.imageworks.common.spring.remoting.SpiIceExceptionGenericTemplate;
import com.imageworks.common.spring.remoting.SpiIceExceptionMinimalTemplate;
import com.imageworks.spcue.CommentDetail;

import com.imageworks.spcue.Host;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.CueClientIce.AllocationInterfacePrx;
import com.imageworks.spcue.CueClientIce.Comment;
import com.imageworks.spcue.CueClientIce.CommentData;
import com.imageworks.spcue.CueClientIce.JobInterfacePrx;
import com.imageworks.spcue.CueClientIce.Owner;
import com.imageworks.spcue.CueClientIce.Proc;
import com.imageworks.spcue.CueClientIce.Deed;
import com.imageworks.spcue.CueClientIce.ProcInterfacePrx;
import com.imageworks.spcue.CueClientIce.RenderPartition;
import com.imageworks.spcue.CueClientIce._HostInterfaceDisp;
import com.imageworks.spcue.CueIce.HardwareState;
import com.imageworks.spcue.CueIce.LockState;
import com.imageworks.spcue.CueIce.ThreadMode;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dispatcher.RedirectManager;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.CommentManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.Whiteboard;

public class ManageHostI extends _HostInterfaceDisp implements InitializingBean {

    private final String id;
    private Host host;
    private HostManager hostManager;
    private HostDao hostDao;
    private AdminManager adminManager;
    private CommentManager commentManager;
    private RedirectManager redirectManager;
    private JobManager jobManager;
    private Whiteboard whiteboard;

    public ManageHostI(Ice.Identity i) {
        this.id = i.name;
    }

    @Override
    public Ice.DispatchStatus __dispatch(IceInternal.Incoming in,
                                         Current current) {
        ServantInterceptor.__dispatch(this, in, current);
        return super.__dispatch(in, current);
    }

    public void afterPropertiesSet() throws Exception {
        host = hostManager.getHost(id);
    }

    public void lock(final Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                hostManager.setHostLock(host, LockState.Locked, new Source(__current));
            }
        }.execute();
    }

    public void unlock(final Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                hostManager.setHostLock(host, LockState.Open, new Source(__current));
            }
        }.execute();
    }

    public void rebootWhenIdle(Current __current)
            throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                hostManager.rebootWhenIdle(host);
            }
        }.execute();
    }

    public void delete(Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                hostManager.deleteHost(host);
            }
        }.execute();
    }

    public void reboot(Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                hostManager.rebootNow(host);
            }
        }.execute();
    }

    public void setAllocation(final AllocationInterfacePrx proxy, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                hostManager.setAllocation(host,
                        adminManager.getAllocationDetail(proxy.ice_getIdentity().name));
            }
        }.execute();
    }

    public void addTags(final String[] tags, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                hostManager.addTags(host, tags);
            }
        }.execute();
    }

    public void removeTags(final String[] tags, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                hostManager.removeTags(host, tags);
            }
        }.execute();
    }

    public void renameTag(final String oldTag, final String newTag, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                hostManager.renameTag(host, oldTag, newTag);
            }
        }.execute();
    }

    @Override
    public void addComment(final CommentData newComment, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                CommentDetail c = new CommentDetail();
                c.message = newComment.message;
                c.subject = newComment.subject;
                c.user = newComment.user;
                c.timestamp = null;
                commentManager.addComment(host, c);
            }
        }.execute();
    }

    @Override
    public List<Comment> getComments(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Comment>>(){
            public List<Comment> throwOnlyIceExceptions() {
                return whiteboard.getComments(host);
            }
        }.execute();
    }


    @Override
    public List<Proc> getProcs(Current arg0) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Proc>>(){
            public List<Proc> throwOnlyIceExceptions() {
                return whiteboard.getProcs(host);
            }
        }.execute();
    }

    @Override
    public void setThreadMode(final ThreadMode mode, Current arg1)
            throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                hostDao.updateThreadMode(host, mode);
            }
        }.execute();
    }

    @Override
    public void setHardwareState(final HardwareState state, Current __curent)
            throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                hostDao.updateHostState(host, state);
            }
        }.execute();
    }

    @Override
    public Owner getOwner(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Owner>(){
            public Owner throwOnlyIceExceptions() {
                return whiteboard.getOwner(host);
            }
        }.execute();
    }

    @Override
    public Deed getDeed(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Deed>(){
            public Deed throwOnlyIceExceptions() {
                return whiteboard.getDeed(host);
            }
        }.execute();
    }

    @Override
    public List<RenderPartition> getRenderPartitions(Current __current)
            throws SpiIceException {
        return new CueIceExceptionTemplate<List<RenderPartition>>() {
            public List<RenderPartition> throwOnlyIceExceptions()  {
                return whiteboard.getRenderPartitions(host);
            }
        }.execute();
    }

    @Override
    public boolean redirectToJob(final List<ProcInterfacePrx> procs,
            final JobInterfacePrx job, final Current __current)
            throws SpiIceException {

        return new CueIceExceptionTemplate<Boolean>() {
            public Boolean throwOnlyIceExceptions()  {
                List<VirtualProc> virtualProcs = new ArrayList<VirtualProc>();
                for (ProcInterfacePrx proxy: procs) {
                    virtualProcs.add(hostManager.getVirtualProc(
                            proxy.ice_getIdentity().name));
                }

                return redirectManager.addRedirect(virtualProcs,
                        jobManager.getJob(job.ice_getIdentity().name),
                        new Source(__current));
            }
        }.execute();
    }

    @Override
    public void setOs(final String arg0, Current arg1) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                hostDao.updateHostOs(host, arg0);
            }
        }.execute();
    }

    public HostManager getHostManager() {
        return hostManager;
    }

    public void setHostManager(HostManager hostManager) {
        this.hostManager = hostManager;
    }

    public AdminManager getAdminManager() {
        return adminManager;
    }

    public void setAdminManager(AdminManager adminManager) {
        this.adminManager = adminManager;
    }

    public CommentManager getCommentManager() {
        return commentManager;
    }

    public void setCommentManager(CommentManager commentManager) {
        this.commentManager = commentManager;
    }

    public Whiteboard getWhiteboard() {
        return whiteboard;
    }

    public void setWhiteboard(Whiteboard whiteboard) {
        this.whiteboard = whiteboard;
    }

    public HostDao getHostDao() {
        return hostDao;
    }

    public void setHostDao(HostDao hostDao) {
        this.hostDao = hostDao;
    }

    public RedirectManager getRedirectManager() {
        return redirectManager;
    }

    public void setRedirectManager(RedirectManager redirectManager) {
        this.redirectManager = redirectManager;
    }

    public JobManager getJobManager() {
        return jobManager;
    }

    public void setJobManager(JobManager jobManager) {
        this.jobManager = jobManager;
    }
}

