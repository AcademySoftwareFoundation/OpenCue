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

package com.imageworks.spcue.test.util;

import org.junit.Test;
import org.springframework.mock.env.MockEnvironment;

import com.imageworks.spcue.util.FrameRetryLimits;

import static org.junit.Assert.assertEquals;

public class FrameRetryLimitsTests {

    private static MockEnvironment env(String def, String max, String min) {
        MockEnvironment env = new MockEnvironment();
        if (def != null) {
            env.setProperty(FrameRetryLimits.DEFAULT_PROPERTY, def);
        }
        if (max != null) {
            env.setProperty(FrameRetryLimits.MAX_PROPERTY, max);
        }
        if (min != null) {
            env.setProperty(FrameRetryLimits.MIN_PROPERTY, min);
        }
        return env;
    }

    @Test
    public void testFallbacksWhenUnset() {
        FrameRetryLimits limits = FrameRetryLimits.from(new MockEnvironment());
        assertEquals(FrameRetryLimits.FALLBACK_DEFAULT, limits.getDefault());
        assertEquals(FrameRetryLimits.FALLBACK_MAX, limits.getMax());
        assertEquals(FrameRetryLimits.FALLBACK_MIN, limits.getMin());
    }

    @Test
    public void testReadsProperties() {
        FrameRetryLimits limits = FrameRetryLimits.from(env("3", "5", "1"));
        assertEquals(3, limits.getDefault());
        assertEquals(5, limits.getMax());
        assertEquals(1, limits.getMin());
    }

    @Test
    public void testClamp() {
        FrameRetryLimits limits = FrameRetryLimits.from(env("1", "3", "0"));
        assertEquals(3, limits.clamp(10));
        assertEquals(0, limits.clamp(-2));
        assertEquals(2, limits.clamp(2));
    }

    @Test
    public void testDefaultClampedIntoRange() {
        assertEquals(3, FrameRetryLimits.from(env("10", "3", "0")).getDefault());
        assertEquals(2, FrameRetryLimits.from(env("0", "3", "2")).getDefault());
    }

    @Test
    public void testInvalidMinAndMaxCorrected() {
        FrameRetryLimits limits = FrameRetryLimits.from(env("1", "1", "-4"));
        assertEquals(0, limits.getMin());

        limits = FrameRetryLimits.from(env("1", "2", "5"));
        assertEquals(5, limits.getMin());
        assertEquals(5, limits.getMax());
        assertEquals(5, limits.getDefault());
    }
}
