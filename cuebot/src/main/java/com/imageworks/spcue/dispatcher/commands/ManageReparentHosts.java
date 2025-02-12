
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

import java.util.List;

import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.dispatcher.commands.KeyRunnable;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.service.HostManager;

public class ManageReparentHosts extends KeyRunnable {
    AllocationInterface alloc;
    List<HostInterface> hosts;
    HostManager hostManager;

    public ManageReparentHosts(AllocationInterface alloc, List<HostInterface> hosts,
            HostManager hostManager) {
        super(alloc.getAllocationId());
        this.alloc = alloc;
        this.hosts = hosts;
        this.hostManager = hostManager;
    }

    public void run() {
        new DispatchCommandTemplate() {
            public void wrapDispatchCommand() {
                for (HostInterface host : hosts) {
                    hostManager.setAllocation(host, alloc);
                }
            }
        }.execute();
    }
}
