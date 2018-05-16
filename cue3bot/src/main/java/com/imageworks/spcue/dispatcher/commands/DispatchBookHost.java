
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



package com.imageworks.spcue.dispatcher.commands;

import java.util.ArrayList;
import java.util.List;

import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.Group;
import com.imageworks.spcue.Job;
import com.imageworks.spcue.Show;
import com.imageworks.spcue.dispatcher.CoreUnitDispatcher;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.VirtualProc;

/**
 * A command for booking a host.
 *
 * @category command
 */
public class DispatchBookHost implements Runnable  {

    private Show show = null;
    private Group group = null;
    private Job job = null;
    private DispatchHost host;
    private Dispatcher dispatcher;

    public DispatchHost getDispatchHost() {
        return host;
    }

    public DispatchBookHost(DispatchHost host, Dispatcher d) {
        this.host = host;
        this.dispatcher = d;
    }

    public DispatchBookHost(DispatchHost host, Job job, Dispatcher d) {
        this.host = host;
        this.job = job;
        this.dispatcher = d;
    }

    public DispatchBookHost(DispatchHost host, Group group, Dispatcher d) {
        this.host = host;
        this.group = group;
        this.dispatcher = d;
    }

    public DispatchBookHost(DispatchHost host, Show show, Dispatcher d) {
        this.host = host;
        this.show = show;
        this.dispatcher = d;
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
                        Dispatcher.GPU_RESERVED_MIN)) {
                    dispatcher.dispatchHost(host);
                }

                if (host.hasAdditionalResources(
                        Dispatcher.CORE_POINTS_RESERVED_MIN,
                        Dispatcher.MEM_RESERVED_MIN,
                        Dispatcher.GPU_RESERVED_MIN)) {
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
       try {
         DispatchBookHost that = (DispatchBookHost) other;
         return that.host.name.equals(host.name);
       }
       catch (ClassCastException e) {
         return false;
       }
    };
}

