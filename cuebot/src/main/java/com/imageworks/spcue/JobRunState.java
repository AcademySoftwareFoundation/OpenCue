
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
 * Where a job's run stands after a frame stops, read in one query of the job's frame counts.
 */
public enum JobRunState {
    /** Neither of the below: the job is launching, has frames left to run, or was killed. */
    IN_PROGRESS,

    /** Every frame succeeded or was eaten, so the job can shut down. */
    COMPLETE,

    /**
     * The job is pending, nothing is waiting, running or checkpointing, and some frames are dead,
     * so it cannot go on without intervention. Depend frames do not count, since the dead frames
     * may be what they wait for.
     */
    FAILING
}
