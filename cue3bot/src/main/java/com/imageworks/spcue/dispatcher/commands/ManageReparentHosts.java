
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

import java.util.List;

import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.Host;
import com.imageworks.spcue.service.HostManager;

public class ManageReparentHosts implements Runnable {
    AllocationInterface alloc;
    List<Host> hosts;
    HostManager hostManager;

    public ManageReparentHosts(AllocationInterface alloc, List<Host> hosts, HostManager hostManager) {
        this.alloc = alloc;
        this.hosts = hosts;
        this.hostManager = hostManager;
    }

    public void run() {
        new DispatchCommandTemplate() {
            public void wrapDispatchCommand() {
                for (Host host : hosts) {
                    hostManager.setAllocation(host, alloc);
                }
            }
        }.execute();
    }
}

