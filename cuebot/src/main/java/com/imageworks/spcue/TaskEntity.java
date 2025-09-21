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

public class TaskEntity extends Entity implements TaskInterface {

    public int minCoreUnits = 100;
    public boolean isDefaultTask = false;

    public String shot;
    public String showId;
    public String deptId;
    public String pointId;

    public TaskEntity() {}

    public TaskEntity(PointInterface c, String shot, int minCoreUnits) {
        this.pointId = c.getPointId();
        this.shot = shot;
        this.minCoreUnits = minCoreUnits;
    }

    public TaskEntity(PointInterface c, String shot) {
        this.pointId = c.getPointId();
        this.shot = shot;
    }

    @Override
    public String getDepartmentId() {
        return deptId;
    }

    @Override
    public String getShowId() {
        return showId;
    }

    @Override
    public String getTaskId() {
        return id;
    }

    @Override
    public String getPointId() {
        return pointId;
    }
}
