
/*
 * Copyright Contributors to the OpenCue Project
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



package com.imageworks.spcue.dispatcher.commands;

import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.dispatcher.Dispatcher;

/**
 * A command for booking a host.
 *
 * @category command
 */
public class DispatchBookHost implements Runnable  {

    private ShowInterface show = null;
    private GroupInterface group = null;
    private JobInterface job = null;
    private DispatchHost host;
    private Dispatcher dispatcher;
    private String key;

    public DispatchHost getDispatchHost() {
        this.key = host.getId();
        return host;
    }

    public DispatchBookHost(DispatchHost host, Dispatcher d) {
        this.host = host;
        this.key = host.getId();
        this.dispatcher = d;
    }

    public DispatchBookHost(DispatchHost host, JobInterface job, Dispatcher d) {
        this.host = host;
        this.job = job;
        this.key = host.getId() + "_job_" + job.getJobId();
        this.dispatcher = d;
    }

    public DispatchBookHost(DispatchHost host, GroupInterface group, Dispatcher d) {
        this.host = host;
        this.group = group;
        this.key = host.getId() + "_group_" + group.getGroupId();
        this.dispatcher = d;
    }

    public DispatchBookHost(DispatchHost host, ShowInterface show, Dispatcher d) {
        this.host = host;
        this.show = show;
        this.key = host.getId() + "_name_" + show.getName();
        this.dispatcher = d;
    }

    public String getKey() {
        return this.key;
    }

    public void run() {
        new DispatchCommandTemplate() {
            public void wrapDispatchCommand() {
                if (show != null) {
                    dispatcher.dispatchHost(host, show);
                }
                else if (group != null) {
                    dispatcher.dispatchHost(host, group);
                }
                else if (job != null) {
                    dispatcher.dispatchHost(host, job);
                }

                // Try to book any remaining resources
                if (host.hasAdditionalResources(
                        Dispatcher.CORE_POINTS_RESERVED_MIN,
                        Dispatcher.MEM_RESERVED_MIN,
                        Dispatcher.GPU_UNITS_RESERVED_MIN,
                        Dispatcher.MEM_GPU_RESERVED_MIN)) {
                    dispatcher.dispatchHost(host);
                }

                if (host.hasAdditionalResources(
                        Dispatcher.CORE_POINTS_RESERVED_MIN,
                        Dispatcher.MEM_RESERVED_MIN,
                        Dispatcher.GPU_UNITS_RESERVED_MIN,
                        Dispatcher.MEM_GPU_RESERVED_MIN)) {
                    dispatcher.dispatchHostToAllShows(host);
                }
            }
        }.execute();
    }

    @Override
    public int hashCode() {
       return host.name.hashCode();
    };

    @Override
    public boolean equals(Object other) {
        if (other == null) {
            return false;
        }
        if (this.getClass() != other.getClass()) {
            return false;
        }
        DispatchBookHost that = (DispatchBookHost) other;
        return that.host.name.equals(host.name);
    };
}

