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

import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.dispatcher.Dispatcher;

/**
 * A command for booking a slot-based host through the slot dispatcher.
 *
 * Slot-based hosts (host.concurrentSlotsLimit >= 0) only run slot-based layers, so their booking
 * never enters the generic cores/memory dispatch pipeline.
 *
 * @category command
 */
public class DispatchBookHostSlots extends KeyRunnable {

    private DispatchHost host;
    private Dispatcher dispatcher;

    public DispatchBookHostSlots(DispatchHost host, Dispatcher d) {
        super(host.getId() + "_slots");
        this.host = host;
        this.dispatcher = d;
    }

    public DispatchHost getDispatchHost() {
        return host;
    }

    public void run() {
        new DispatchCommandTemplate() {
            public void wrapDispatchCommand() {
                if (host.idleSlots > 0) {
                    dispatcher.dispatchHost(host);
                }
            }
        }.execute();
    }
}
