
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



package com.imageworks.spcue.dispatcher;

public interface ResourceContainer {

    /**
     * Return true if the container can handle the given resource amounts. False
     * if not.
     *
     * @param minCores
     * @param minMemory
     * @param minGpu
     * @return
     */
    public boolean hasAdditionalResources(int minCores, long minMemory, long minGpu);

    /**
     * Subtract the given resources from the grand totals.
     *
     * @param coreUnits
     * @param memory
     * @param gpu
     */
    public void useResources(int coreUnits, long memory, long gpu);

}

