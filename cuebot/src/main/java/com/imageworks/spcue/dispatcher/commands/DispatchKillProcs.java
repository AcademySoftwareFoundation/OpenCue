
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

import com.imageworks.spcue.Source;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.service.JobManagerSupport;
import java.util.Collection;

public class DispatchKillProcs extends KeyRunnable {
    private Collection<VirtualProc> procs;
    private JobManagerSupport jobManagerSupport;
    private Source source;

    public DispatchKillProcs(Collection<VirtualProc> procs, Source source,
            JobManagerSupport jobManagerSupport) {
        super("disp_kill_procs_" + procs.hashCode() + "_" + source.toString() + "_"
                + jobManagerSupport.hashCode());
        this.procs = procs;
        this.source = source;
        this.jobManagerSupport = jobManagerSupport;
    }

    public void run() {
        new DispatchCommandTemplate() {
            public void wrapDispatchCommand() {
                for (VirtualProc p : procs) {
                    jobManagerSupport.kill(p, source);
                }
            }
        }.execute();
    }
}
