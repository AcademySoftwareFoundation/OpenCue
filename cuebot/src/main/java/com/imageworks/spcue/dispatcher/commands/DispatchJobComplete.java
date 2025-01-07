
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
 * A command for shutting down a job.
 *
 * @category command
 */
public class DispatchJobComplete extends KeyRunnable {
    private JobInterface job;
    private Source source;
    private boolean isManualKill;

    private JobManagerSupport jobManagerSupport;

    public DispatchJobComplete(JobInterface job, Source source, boolean isManualKill,
            JobManagerSupport jobManagerSupport) {
        super("disp_job_complete_" + job.getJobId() + "_" + source.toString());
        this.job = job;
        this.source = source;
        this.isManualKill = isManualKill;
        this.jobManagerSupport = jobManagerSupport;
    }

    public void run() {
        new DispatchCommandTemplate() {
            public void wrapDispatchCommand() {
                jobManagerSupport.shutdownJob(job, source, isManualKill);
            }
        }.execute();
    }
}
