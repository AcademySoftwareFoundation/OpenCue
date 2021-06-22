
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

import java.util.LinkedHashSet;

import com.imageworks.spcue.dispatcher.Dispatcher;

public class ServiceEntity extends Entity {
    /**
     * Determines if the service is threadable or not.
     */
    public boolean threadable = false;

    /**
     * Determines the default minimum cores per frame.
     */
    public int minCores = Dispatcher.CORE_POINTS_RESERVED_DEFAULT;

    /**
     * Determines the default minimum cores per frame.  0 indicates
     * the feature is disabled.
     */
    public int maxCores = 0;

    /**
     * Determines the default minimum gpus per frame.
     */
    public int minGpus = 0;

    /**
     * Determines the default minimum gpus per frame.  0 indicates
     * the feature is disabled.
     */
    public int maxGpus = 0;

    /**
     * Determines the default minimum memory per frame.
     */
    public long minMemory = Dispatcher.MEM_RESERVED_DEFAULT;

    /**
     * Determines the default minimum gpu per frame.
     */
    public long minGpuMemory = Dispatcher.MEM_GPU_RESERVED_DEFAULT;

    /**
     * Determines the default tags.
     */
    public LinkedHashSet<String> tags = new LinkedHashSet<String>();

    public int timeout = 0;

    public int timeout_llu = 0;

}

