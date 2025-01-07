
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

import java.sql.Date;

/**
 * Class for track-it details
 */
public class TrackitTaskDetail {

    public String show;
    public String shot;
    public String task;
    public String status;
    public Date startDate;
    public Date endDate;
    public String cgSup;
    public int frameCount;
    public int points;
    public int weeks;
}
