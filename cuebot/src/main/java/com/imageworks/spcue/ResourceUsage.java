
/*
 * Copyright (c) 2018 Sony Pictures Imageworks Inc.
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

/**
 * A class for passing around frame resource usage stats.
 */
public class ResourceUsage {

    private final long coreTimeSeconds;
    private final long clockTimeSeconds;

    public ResourceUsage(long clockTime, int corePoints) {

        if (clockTime < 1) {
            clockTime = 1;
        }

        long coreTime = (long) (clockTime * (corePoints / 100f));
        if (coreTime < 1) {
            coreTime = 1;
        }

        clockTimeSeconds = clockTime;
        coreTimeSeconds = coreTime;
    }

    public long getCoreTimeSeconds() {
        return coreTimeSeconds;
    }

    public long getClockTimeSeconds() {
        return clockTimeSeconds;
    }
}

