
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

package com.imageworks.spcue;

/**
 * A wrapper for a string that contains the source of external commands.
 */
public class Source {

    public String source = "unknown";
    public String username = "";
    public String pid = "";
    public String host_kill = "";
    public String reason = "";

    public Source() {}

    public Source(String source) {
        this.source = source;
    }

    public Source(String source, String username, String pid, String host_kill, String reason) {
        this.source = source;
        this.username = username;
        this.pid = pid;
        this.host_kill = host_kill;
        this.reason = reason;
    }

    public String getReason() {
        return this.reason;
    }

    public String toString() {
        return "User: " + this.username + ", Pid: " + this.pid + ", Hostname: " + this.host_kill
                + ", Reason: " + this.reason + "\n" + this.source;
    }
}
