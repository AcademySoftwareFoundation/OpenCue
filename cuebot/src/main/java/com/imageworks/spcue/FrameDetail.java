
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

import java.sql.Timestamp;

import com.imageworks.spcue.grpc.job.FrameState;

public class FrameDetail extends FrameEntity implements FrameInterface {

    public FrameState state;
    public int number;
    public int dependCount;
    public int retryCount;
    public int exitStatus;
    public long maxRss;
    public int dispatchOrder;
    public String lastResource;

    public Timestamp dateStarted;
    public Timestamp dateStopped;
    public Timestamp dateUpdated;
    public Timestamp dateLLU;
}
