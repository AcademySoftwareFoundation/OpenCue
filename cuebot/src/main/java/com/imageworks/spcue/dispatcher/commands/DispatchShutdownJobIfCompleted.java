
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

import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.service.JobManagerSupport;

/**
 * A command for shutting down a job if it is completed. This is a workaround for when Cuebot failed
 * to shutdown a job due to database access error.
 *
 * @category command
 */
public class DispatchShutdownJobIfCompleted extends KeyRunnable {
    private JobInterface job;

    private JobManagerSupport jobManagerSupport;

    public DispatchShutdownJobIfCompleted(JobInterface job, JobManagerSupport jobManagerSupport) {
        super("disp_st_job_comp_" + job.getJobId());
        this.job = job;
        this.jobManagerSupport = jobManagerSupport;
    }

    public void run() {
        new DispatchCommandTemplate() {
            public void wrapDispatchCommand() {
                if (jobManagerSupport.isJobComplete(job)) {
                    jobManagerSupport.shutdownJob(job, new Source("natural"), false);
                }
            }
        }.execute();
    }
}
