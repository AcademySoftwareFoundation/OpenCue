
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

public class DispatchBookHostLocal extends KeyRunnable {

    private DispatchHost host;
    private Dispatcher dispatcher;

    public DispatchBookHostLocal(DispatchHost host, Dispatcher d) {
        super(host.getId());

        this.host = host;
        this.dispatcher = d;
    }

    @Override
    public void run() {
        new DispatchCommandTemplate() {
            public void wrapDispatchCommand() {
                dispatcher.dispatchHost(host);
            }
        }.execute();
    }
}
