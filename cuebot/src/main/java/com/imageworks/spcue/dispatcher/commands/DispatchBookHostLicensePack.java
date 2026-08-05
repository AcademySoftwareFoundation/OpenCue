
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

package com.imageworks.spcue.dispatcher.commands;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.springframework.core.env.Environment;
import org.springframework.dao.EmptyResultDataAccessException;

import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.LicenseBookingGate;
import com.imageworks.spcue.grpc.report.RunningFrameInfo;
import com.imageworks.spcue.service.JobManager;

/**
 * License-packing variant of {@link DispatchBookHost}.
 *
 * Queued when a host report shows running frames that declare application licenses. All the real
 * work: deciding which of those licenses are host-based with a live sample, finding pending jobs
 * that need them, and dispatching happens here on a booking thread, so the report thread only pays
 * a cache lookup to decide whether to queue this command at all.
 *
 * Jobs that need a host-based license this host already holds get the first shot at its idle
 * resources (an extra frame on a seated machine is free; a fresh machine burns a seat). Whatever
 * they leave falls through to the exact booking the host would have received without packing: its
 * preferred show when it has one, then the normal all-shows order.
 */
public class DispatchBookHostLicensePack extends KeyRunnable {

    private static final Logger logger = LogManager.getLogger(DispatchBookHostLicensePack.class);

    private final DispatchHost host;
    private final List<RunningFrameInfo> runningFrames;
    private final ShowInterface preferredShow;
    private final LicenseBookingGate licenseBookingGate;
    private final JobManager jobManager;
    private final Dispatcher dispatcher;
    private final Environment env;

    public DispatchBookHostLicensePack(DispatchHost host, List<RunningFrameInfo> runningFrames,
            ShowInterface preferredShow, LicenseBookingGate licenseBookingGate,
            JobManager jobManager, Dispatcher dispatcher, Environment env) {
        super(host.getId() + "_license_pack");
        this.host = host;
        this.runningFrames = runningFrames;
        this.preferredShow = preferredShow;
        this.licenseBookingGate = licenseBookingGate;
        this.jobManager = jobManager;
        this.dispatcher = dispatcher;
        this.env = env;
    }

    public void run() {
        new DispatchCommandTemplate() {
            public void wrapDispatchCommand() {
                long memReservedMin =
                        env.getRequiredProperty("dispatcher.memory.mem_reserved_min", Long.class);
                long memGpuReservedMin = env
                        .getRequiredProperty("dispatcher.memory.mem_gpu_reserved_min", Long.class);

                for (JobInterface packJob : findPackJobs()) {
                    if (!host.hasAdditionalResources(Dispatcher.CORE_POINTS_RESERVED_MIN,
                            memReservedMin, Dispatcher.GPU_UNITS_RESERVED_MIN, memGpuReservedMin)) {
                        break;
                    }
                    dispatcher.dispatchHost(host, packJob);
                }

                /*
                 * Fall through to the exact booking this host would have received without packing
                 * (DispatchBookHost ends with the generic remaining-resources booking).
                 */
                if (preferredShow != null) {
                    new DispatchBookHost(host, preferredShow, dispatcher, env).run();
                } else {
                    new DispatchBookHost(host, dispatcher, env).run();
                }
            }
        }.execute();
    }

    /**
     * Jobs whose waiting layers need a host-based license this host's running frames already hold.
     * Empty on any failure: packing is an optimization and must never block the fall-through
     * booking.
     */
    private List<JobInterface> findPackJobs() {
        List<JobInterface> packJobs = new ArrayList<JobInterface>();
        try {
            Set<String> packLicenses = licenseBookingGate.hostBasedLicensesRunning(runningFrames);
            if (packLicenses.isEmpty()) {
                return packJobs;
            }
            int packJobsMax = env.getProperty("scheduler.license.pack_jobs_max", Integer.class, 5);
            for (String jobId : licenseBookingGate.findPackableJobs(packLicenses, host,
                    packJobsMax)) {
                try {
                    packJobs.add(jobManager.getJob(jobId));
                } catch (EmptyResultDataAccessException e) {
                    // The job finished between the query and here; nothing to pack.
                }
            }
        } catch (Exception e) {
            logger.warn("Failed to find license pack jobs for " + host.getName() + ": " + e);
        }
        return packJobs;
    }
}
