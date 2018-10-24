
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

import Ice.Current;
import com.google.common.collect.Sets;
import com.imageworks.common.SpiIce.SpiIceException;
import com.imageworks.common.spring.remoting.IceServer;
import com.imageworks.common.spring.remoting.SpiIceExceptionGenericTemplate;
import com.imageworks.common.spring.remoting.SpiIceExceptionMinimalTemplate;
import com.imageworks.spcue.BuildableJob;
import com.imageworks.spcue.CueClientIce.Allocation;
import com.imageworks.spcue.CueClientIce.Depend;
import com.imageworks.spcue.CueClientIce.Filter;
import com.imageworks.spcue.CueClientIce.Frame;
import com.imageworks.spcue.CueClientIce.FrameSearchCriteria;
import com.imageworks.spcue.CueClientIce.Group;
import com.imageworks.spcue.CueClientIce.GroupInterfacePrx;
import com.imageworks.spcue.CueClientIce.Host;
import com.imageworks.spcue.CueClientIce.HostSearchCriteria;
import com.imageworks.spcue.CueClientIce.Job;
import com.imageworks.spcue.CueClientIce.JobInterfacePrx;
import com.imageworks.spcue.CueClientIce.JobSearchCriteria;
import com.imageworks.spcue.CueClientIce.Layer;
import com.imageworks.spcue.CueClientIce.NestedHost;
import com.imageworks.spcue.CueClientIce.Owner;
import com.imageworks.spcue.CueClientIce.Proc;
import com.imageworks.spcue.CueClientIce.ProcSearchCriteria;
import com.imageworks.spcue.CueClientIce.Service;
import com.imageworks.spcue.CueClientIce.ServiceData;
import com.imageworks.spcue.CueClientIce.Show;
import com.imageworks.spcue.CueClientIce.Subscription;
import com.imageworks.spcue.CueClientIce.SubscriptionData;
import com.imageworks.spcue.CueClientIce.SystemStats;
import com.imageworks.spcue.CueClientIce._CueStaticDisp;
import com.imageworks.spcue.CueIce.CueIceException;
import com.imageworks.spcue.CueIce.EntityCreationErrorException;
import com.imageworks.spcue.CueIce.EntityNotFoundException;
import com.imageworks.spcue.ShowDetail;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.criteria.Direction;
import com.imageworks.spcue.dao.criteria.FrameSearch;
import com.imageworks.spcue.dao.criteria.HostSearch;
import com.imageworks.spcue.dao.criteria.JobSearch;
import com.imageworks.spcue.dao.criteria.ProcSearch;
import com.imageworks.spcue.dao.criteria.Sort;
import com.imageworks.spcue.dispatcher.BookingQueue;
import com.imageworks.spcue.dispatcher.DispatchQueue;
import com.imageworks.spcue.dispatcher.DispatchSupport;
import com.imageworks.spcue.dispatcher.HostReportQueue;
import com.imageworks.spcue.dispatcher.RedirectManager;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.GroupManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.JobManagerSupport;
import com.imageworks.spcue.service.JobSpec;
import com.imageworks.spcue.service.ServiceManager;
import com.imageworks.spcue.service.Whiteboard;
import com.imageworks.spcue.util.Convert;
import com.imageworks.spcue.util.CueUtil;
import org.apache.commons.lang.NotImplementedException;
import org.springframework.dao.EmptyResultDataAccessException;

import java.util.ArrayList;
import java.util.List;

public class CueStaticI extends _CueStaticDisp {

    private AdminManager adminManager;
    private Whiteboard whiteboard;
    private DispatchQueue manageQueue;
    private DispatchQueue dispatchQueue;
    private HostReportQueue reportQueue;
    private BookingQueue bookingQueue;
    private DispatchSupport dispatchSupport;
    private JobManagerSupport jobManagerSupport;
    private JobLauncher jobLauncher;
    private GroupManager groupManager;
    private JobManager jobManager;
    private RedirectManager redirectManager;
    private ServiceManager serviceManager;

    @Override
    public Ice.DispatchStatus __dispatch(IceInternal.Incoming in,
                                         Current current) {
        ServantInterceptor.__dispatch(this, in, current);
        return super.__dispatch(in, current);
    }

