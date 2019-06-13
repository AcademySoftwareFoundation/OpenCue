
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


package com.imageworks.spcue.dispatcher;

import java.util.ArrayList;
import java.util.List;

import org.apache.log4j.Logger;

import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.ProcInterface;
import com.imageworks.spcue.Redirect;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.GroupDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.ProcDao;
import com.imageworks.spcue.dao.criteria.ProcSearchFactory;
import com.imageworks.spcue.dao.criteria.ProcSearchInterface;
import com.imageworks.spcue.dispatcher.commands.DispatchBookHost;
import com.imageworks.spcue.grpc.host.ProcSearchCriteria;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobManagerSupport;
import com.imageworks.spcue.service.RedirectService;
import com.imageworks.spcue.util.CueExceptionUtil;
import com.imageworks.spcue.util.SqlUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.stereotype.Component;

@Component
public class RedirectManager {

    private static final Logger logger = Logger.getLogger(RedirectManager.class);

    @Autowired
    private JobDao jobDao;

    @Autowired
    private ProcDao procDao;

    @Autowired
    private GroupDao groupDao;

    @Autowired
    @Qualifier("dispatcher")
    private Dispatcher dispatcher;

    @Autowired
    private BookingQueue bookingQueue;

    @Autowired
    private HostManager hostManager;

    @Autowired
    private JobManagerSupport jobManagerSupport;

    @Autowired
    private DispatchSupport dispatchSupport;

    @Autowired
    private RedirectService redirectService;

    @Autowired
    private ProcSearchFactory procSearchFactory;

    public RedirectManager(RedirectService redirectService) {
        this.redirectService = redirectService;
    }

    /**
     * Delete all redirects that are past expiration age.
     *
     * @return count of redirects deleted
     */
    public int deleteExpired() {
        return redirectService.deleteExpired();
    }

    /**
     * Remove a redirect for a specific proc.
     *
     * @param proc
     */
    public boolean removeRedirect(ProcInterface proc) {
        procDao.setRedirectTarget(proc, null);
        return redirectService.remove(proc.getProcId()) != null;
    }

    /**
     * Return true if a redirect for a specific Proc
     * exists.  False if it does not.
     *
     * @param proc
     * @return
     */
    public boolean hasRedirect(ProcInterface proc) {
        return redirectService.containsKey(proc.getProcId());
    }

    /**
     * Redirects procs found by the ProcSearchCriteria
     * to the specified group.
     *
     * @param criteria
     * @param group
     * @param kill
     * @param source
     * @return
     */
    public List<VirtualProc> addRedirect(ProcSearchCriteria criteria,
                                         GroupInterface group, boolean kill, Source source) {

        List<GroupInterface> groups = new ArrayList<GroupInterface>(1);
        groups.add(group);

        ProcSearchInterface search = procSearchFactory.create(criteria);
        search.sortByBookedTime();
        search.notGroups(groups);

        List<VirtualProc> procs = hostManager.findBookedVirtualProcs(search);
        if (procs.size() == 0) {
            return procs;
        }

        for (VirtualProc proc: procs) {
            logger.info("Adding redirect from " + proc + " to group "
                    + group.getName());

            Redirect r = new Redirect(group);
            if (procDao.setRedirectTarget(proc, r)) {
                redirectService.put(proc.getProcId(), r);
            }
            else {
                procs.remove(proc);
            }
        }

        if (kill) {
            jobManagerSupport.kill(procs, source);
        }

        return procs;
    }

    /**
     * Redirects procs found by the proc search criteria to
     * an array of jobs.
     *
     * @param criteria
     * @param jobs
     * @param kill
     * @param source
     * @return
     */
    public List<VirtualProc> addRedirect(ProcSearchCriteria criteria,
                                         List<JobInterface> jobs, boolean kill, Source source) {
        int index = 0;

        ProcSearchInterface procSearch = procSearchFactory.create(criteria);
        procSearch.notJobs(jobs);
        List<VirtualProc> procs = hostManager.findBookedVirtualProcs(procSearch);
        if (procs.size() == 0) {
            return procs;
        }

        for (VirtualProc proc: procs) {
            if (index >= jobs.size()) {
                index = 0;
            }

            logger.info("Adding redirect from " + proc + " to job "
                    + jobs.get(index).getName());

            Redirect r = new Redirect(jobs.get(index));
            if (procDao.setRedirectTarget(proc, r)) {
                redirectService.put(proc.getProcId(), r);
                index++;
            }
            else {
                procs.remove(proc);
            }
        }
        if (kill) {
            jobManagerSupport.kill(procs, source);
        }

        return procs;
    }
    /**
     * Redirect a list of procs to the specified job. Using
     * redirect counters, the redirect only happens one
     * all procs have reported in.  This gives users the
     * ability to kill multiple frames and open up large
     * amounts of memory and cores.
     *
     * @param procs
     * @param job
     * @param source
     * @return true if the redirect succeeds.
     */
    public boolean addRedirect(List<VirtualProc> procs, JobInterface job,
            Source source) {

        String redirectGroupId = SqlUtil.genKeyRandom();

        for (VirtualProc proc: procs) {
            Redirect r = new Redirect(redirectGroupId, job);
            if (procDao.setRedirectTarget(proc, r)) {
                redirectService.put(proc.getProcId(), r);
            }
        }

        for (VirtualProc proc: procs) {
            jobManagerSupport.kill(proc, source);
        }

        return true;
    }

