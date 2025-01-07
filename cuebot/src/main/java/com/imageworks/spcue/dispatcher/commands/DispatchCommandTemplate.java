
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

import com.imageworks.spcue.util.CueExceptionUtil;

/**
 * A template that wraps the code within the run() method of each dispatch command.
 *
 * @category command
 */
public abstract class DispatchCommandTemplate {

    public abstract void wrapDispatchCommand();

    public void execute() {
        try {
            wrapDispatchCommand();
        } catch (java.lang.Throwable t) {
            CueExceptionUtil.logStackTrace(
                    "Dispatch command template " + this.getClass().toString() + " caught error ",
                    t);
        }
    }
}
