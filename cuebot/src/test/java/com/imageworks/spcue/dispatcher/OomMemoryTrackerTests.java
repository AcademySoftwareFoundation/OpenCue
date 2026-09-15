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

package com.imageworks.spcue.dispatcher;

import org.junit.Before;
import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/**
 * Unit tests for {@link OomMemoryTracker}. The tracker is a JVM singleton, so each test resets it
 * via {@link OomMemoryTracker#configure} (which rebuilds the caches empty) and uses ids unique to
 * the test.
 */
public class OomMemoryTrackerTests {

    private static final int THRESHOLD = 3;

    @Before
    public void reset() {
        OomMemoryTracker.INSTANCE.configure(OomMemoryTracker.DEFAULT_EXPIRE_HOURS,
                OomMemoryTracker.DEFAULT_EXPIRE_HOURS);
    }

    @Test
    public void outlierOomBumpsOnlyTheFrame() {
        assertFalse(OomMemoryTracker.INSTANCE.onOom("f1", "layerA", 4096L, THRESHOLD));
        assertEquals(4096L, OomMemoryTracker.INSTANCE.frameBumpKb("f1"));
        assertEquals(0L, OomMemoryTracker.INSTANCE.frameBumpKb("f2"));
    }

    @Test
    public void layerRaisedExactlyOnceAtThreshold() {
        assertFalse(OomMemoryTracker.INSTANCE.onOom("f1", "layerB", 1L, THRESHOLD));
        assertFalse(OomMemoryTracker.INSTANCE.onOom("f2", "layerB", 1L, THRESHOLD));
        // Third OOM crosses the threshold: raise the layer, once.
        assertTrue(OomMemoryTracker.INSTANCE.onOom("f3", "layerB", 1L, THRESHOLD));
        // Later recurrences never re-raise the layer but keep bumping the frame.
        assertFalse(OomMemoryTracker.INSTANCE.onOom("f4", "layerB", 2048L, THRESHOLD));
        assertEquals(2048L, OomMemoryTracker.INSTANCE.frameBumpKb("f4"));
    }

    @Test
    public void successKeepsTheStreakButForgetsTheFrameBump() {
        assertFalse(OomMemoryTracker.INSTANCE.onOom("f1", "layerC", 4096L, THRESHOLD));
        assertFalse(OomMemoryTracker.INSTANCE.onOom("f2", "layerC", 4096L, THRESHOLD));
        OomMemoryTracker.INSTANCE.onSuccess("f1");
        assertEquals(0L, OomMemoryTracker.INSTANCE.frameBumpKb("f1"));
        // The streak survived the success: the next OOM still escalates.
        assertTrue(OomMemoryTracker.INSTANCE.onOom("f3", "layerC", 4096L, THRESHOLD));
    }

    @Test
    public void streaksAreIndependentPerLayer() {
        assertFalse(OomMemoryTracker.INSTANCE.onOom("f1", "layerD", 1L, THRESHOLD));
        assertFalse(OomMemoryTracker.INSTANCE.onOom("f2", "layerD", 1L, THRESHOLD));
        assertFalse(OomMemoryTracker.INSTANCE.onOom("f3", "layerE", 1L, THRESHOLD));
        assertTrue(OomMemoryTracker.INSTANCE.onOom("f4", "layerD", 1L, THRESHOLD));
    }

    @Test
    public void configureDiscardsTrackedState() {
        assertFalse(OomMemoryTracker.INSTANCE.onOom("f1", "layerF", 4096L, THRESHOLD));
        OomMemoryTracker.INSTANCE.configure(1, 1);
        assertEquals(0L, OomMemoryTracker.INSTANCE.frameBumpKb("f1"));
        // Streak restarted from zero.
        assertFalse(OomMemoryTracker.INSTANCE.onOom("f2", "layerF", 1L, 2));
        assertTrue(OomMemoryTracker.INSTANCE.onOom("f3", "layerF", 1L, 2));
    }
}
