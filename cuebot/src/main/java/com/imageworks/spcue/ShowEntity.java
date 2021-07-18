
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

public class ShowEntity extends Entity implements ShowInterface {

    public boolean active;
    public boolean paused;
    public int defaultMinCores;
    public int defaultMaxCores;
    public int defaultMinGpus;
    public int defaultMaxGpus;
    public String[] commentMail;

    public String getShowId() {
        return id;
    }
}

