
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
 * A limit's failure rule: what to do when a frame exits with the status the limit claims as "this
 * license was unavailable". Replaces the dispatcher.layer_delay.rules property entries for statuses
 * a limit claims.
 */
public final class LimitRule {

    public final String limitId;
    public final String limitName;
    public final int exitStatus;
    /** Minutes to postpone the failing frame's layer; 0 = tag without delaying. */
    public final int delayMinutes;
    /** Whether to bind the failing frame's layer to the limit. */
    public final boolean autoTag;

    public LimitRule(String limitId, String limitName, int exitStatus, int delayMinutes,
            boolean autoTag) {
        this.limitId = limitId;
        this.limitName = limitName;
        this.exitStatus = exitStatus;
        this.delayMinutes = delayMinutes;
        this.autoTag = autoTag;
    }
}
