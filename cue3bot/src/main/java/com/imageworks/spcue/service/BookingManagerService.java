
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



package com.imageworks.spcue.service;

import java.util.List;

import org.apache.log4j.Logger;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.CueIce.JobState;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.Frame;
import com.imageworks.spcue.Host;
import com.imageworks.spcue.Job;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.Layer;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.BookingDao;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.ProcDao;
import com.imageworks.spcue.dispatcher.BookingQueue;
import com.imageworks.spcue.dispatcher.Dispatcher;


@Transactional
public class BookingManagerService implements BookingManager {

    @SuppressWarnings("unused")
    private static final Logger logger =
        Logger.getLogger(BookingManagerService.class);

    private BookingQueue bookingQueue;
    private BookingDao bookingDao;
    private Dispatcher localDispatcher;
    private JobManager jobManager;
    private JobManagerSupport jobManagerSupport;
    private JobDao jobDao;
    private HostDao hostDao;
    private ProcDao procDao;

    @Override
    public boolean hasLocalHostAssignment(Host host) {
        return bookingDao.hasLocalJob(host);
    }

    @Override
    public boolean hasActiveLocalFrames(Host host) {
        return bookingDao.hasActiveLocalJob(host);
    }

    @Override
    public void setMaxResources(LocalHostAssignment l, int maxCoreUnits,
            long maxMemory, long maxGpu) {

        Host host = hostDao.getHost(l.getHostId());

        if (maxCoreUnits > 0) {
            bookingDao.updateMaxCores(l, maxCoreUnits);
        }

        if (maxMemory > 0) {
            bookingDao.updateMaxMemory(l, maxMemory);
        }

        if (maxGpu > 0) {
            bookingDao.updateMaxGpu(l, maxGpu);
        }
    }

    @Override
    @Transactional(propagation = Propagation.SUPPORTS)
    public void removeInactiveLocalHostAssignment(LocalHostAssignment lha) {
        String jobId = lha.getJobId();
        try {
            JobDetail jobDetail = jobDao.getJobDetail(jobId);
            if (jobManager.isJobComplete(jobDetail) || jobDetail.state.equals(JobState.Finished)) {
                removeLocalHostAssignment(lha);
            }
        }
        catch (EmptyResultDataAccessException e) {
            removeLocalHostAssignment(lha);
        }
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED)
    public void removeLocalHostAssignment(LocalHostAssignment l) {

        LocalHostAssignment lja = bookingDao.getLocalJobAssignment(l.id);
        Host host = hostDao.getHost(l.getHostId());

        bookingDao.deleteLocalJobAssignment(lja);
    }

    @Override
    @Transactional(propagation = Propagation.SUPPORTS)
    public void deactivateLocalHostAssignment(LocalHostAssignment l) {

        /*
         * De-activate the local booking and unbook procs.
         * The last proc to report in should remove the LHA.
         */
        bookingDao.deactivate(l);

        List<VirtualProc> procs = procDao.findVirtualProcs(l);
        for (VirtualProc p: procs) {
            jobManagerSupport.unbookProc(p, true, new
                    Source("user cleared local jobs"));
        }
        removeLocalHostAssignment(l);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public List<LocalHostAssignment> getLocalHostAssignment(Host host) {
        return bookingDao.getLocalJobAssignment(host);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public LocalHostAssignment getLocalHostAssignment(String id) {
        return bookingDao.getLocalJobAssignment(id);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public LocalHostAssignment getLocalHostAssignment(String hostId, String jobId) {
        return bookingDao.getLocalJobAssignment(hostId, jobId);
    }

    /**
     * Create LocalHostAssignments
     */

    @Override
    public void createLocalHostAssignment(DispatchHost host, Job job,
            LocalHostAssignment lja) {
        bookingDao.insertLocalHostAssignment(host, job, lja);
    }

    @Override
    public void createLocalHostAssignment(DispatchHost host, Layer layer,
            LocalHostAssignment lja) {
        bookingDao.insertLocalHostAssignment(host, layer, lja);
    }

    @Override
    public void createLocalHostAssignment(DispatchHost host, Frame frame,
            LocalHostAssignment lja) {
        bookingDao.insertLocalHostAssignment(host, frame, lja);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public boolean isBlackOutTime(Host host) {
        return bookingDao.isBlackoutTime(host);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public boolean hasResourceDeficit(Host host) {
        return bookingDao.hasResourceDeficit(host);
    }

    public BookingQueue getBookingQueue() {
        return bookingQueue;
    }

    public void setBookingQueue(BookingQueue bookingQueue) {
        this.bookingQueue = bookingQueue;
    }

    public BookingDao getBookingDao() {
        return bookingDao;
    }

    public void setBookingDao(BookingDao bookingDao) {
        this.bookingDao = bookingDao;
    }

    public Dispatcher getLocalDispatcher() {
        return localDispatcher;
    }

    public void setLocalDispatcher(Dispatcher localDispatcher) {
        this.localDispatcher = localDispatcher;
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

    public JobDao getJobDao() {
        return jobDao;
    }

    public void setJobDao(JobDao jobDao) {
        this.jobDao = jobDao;
    }

    public HostDao getHostDao() {
        return hostDao;
    }

    public void setHostDao(HostDao hostDao) {
        this.hostDao = hostDao;
    }

    public ProcDao getProcDao() {
        return procDao;
    }

    public void setProcDao(ProcDao procDao) {
        this.procDao = procDao;
    }
}