    @Override
    public List<Job> launchSpecAndWait(final String payload, Current arg1)
            throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Job>>() {
            public List<Job> throwOnlyIceExceptions() throws EntityCreationErrorException  {
                JobSpec spec = jobLauncher.parse(payload);
                jobLauncher.launch(spec);
                JobSearchCriteria r = JobSearch.criteriaFactory();
                for (BuildableJob job: spec.getJobs()) {
                    r.ids.add(job.detail.id);
                }
                return whiteboard.getJobs(new JobSearch(r));
            }
        }.execute();
    }

    @Override
    public List<String> launchSpec(final String payload, Current arg1)
            throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<String>>() {
            public List<String> throwOnlyIceExceptions() throws EntityCreationErrorException  {
                JobSpec spec = jobLauncher.parse(payload);
                List<String> result = new ArrayList<String>(8);
                for (BuildableJob j: spec.getJobs()) {
                    result.add(j.detail.name);
                }
                jobLauncher.queueAndLaunch(spec);
                return result;
            }
        }.execute();
    }

    @Override
    public SystemStats getSystemStats(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<SystemStats>() {
            public SystemStats throwOnlyIceExceptions()  {

                SystemStats s = new SystemStats();

                s.dispatchThreads = dispatchQueue.getActiveThreadCount();
                s.dispatchWaiting = dispatchQueue.getWaitingCount();
                s.dispatchRemainingCapacity = dispatchQueue.getRemainingCapacity();
                s.dispatchExecuted = dispatchQueue.getTotalDispatched();
                s.dispatchRejected = dispatchQueue.getTotalRejected();

                s.manageThreads = manageQueue.getActiveThreadCount();
                s.manageWaiting = manageQueue.getWaitingCount();
                s.manageRemainingCapacity = manageQueue.getRemainingCapacity();
                s.manageExecuted = manageQueue.getTotalDispatched();
                s.manageRejected = manageQueue.getTotalRejected();

                s.reportThreads = reportQueue.getActiveCount();
                s.reportWaiting = reportQueue.getQueue().size();
                s.reportRemainingCapacity = reportQueue.getQueue().remainingCapacity();
                s.reportExecuted = reportQueue.getTaskCount();
                s.reportRejected = reportQueue.getRejectedTaskCount();

                s.bookingWaiting = bookingQueue.getQueue().size();
                s.bookingRemainingCapacity = bookingQueue.getQueue().remainingCapacity();
                s.bookingThreads = bookingQueue.getActiveCount();
                s.bookingExecuted = bookingQueue.getCompletedTaskCount();
                s.bookingRejected = bookingQueue.getRejectedTaskCount();
                s.bookingSleepMillis = bookingQueue.sleepTime();

                s.hostBalanceSuccess = DispatchSupport.balanceSuccess.get();
                s.hostBalanceFailed = DispatchSupport.balanceFailed.get();
                s.killedOffenderProcs = DispatchSupport.killedOffenderProcs.get();
                s.killedOomProcs = DispatchSupport.killedOomProcs.get();
                s.clearedProcs = DispatchSupport.clearedProcs.get();
                s.bookingRetries = DispatchSupport.bookingRetries.get();
                s.bookingErrors = DispatchSupport.bookingErrors.get();
                s.bookedProcs =  DispatchSupport.bookedProcs.get();

                s.reqForData = IceServer.dataRequests.get();
                s.reqForFunction = IceServer.rpcRequests.get();
                s.reqErrors = IceServer.errors.get();

                s.unbookedProcs = DispatchSupport.unbookedProcs.get();
                s.pickedUpCores = DispatchSupport.pickedUpCoresCount.get();
                s.strandedCores = DispatchSupport.strandedCoresCount.get();

                return s;
            }
        }.execute();
    }

    @Override
    public Show createShow(final String name, Current __current)
            throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Show>() {
            public Show throwOnlyIceExceptions() throws EntityCreationErrorException  {
                if (adminManager.showExists(name)) {
                    throw new EntityCreationErrorException("the show" + name +
                            " already exists", null,  null);
                }
                try {
                    ShowDetail show = new ShowDetail();
                    show.name = name;
                    adminManager.createShow(show);
                    return whiteboard.getShow(show.getShowId());
                } catch (Exception e) {
                    throw new EntityCreationErrorException("show could not be created",
                            null, null);
                }
            }
        }.execute();
    }

    @Override
    public List<Allocation> getAllocations(Current __current)
            throws SpiIceException {
        throw new SpiIceException(new NotImplementedException());
    }

    @Override
    public List<Show> getShows(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Show>>() {
            public List<Show> throwOnlyIceExceptions() {
                return whiteboard.getShows();
            }
        }.execute();
    }

    @Override
    public Allocation findAllocation(final String name, Current __current) throws SpiIceException {
        throw new SpiIceException(new NotImplementedException());
    }

    @Override
    public Allocation getAllocation(final String id, Current arg1)
            throws SpiIceException {
        throw new SpiIceException(new NotImplementedException());
    }

    @Override
    public void addDepartmentName(final String name, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                adminManager.createDepartment(name);
            }
        }.execute();
    }

    @Override
    public List<String> getDepartmentNames(Current arg0) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<String>>() {
            public List<String> throwOnlyIceExceptions() {
                return whiteboard.getDepartmentNames();
            }
        }.execute();
    }

    @Override
    public void removeDepartmentName(final String name, Current arg1) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                adminManager.removeDepartment(adminManager.findDepartment(name));
            }
        }.execute();
    }

    @Override
    public Job findJob(final String name, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Job>() {
            public Job throwOnlyIceExceptions() throws SpiIceException {
                try {
                    return whiteboard.findJob(name);
                } catch (org.springframework.dao.EmptyResultDataAccessException e) {
                    throw new EntityNotFoundException("job not found",null,null);
                }
            }
        }.execute();
    }

    @Override
    public Job getJob(final String id, Current arg1) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Job>() {
            public Job throwOnlyIceExceptions() throws SpiIceException {
                try {
                    return whiteboard.getJob(id);
                } catch (org.springframework.dao.EmptyResultDataAccessException e) {
                    throw new EntityNotFoundException("job not found",null,null);
                }
            }
        }.execute();
    }

    @Override
    public List<Job> getJobs(final JobSearchCriteria r, Current arg1)
            throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Job>>() {
            public List<Job> throwOnlyIceExceptions() throws SpiIceException {
                return whiteboard.getJobs(new JobSearch(r));
            }
        }.execute();
    }

    @Override
    public List<String> getJobNames(final JobSearchCriteria r,
            Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<String>>() {
            public List<String> throwOnlyIceExceptions() throws SpiIceException {
                return whiteboard.getJobNames(new JobSearch(r));
            }
        }.execute();
    }

    @Override
    public List<NestedHost> getHostWhiteboard(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<NestedHost>>() {
            public List<NestedHost> throwOnlyIceExceptions() throws SpiIceException {
                return whiteboard.getHostWhiteboard();
            }
        }.execute();
    }

    @Override
    public Host findHost(final String name, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Host>() {
            public Host throwOnlyIceExceptions() throws SpiIceException {
                try {
                    return whiteboard.findHost(name);
                } catch (org.springframework.dao.EmptyResultDataAccessException e) {
                    throw new EntityNotFoundException("host not found",null,null);
                }
            }
        }.execute();
    }

    @Override
    public Host getHost(final String id, Current arg1) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Host>() {
            public Host throwOnlyIceExceptions() throws SpiIceException {
                try {
                    return whiteboard.getHost(id);
                } catch (org.springframework.dao.EmptyResultDataAccessException e) {
                    throw new EntityNotFoundException("host not found",null,null);
                }
            }
        }.execute();
    }

    @Override
    public Group getGroup(final String groupId, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Group>() {
            public Group throwOnlyIceExceptions() throws SpiIceException {
                try {
                    return whiteboard.getGroup(groupId);
                } catch (org.springframework.dao.EmptyResultDataAccessException e) {
                    throw new EntityNotFoundException("group not found",null,null);
                }
            }
        }.execute();
    }

    @Override
    public Show findShow(final String name,  Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Show>() {
            public Show throwOnlyIceExceptions() throws SpiIceException {
                try {
                    return whiteboard.findShow(name);
                } catch (org.springframework.dao.EmptyResultDataAccessException e) {
                    throw new EntityNotFoundException("show not found",null,null);
                }
            }
        }.execute();
    }

    @Override
    public Frame findFrame(final String job, final String layer, final int frame, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Frame>() {
            public Frame throwOnlyIceExceptions() throws SpiIceException {
                try {
                    return whiteboard.findFrame(job, layer, frame);
                } catch (org.springframework.dao.EmptyResultDataAccessException e) {
                    throw new EntityNotFoundException("frame not found",null,null);
                }
            }
        }.execute();
    }

    @Override
    public Frame getFrame(final String id, Current arg1) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Frame>() {
            public Frame throwOnlyIceExceptions() throws SpiIceException {
                try {
                    return whiteboard.getFrame(id);
                } catch (org.springframework.dao.EmptyResultDataAccessException e) {
                    throw new EntityNotFoundException("frame not found",null,null);
                }
            }
        }.execute();
    }

    @Override
    public List<Frame> getFrames(final String name, final FrameSearchCriteria arg1,
            Current arg2) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Frame>>() {
            public List<Frame> throwOnlyIceExceptions() throws SpiIceException {
                try {
                    return whiteboard.getFrames(new FrameSearch(jobManagerSupport.
                            getJobManager().findJob(name) ,arg1));
                } catch (org.springframework.dao.EmptyResultDataAccessException e) {
                    throw new EntityNotFoundException("job not found or is not pending",null,null);
                }
            }
        }.execute();
    }

    @Override
    public Layer findLayer(final String job, final String layer, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Layer>() {
            public Layer throwOnlyIceExceptions() throws SpiIceException {
                try {
                    return whiteboard.findLayer(job, layer);
                } catch (org.springframework.dao.EmptyResultDataAccessException e) {
                    throw new EntityNotFoundException("layer not found",null,null);
                }
            }
        }.execute();
    }

    @Override
    public Layer getLayer(final String id, Current arg1) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Layer>() {
            public Layer throwOnlyIceExceptions() throws SpiIceException {
                try {
                    return whiteboard.getLayer(id);
                } catch (org.springframework.dao.EmptyResultDataAccessException e) {
                    throw new EntityNotFoundException("layer not found",null,null);
                }
            }
        }.execute();
    }

    @Override
    public Group findGroup(final String show, final String name, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Group>() {
            public Group throwOnlyIceExceptions() throws SpiIceException {
                try {
                    return whiteboard.findGroup(show, name);
                } catch (org.springframework.dao.EmptyResultDataAccessException e) {
                    throw new EntityNotFoundException("group not found", null, null);
                }
            }
        }.execute();
    }

    @Override
    public boolean isJobPending(final String name, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Boolean>() {
            public Boolean throwOnlyIceExceptions() throws SpiIceException {
                return whiteboard.isJobPending(name);
            }
        }.execute();
    }

    @Override
    public List<Host> getHosts(final HostSearchCriteria criteria, Current arg1)
            throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Host>>() {
            public List<Host> throwOnlyIceExceptions() throws SpiIceException {
                return whiteboard.getHosts(new HostSearch(criteria));
            }
        }.execute();

    }

    @Override
    public Depend getDepend(final String id, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Depend>() {
            public Depend throwOnlyIceExceptions() throws SpiIceException {
                try {
                    return whiteboard.getDepend(id);
                } catch (org.springframework.dao.EmptyResultDataAccessException e) {
                    throw new EntityNotFoundException("layer not found",null,null);
                }
            }
        }.execute();
    }

    @Override
    public Filter findFilter(final String show, final String name, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Filter>() {
            public Filter throwOnlyIceExceptions() throws SpiIceException {
                try {
                    return whiteboard.findFilter(show, name);
                } catch (org.springframework.dao.EmptyResultDataAccessException e) {
                    throw new EntityNotFoundException("filter not found",null,null);
                }
            }
        }.execute();
    }

    @Override
    public Subscription findSubscription(final String name, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Subscription>() {
            public Subscription throwOnlyIceExceptions() throws SpiIceException {
                try {
                    String[] parts = name.split("\\.", 3);
                    if (parts.length != 3) {
                        throw new CueIceException(
                                "Subscription names must be in the form of alloc.show",
                                new String[] {}, null);
                    }
                    // TODO: (gdenton) Switch to whiteboard method once grpc switch is complete
                    // This is a temporary conversion of grpc obj to ice obj
                    //return whiteboard.findSubscription(parts[2], parts[0]+"."+parts[1]);
                    com.imageworks.spcue.grpc.subscription.Subscription grpcSubscription =
                            whiteboard.findSubscription(parts[2], parts[0]+"."+parts[1]);
                    Subscription iceSubscription = new Subscription();
                    iceSubscription.data = new SubscriptionData();
                    iceSubscription.data.burst = Convert.coreUnitsToCores(grpcSubscription.getBurst());
                    iceSubscription.data.name = grpcSubscription.getName();
                    iceSubscription.data.reservedCores = Convert.coreUnitsToCores(grpcSubscription.getReservedCores());
                    iceSubscription.data.size = Convert.coreUnitsToCores(grpcSubscription.getSize());
                    iceSubscription.data.allocationName = grpcSubscription.getAllocationName();
                    iceSubscription.data.showName = grpcSubscription.getShowName();
                    iceSubscription.data.facility = grpcSubscription.getFacility();
                    return iceSubscription;

                } catch (org.springframework.dao.EmptyResultDataAccessException e) {
                    throw new EntityNotFoundException(
                            "A subscrition to " + name + " was not found.", null, null);
                }
            }
        }.execute();
    }

    @Override
    public Subscription getSubscription(final String id, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Subscription>() {
            public Subscription throwOnlyIceExceptions() {
                // TODO: (gdenton) Switch to whiteboard method once grpc switch is complete
                // This is a temporary conversion of grpc obj to ice obj
                //return whiteboard.getSubscription(id);
                com.imageworks.spcue.grpc.subscription.Subscription grpcSubscription = whiteboard.getSubscription(id);
                Subscription iceSubscription = new Subscription();
                iceSubscription.data = new SubscriptionData();
                iceSubscription.data.burst = Convert.coreUnitsToCores(grpcSubscription.getBurst());
                iceSubscription.data.name = grpcSubscription.getName();
                iceSubscription.data.reservedCores = Convert.coreUnitsToCores(grpcSubscription.getReservedCores());
                iceSubscription.data.size = Convert.coreUnitsToCores(grpcSubscription.getSize());
                iceSubscription.data.allocationName = grpcSubscription.getAllocationName();
                iceSubscription.data.showName = grpcSubscription.getShowName();
                iceSubscription.data.facility = grpcSubscription.getFacility();
                return iceSubscription;
            }
        }.execute();
    }

    @Override
    public List<Proc> getProcs(final ProcSearchCriteria r, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Proc>>() {
            public List<Proc> throwOnlyIceExceptions() {
                return whiteboard.getProcs(new ProcSearch(r));
            }
        }.execute();
    }

    @Override
    public int unbookProcs(final ProcSearchCriteria arg0, final boolean kill, final Current __current)
            throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Integer>() {
            public Integer throwOnlyIceExceptions() {
                return jobManagerSupport.unbookProcs(
                        new ProcSearch(arg0,
                                new Sort("proc.ts_booked",Direction.ASC)), kill,
                                new Source(__current));
            }
        }.execute();
    }

    @Override
    public int unbookToGroup(final ProcSearchCriteria search, final GroupInterfacePrx group,
            final boolean kill, final Current __current) throws SpiIceException {

        return new SpiIceExceptionGenericTemplate<Integer>() {
            public Integer throwOnlyIceExceptions() {

                if (search.maxResults.length == 0) {
                    throw new RuntimeException(
                            "You must specify the number of procs to unbook " +
                            "within the ProcSearchCriteria.");
                }

                com.imageworks.spcue.Group g =
                    groupManager.getGroup(group.ice_getIdentity().name);

                List<VirtualProc> procs = redirectManager.addRedirect(search,
                        g, kill, new Source(__current));
                return procs.size();
            }
        }.execute();
    }

    @Override
    public int unbookToJob(final ProcSearchCriteria search,
            final List<JobInterfacePrx> proxies, final boolean kill,
            final Current __current) throws SpiIceException {

        return new SpiIceExceptionGenericTemplate<Integer>() {
            public Integer throwOnlyIceExceptions() {

                if (search.maxResults.length == 0) {
                    throw new RuntimeException(
                            "You must specify the number of procs to unbook " +
                            "within the ProcSearchCriteria.");
                }

                List<com.imageworks.spcue.Job> jobs =
                    new ArrayList<com.imageworks.spcue.Job>(proxies.size());

                for (JobInterfacePrx proxy: proxies) {
                    try {
                        jobs.add(jobManager.getJob(
                                proxy.ice_getIdentity().name));
                    }
                    catch (EmptyResultDataAccessException e) {
                        // just eat it, just eat it.
                        // Open up your mouth and feed it.
                        // Have a banana. Have a whole bunch.
                        // It doesn't matter, when you had lunch.
                        // just eat it, just eat it
                        // get yourself and egg and beat it
                    }
                }

                if (jobs.size() == 0) {
                    return 0;
                }

                List<VirtualProc> procs = redirectManager.addRedirect(search,
                        jobs, kill, new Source(__current));

                return procs.size();
            }
        }.execute();
    }

    @Override
    public Owner getOwner(final String id, Current arg1) throws SpiIceException {
        return new CueIceExceptionTemplate<Owner>() {
            public Owner throwOnlyIceExceptions() {
                return whiteboard.getOwner(id);
            }
        }.execute();
    }

    @Override
    public List<Show> getActiveShows(Current arg0) throws SpiIceException {
        return new CueIceExceptionTemplate<List<Show>>() {
            public List<Show> throwOnlyIceExceptions() {
                return whiteboard.getActiveShows();
            }
        }.execute();
    }

    @Override
    public Service createService(final ServiceData srv, Current arg1)
            throws SpiIceException {

        return new CueIceExceptionTemplate<Service>() {
            public Service throwOnlyIceExceptions() {
                com.imageworks.spcue.Service service =
                    new com.imageworks.spcue.Service();
                service.name = srv.name;
                service.minCores = srv.minCores;
                service.minMemory = srv.minMemory;
                service.minGpu = srv.minGpu;
                service.tags = Sets.newLinkedHashSet(srv.tags);
                service.threadable = srv.threadable;
                serviceManager.createService(service);
                return whiteboard.getService(service.getId());
            }
        }.execute();
    }

    @Override
    public List<Service> getDefaultServices(Current arg0)
            throws SpiIceException {
        return new CueIceExceptionTemplate<List<Service>>() {
            public List<Service> throwOnlyIceExceptions() {
                return whiteboard.getDefaultServices();
            }
        }.execute();
    }

    @Override
    public Service getService(final String id, Current arg1) throws SpiIceException {
        return new CueIceExceptionTemplate<Service>() {
            public Service throwOnlyIceExceptions() {
                return whiteboard.getService(id);
            }
        }.execute();
    }

    public AdminManager getAdminManager() {
        return adminManager;
    }

    public void setAdminManager(AdminManager adminManager) {
        this.adminManager = adminManager;
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

    public void setManageQueue(DispatchQueue manageQueue) {
        this.manageQueue = manageQueue;
    }

    public DispatchQueue getDispatchQueue() {
        return dispatchQueue;
    }

    public void setDispatchQueue(DispatchQueue dispatchQueue) {
        this.dispatchQueue = dispatchQueue;
    }

    public HostReportQueue getReportQueue() {
        return reportQueue;
    }

    public void setReportQueue(HostReportQueue reportQueue) {
        this.reportQueue = reportQueue;
    }

    public BookingQueue getBookingQueue() {
        return bookingQueue;
    }

    public void setBookingQueue(BookingQueue bookingQueue) {
        this.bookingQueue = bookingQueue;
    }

    public DispatchSupport getDispatchSupport() {
        return dispatchSupport;
    }

    public void setDispatchSupport(DispatchSupport dispatchSupport) {
        this.dispatchSupport = dispatchSupport;
    }

    public JobManagerSupport getJobManagerSupport() {
        return jobManagerSupport;
    }

    public void setJobManagerSupport(JobManagerSupport jobManagerSupport) {
        this.jobManagerSupport = jobManagerSupport;
    }

    public RedirectManager getRedirectManager() {
        return redirectManager;
    }

    public void setRedirectManager(RedirectManager redirectManager) {
        this.redirectManager = redirectManager;
    }

    public GroupManager getGroupManager() {
        return groupManager;
    }

    public void setGroupManager(GroupManager groupManager) {
        this.groupManager = groupManager;
    }

    public JobManager getJobManager() {
        return jobManager;
    }

    public void setJobManager(JobManager jobManager) {
        this.jobManager = jobManager;
    }

    public JobLauncher getJobLauncher() {
        return jobLauncher;
    }

    public void setJobLauncher(JobLauncher jobLauncher) {
        this.jobLauncher = jobLauncher;
    }

    public ServiceManager getServiceManager() {
        return serviceManager;
    }

    public void setServiceManager(ServiceManager serviceManager) {
        this.serviceManager = serviceManager;
    }
}