    /**
     * Redirect a proc to the specified job.
     *
     * @param proc
     * @param job
     * @param kill
     * @param source
     * @return true if the redirect succeeds.
     */
    public boolean addRedirect(VirtualProc proc, JobInterface job,
            boolean kill, Source source) {

        if (dispatchSupport.findNextDispatchFrames(
                job, proc, 1).size() < 1) {
            return false;
        }

        Redirect r = new Redirect(job);
        if (procDao.setRedirectTarget(proc, r)) {
            redirectService.put(proc.getProcId(), r);
            if (kill) {
                jobManagerSupport.kill(proc, source);
            }
            return true;
        }

        return false;
    }

    /**
     * Redirect a proc to the specified group.
     *
     * @param proc
     * @param group
     * @param kill
     * @param source
     * @return true if the redirect succeeds.
     */
    public boolean addRedirect(VirtualProc proc, GroupInterface group,
            boolean kill, Source source) {

        // Test a dispatch
        DispatchHost host = hostManager.getDispatchHost(proc.getHostId());
        host.idleCores = proc.coresReserved;
        host.idleMemory = proc.memoryReserved;

        if (dispatchSupport.findDispatchJobs(host, group).size() < 1) {
            logger.info("Failed to find a pending job in group: " + group.getName());
            return false;
        }

        Redirect r = new Redirect(group);
        if (procDao.setRedirectTarget(proc, r)) {
            redirectService.put(proc.getProcId(), r);
            if (kill) {
                jobManagerSupport.kill(proc, source);
            }
            return true;
        }

        return false;
    }

    /**
     * Redirect the specified proc to its redirect
     * destination;
     *
     * @param proc
     * @return
     */
    public boolean redirect(VirtualProc proc) {

        try {

            Redirect r = redirectService.remove(proc.getProcId());
            if (r == null) {
                logger.info("Failed to find redirect for proc " + proc);
                return false;
            }

            int other_redirects_with_same_group =
                redirectService.countRedirectsWithGroup(r.getGroupId());

            if (other_redirects_with_same_group > 0) {
                logger.warn("Redirect waiting on " + other_redirects_with_same_group + " more frames.");
                return false;
            }

            /*
             * The proc must be unbooked before its resources can be
             * redirected.
             */
            dispatchSupport.unbookProc(proc, "is being redirected");

            /*
             * Set the free cores and memory to the exact amount
             * on the proc we just unbooked so we don't stomp on
             * other redirects.
             */
            DispatchHost host = hostManager.getDispatchHost(
                    proc.getHostId());

            switch (r.getType()) {

                case JOB_REDIRECT:
                    logger.info("attempting a job redirect to " +
                            r.getDestinationId());
                    JobInterface job = jobDao.getJob(r.getDestinationId());
                    logger.info("redirecting proc " + proc
                            + " to job " + job.getName());

                    if (dispatcher.isTestMode()) {
                        dispatcher.dispatchHost(host, job);
                    }
                    else {
                        bookingQueue.execute(new
                                DispatchBookHost(host, job, dispatcher));
                    }
                    return true;

                case GROUP_REDIRECT:
                    logger.info("attempting a group redirect to " +
                            r.getDestinationId());
                    GroupInterface group = groupDao.getGroup(r.getDestinationId());
                    logger.info("redirecting group " + proc +
                            " to job " + group.getName());

                    if (dispatcher.isTestMode()) {
                        dispatcher.dispatchHost(host, group);
                    }
                    else {
                        bookingQueue.execute(new DispatchBookHost(host,
                                group, dispatcher));
                    }
                    return true;

                default:
                    logger.info("redirect failed, invalid redirect type: "
                            + r.getType());
                    return false;
            }

        }
        catch (Exception e) {
            /*
             * If anything fails the redirect fails, so just
             * return false after logging.
             */
            CueExceptionUtil.logStackTrace("redirect failed", e);
            return false;
        }
    }

    public JobDao getJobDao() {
        return jobDao;
    }

    public void setJobDao(JobDao jobDao) {
        this.jobDao = jobDao;
    }

    public GroupDao getGroupDao() {
        return groupDao;
    }

    public void setGroupDao(GroupDao groupDao) {
        this.groupDao = groupDao;
    }

    public Dispatcher getDispatcher() {
        return dispatcher;
    }

    public void setDispatcher(Dispatcher dispatcher) {
        this.dispatcher = dispatcher;
    }

    public BookingQueue getBookingQueue() {
        return bookingQueue;
    }

    public void setBookingQueue(BookingQueue bookingQueue) {
        this.bookingQueue = bookingQueue;
    }

    public HostManager getHostManager() {
        return hostManager;
    }

    public void setHostManager(HostManager hostManager) {
        this.hostManager = hostManager;
    }

    public JobManagerSupport getJobManagerSupport() {
        return jobManagerSupport;
    }

    public void setJobManagerSupport(JobManagerSupport jobManagerSupport) {
        this.jobManagerSupport = jobManagerSupport;
    }

    public DispatchSupport getDispatchSupport() {
        return dispatchSupport;
    }

    public void setDispatchSupport(DispatchSupport dispatchSupport) {
        this.dispatchSupport = dispatchSupport;
    }

    public ProcDao getProcDao() {
        return procDao;
    }

    public void setProcDao(ProcDao procDao) {
        this.procDao = procDao;
    }

    public ProcSearchFactory getProcSearchFactory() {
        return procSearchFactory;
    }

    public void setProcSearchFactory(ProcSearchFactory procSearchFactory) {
        this.procSearchFactory = procSearchFactory;
    }
}

