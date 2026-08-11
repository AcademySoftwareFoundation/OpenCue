
/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */

package com.imageworks.spcue.dispatcher;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.concurrent.TimeUnit;

import com.google.common.cache.Cache;
import com.google.common.cache.CacheBuilder;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.DispatchJob;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.rqd.RqdClient;
import com.imageworks.spcue.rqd.RqdClientException;
import com.imageworks.spcue.service.JobManager;

/**
 * The Slot Dispatcher.
 *
 * Books slot-based layers (layer.slotsRequired > 0) onto slot-based hosts
 * (host.concurrentSlotsLimit >= 0). Slot bookings reserve 0 cores and 0 memory; the only
 * constraints are the host's concurrent slots limit and the subscription/folder/job max_slots caps.
 * This dispatcher is completely independent from the generic cores/memory pipeline
 * ({@link CoreUnitDispatcher}): host reports for slot-based hosts are deviated here by
 * {@link HostReportHandler} and never enter the generic dispatch queries.
 *
 * The dispatch pipeline mirrors the generic one:
 *
 * 1. Find jobs with pending slot work bookable on this host.
 *
 * 2. For each job, find slot frames that fit the host's idle slots and the max_slots caps.
 *
 * 3. Reserve the frame (WAITING to RUNNING), insert the proc (the before_insert_proc database
 * trigger revalidates the host's slot cap under a host row lock, so concurrent bookings can never
 * exceed the cap), and launch on RQD.
 */
public class SlotDispatcher implements Dispatcher {

    private static final Logger logger = LogManager.getLogger(SlotDispatcher.class);

    private DispatchSupport dispatchSupport;

    private JobManager jobManager;

    private RqdClient rqdClient;

    public boolean testMode = false;

    private Environment env;

    @Autowired
    public SlotDispatcher(Environment env) {
        this.env = env;
    }

    private int getIntProperty(String property) {
        return env.getRequiredProperty(property, Integer.class);
    }

    /*
     * Keeps a map of unique job IDs that should be skipped over for booking until the record has
     * expired, so concurrent slot hosts don't all pile onto the same top-priority job. Mirrors
     * CoreUnitDispatcher's job lock.
     */
    private Cache<String, String> jobLock;

    private Cache<String, String> getOrCreateJobLock() {
        if (jobLock == null) {
            this.jobLock = CacheBuilder.newBuilder()
                    .concurrencyLevel(getIntProperty("dispatcher.job_lock_concurrency_level"))
                    .expireAfterWrite(getIntProperty("dispatcher.job_lock_expire_seconds"),
                            TimeUnit.SECONDS)
                    .build();
        }
        return jobLock;
    }

    @Override
    public List<VirtualProc> dispatchHostToAllShows(DispatchHost host) {
        return dispatchHost(host);
    }

    @Override
    public List<VirtualProc> dispatchHost(DispatchHost host) {
        List<VirtualProc> procs = new ArrayList<VirtualProc>();

        if (!host.isSlotHost()) {
            logger.warn(host.getName() + " is not a slot-based host, skipping slot dispatch.");
            return procs;
        }

        Set<String> jobs = dispatchSupport.findSlotDispatchJobs(host,
                getIntProperty("dispatcher.job_query_max"));

        try {
            for (String jobId : jobs) {
                if (host.idleSlots <= 0) {
                    break;
                }

                if (procs.size() >= getIntProperty("dispatcher.host_frame_dispatch_max")) {
                    break;
                }

                if (getIntProperty("dispatcher.job_lock_expire_seconds") > 0) {
                    if (getOrCreateJobLock().getIfPresent(jobId) != null) {
                        continue;
                    }
                    jobLock.put(jobId, jobId);
                }

                DispatchJob job = jobManager.getDispatchJob(jobId);
                try {
                    procs.addAll(dispatchHost(host, job));
                } catch (DispatcherException e) {
                    /*
                     * Something is wrong with the host itself (e.g. RQD is unreachable); stop
                     * dispatching to it instead of churning through every remaining job.
                     */
                    throw e;
                } catch (Exception e) {
                    logger.info("slot job dispatch exception, " + e);
                }
            }
        } catch (DispatcherException e) {
            logger.info(host.name + " slot dispatcher exception, " + e);
        }

        return procs;
    }

