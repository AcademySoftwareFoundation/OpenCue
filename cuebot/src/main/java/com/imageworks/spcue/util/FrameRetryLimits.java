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

package com.imageworks.spcue.util;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.springframework.core.env.Environment;

/**
 * The single source of the per-frame retry limits (job.int_max_retries), read from the
 * job.frame_retries_* properties. Both job submission (JobSpec) and runtime updates
 * (JobDao.updateMaxFrameRetries, JobDao.updateAutoEat) go through this class so the two paths
 * cannot disagree.
 */
public final class FrameRetryLimits {

    private static final Logger logger = LogManager.getLogger(FrameRetryLimits.class);

    public static final String DEFAULT_PROPERTY = "job.frame_retries_default";
    public static final String MAX_PROPERTY = "job.frame_retries_max";
    public static final String MIN_PROPERTY = "job.frame_retries_min";

    public static final int FALLBACK_DEFAULT = 1;
    public static final int FALLBACK_MAX = 16;
    public static final int FALLBACK_MIN = 0;

    private final int defaultRetries;
    private final int maxRetries;
    private final int minRetries;

    private FrameRetryLimits(int defaultRetries, int maxRetries, int minRetries) {
        this.defaultRetries = defaultRetries;
        this.maxRetries = maxRetries;
        this.minRetries = minRetries;
    }

    /**
     * Reads the limits from the environment. A negative min is raised to 0, a max below min is
     * raised to min, and a default outside [min, max] is clamped into it, each with a warning.
     */
    public static FrameRetryLimits from(Environment env) {
        int min = env.getProperty(MIN_PROPERTY, Integer.class, FALLBACK_MIN);
        int max = env.getProperty(MAX_PROPERTY, Integer.class, FALLBACK_MAX);
        int def = env.getProperty(DEFAULT_PROPERTY, Integer.class, FALLBACK_DEFAULT);

        if (min < 0) {
            logger.warn(MIN_PROPERTY + "=" + min + " is negative, using 0");
            min = 0;
        }
        if (max < min) {
            logger.warn(MAX_PROPERTY + "=" + max + " is below " + MIN_PROPERTY + "=" + min
                    + ", using " + min);
            max = min;
        }
        int clampedDef = Math.max(min, Math.min(max, def));
        if (clampedDef != def) {
            logger.warn(DEFAULT_PROPERTY + "=" + def + " is outside [" + min + ", " + max
                    + "], using " + clampedDef);
        }
        return new FrameRetryLimits(clampedDef, max, min);
    }

    public int getDefault() {
        return defaultRetries;
    }

    public int getMax() {
        return maxRetries;
    }

    public int getMin() {
        return minRetries;
    }

    /**
     * Clamps a requested retry count into [min, max].
     */
    public int clamp(int retries) {
        return Math.max(minRetries, Math.min(maxRetries, retries));
    }
}
