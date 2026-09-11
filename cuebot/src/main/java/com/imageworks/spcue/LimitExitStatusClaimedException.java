
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
 * Thrown when a limit tries to claim a frame exit status already claimed by another limit. Two
 * limits claiming the same status have no sensible resolution.
 */
public class LimitExitStatusClaimedException extends RuntimeException {

    private final String claimingLimitName;

    public LimitExitStatusClaimedException(int exitStatus, String claimingLimitName) {
        super("Exit status " + exitStatus + " is already claimed by limit " + claimingLimitName);
        this.claimingLimitName = claimingLimitName;
    }

    public String getClaimingLimitName() {
        return claimingLimitName;
    }
}