    @Override
    public List<VirtualProc> dispatchHost(DispatchHost host, JobInterface job) {
        List<VirtualProc> procs = new ArrayList<VirtualProc>();

        if (!host.isSlotHost() || host.idleSlots <= 0) {
            return procs;
        }

        List<DispatchFrame> frames = dispatchSupport.findNextSlotDispatchFrames(job, host,
                getIntProperty("dispatcher.frame_query_max"));

        logger.info("Slot frames found: " + frames.size() + " for host " + host.getName() + " "
                + host.idleSlots + "/" + host.concurrentSlotsLimit + " idle slots on job "
                + job.getName());

        /*
         * The frame query checks the job/folder/subscription max_slots caps against usage at query
         * time; bookings made in this pass are not reflected there, so track them here to never
         * exceed a cap within the pass.
         */
        int slotCapacityRemaining = dispatchSupport.getSlotCapacityRemaining(job, host);
        int slotsBooked = 0;

        for (DispatchFrame frame : frames) {

            if (frame.slotsRequired <= 0 || frame.slotsRequired > host.idleSlots) {
                continue;
            }

            if (slotsBooked + frame.slotsRequired > slotCapacityRemaining) {
                // The job/folder/subscription caps have no room for another booking of this
                // job in this pass.
                break;
            }

            VirtualProc proc = VirtualProc.buildSlotProc(host, frame);

            try {
                dispatch(frame, proc);
                dispatchSummary(proc, frame);
            } catch (FrameReservationException fre) {
                /*
                 * Another thread got the frame first, move on to the next frame.
                 */
                DispatchSupport.bookingRetries.incrementAndGet();
                logger.info("slot frame reservation error, " + "failed to book next frame, " + fre);
                continue;
            } catch (ResourceDuplicationFailureException rdfe) {
                /*
                 * The frame already has a proc assigned; fix it and move on.
                 */
                DispatchSupport.bookingErrors.incrementAndGet();
                dispatchSupport.fixFrame(frame);
                logger.info("slot proc update error, " + proc + " already assigned "
                        + "to another frame, " + rdfe);
                continue;
            } catch (ResourceReservationFailureException rrfe) {
                /*
                 * The host slot cap was exceeded (enforced by the before_insert_proc trigger) or
                 * the proc insert failed. Clear the frame back to WAITING and stop dispatching to
                 * this host; its slot capacity is spent.
                 */
                DispatchSupport.bookingErrors.incrementAndGet();
                dispatchSupport.clearFrame(frame);
                logger.info("slot reservation error, failed to allocate slots on " + host.getName()
                        + ", " + rrfe);
                break;
            } catch (Exception e) {
                /*
                 * The frame/host records may have been updated but something else failed. Unbook
                 * the proc, clear the frame and stop dispatching this host. Also send a kill just
                 * in case the frame actually launched.
                 */
                DispatchSupport.bookingErrors.incrementAndGet();
                logger.warn("slot dispatch failed booking proc " + proc + " on job " + job, e);
                dispatchSupport.unbookProc(proc);
                dispatchSupport.clearFrame(frame);
                try {
                    rqdClient.killFrame(proc,
                            "An accounting error occured when booking this frame.");
                } catch (RqdClientException rqde) {
                    // Expected to fail unless the frame actually launched.
                }
                throw new DispatcherException(
                        "stopped slot dispatching " + host.getName() + ", " + e);
            }

            procs.add(proc);
            DispatchSupport.bookedProcs.getAndIncrement();
            host.idleSlots = host.idleSlots - frame.slotsRequired;
            slotsBooked = slotsBooked + frame.slotsRequired;

            if (host.idleSlots <= 0) {
                break;
            }
            if (procs.size() >= getIntProperty("dispatcher.job_frame_dispatch_max")) {
                break;
            }
            if (procs.size() >= getIntProperty("dispatcher.host_frame_dispatch_max")) {
                break;
            }
        }

        return procs;
    }

    @Override
    public void dispatch(DispatchFrame frame, VirtualProc proc) {
        // Allocate frame on the database
        dispatchSupport.startFrameAndProc(proc, frame);

        // Communicate with RQD to run the frame.
        if (!testMode) {
            dispatchSupport.runFrame(proc, frame);
        }
    }

    @Override
    public List<VirtualProc> dispatchHost(DispatchHost host, ShowInterface show) {
        throw new RuntimeException("not implemented");
    }

    @Override
    public List<VirtualProc> dispatchHost(DispatchHost host, GroupInterface group) {
        throw new RuntimeException("not implemented");
    }

    @Override
    public List<VirtualProc> dispatchHost(DispatchHost host, LayerInterface layer) {
        throw new RuntimeException("not implemented");
    }

    @Override
    public List<VirtualProc> dispatchHost(DispatchHost host, FrameInterface frame) {
        throw new RuntimeException("not implemented");
    }

    @Override
    public void dispatchProcToJob(VirtualProc proc, JobInterface job) {
        throw new RuntimeException("not implemented, slot procs are unbooked on frame completion");
    }

    @Override
    public boolean isTestMode() {
        return testMode;
    }

    @Override
    public void setTestMode(boolean enabled) {
        testMode = enabled;
    }

    private void dispatchSummary(VirtualProc p, DispatchFrame f) {
        logger.trace("Slot booking summary: " + p.slotsReserved + " slots " + p.getName() + " to "
                + f.show + "/" + f.shot);
    }

    public DispatchSupport getDispatchSupport() {
        return dispatchSupport;
    }

    public void setDispatchSupport(DispatchSupport dispatchSupport) {
        this.dispatchSupport = dispatchSupport;
    }

    public JobManager getJobManager() {
        return jobManager;
    }

    public void setJobManager(JobManager jobManager) {
        this.jobManager = jobManager;
    }

    public RqdClient getRqdClient() {
        return rqdClient;
    }

    public void setRqdClient(RqdClient rqdClient) {
        this.rqdClient = rqdClient;
    }
}
