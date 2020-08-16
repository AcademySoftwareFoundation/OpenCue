
/*
 * Copyright Contributors to the OpenCue Project
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

package com.imageworks.spcue;

import java.util.Optional;

import com.imageworks.spcue.grpc.job.JobState;

public class JobDetail extends JobEntity implements JobInterface, DepartmentInterface {
    public String groupId;
    public String deptId;
    public JobState state;
    public String shot;
    public String user;
    public String email;
    public Optional<Integer> uid;
    public String logDir;
    public boolean isPaused;
    public boolean isAutoEat;
    public int totalFrames;
    public int totalLayers;
    public int startTime;
    public int stopTime;
    public int maxRetries;

    public String os;
    public String facilityName;
    public String deptName;
    public String showName;

    public int priority = 1;
    public int minCoreUnits = 100;
    public int maxCoreUnits = 200000;
    public int minGpuUnits = 0;
    public int maxGpuUnits = 100;
    public boolean isLocal = false;
    public String localHostName;
    public int localMaxCores;
    public int localMaxGpu;
    public int localMaxMemory;
    public int localThreadNumber;
    public int localMaxGpuMemory;

    public String getDepartmentId() {
        return deptId;
    }
}

