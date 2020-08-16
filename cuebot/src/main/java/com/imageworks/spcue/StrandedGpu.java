
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

public final class StrandedGpu {

    /**
     * The maximum time this object should be valid.
     */
    private static final long MAX_AGE_MILLIS = 5000l;

    private final int gpu;
    private final long expireTime = System.currentTimeMillis() + MAX_AGE_MILLIS;

    public StrandedGpu(int gpu) {
        this.gpu = gpu;
    }

    public int getGpu() {
        return this.gpu;
    }

    public boolean isExpired() {
        return System.currentTimeMillis() > expireTime;
    }
}

