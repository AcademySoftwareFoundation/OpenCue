
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



package com.imageworks.spcue.test.util;

import java.util.List;

import junit.framework.TestCase;
import org.junit.Test;

import com.imageworks.spcue.util.Convert;
import com.imageworks.spcue.util.CueUtil;

public class CueUtilTester extends TestCase {

    @Test
    public void testFindChunk() {

        List<Integer> dependOnFrameSet =
            CueUtil.normalizeFrameRange("101-160x10", 1);
        List<Integer> dependErFrameSet =
            CueUtil.normalizeFrameRange("101-160", 1);

        Integer[] results = new Integer[] {
                101,101,101,101,101,101,101,101,101,101,
                111,111,111,111,111,111,111,111,111,111,
                121,121,121,121,121,121,121,121,121,121,
                131,131,131,131,131,131,131,131,131,131,
                141,141,141,141,141,141,141,141,141,141,
                151,151,151,151,151,151,151,151,151,151};

        for (int dependErFrameSetIdx = 0;
            dependErFrameSetIdx < dependErFrameSet.size();
            dependErFrameSetIdx = dependErFrameSetIdx + 1) {

            int result = CueUtil.findChunk(dependOnFrameSet,
                    dependErFrameSet.get(dependErFrameSetIdx));
            assertEquals((int)results[dependErFrameSetIdx], result);
        }
    }

    @Test
    public void testFindChunkStaggered() {

        List<Integer> dependOnFrameSet =
            CueUtil.normalizeFrameRange("101-110:2", 1);
        List<Integer> dependErFrameSet =
            CueUtil.normalizeFrameRange("101-110", 1);

        Integer[] results = new Integer[] {
                101,102,103,104,105,106,107,108,109,110
        };
        for (int i=0; i < dependErFrameSet.size(); i=i+1) {
            int result = CueUtil.findChunk(dependOnFrameSet,dependErFrameSet.get(i));
            assertEquals((int)results[i], result);
        }
    }

    /**
     * Removes all duplicates from the frame range, applies
     * the chunk size, and maintains dispatch order.
     */
    public void testNormalizeFrameRange() {

        /*
         * An array of frame numbers which is the known result
         */
        int[] knownResult;

        /*
         * An array of frames returned from normalizeFrameRange
         */
        List<Integer> frames;

        /*
         * Normal every day frame range.
         */
        knownResult = new int[] { 1,2,3,4,5 };
        frames = CueUtil.normalizeFrameRange("1-5", 1);
        for (int i=0; i<frames.size(); i++) {
            assertEquals(knownResult[i], (int) frames.get(i));
        }

        /*
         * Frame range with chunking
         */
        knownResult = new int[] { 1,5,9 };
        frames = CueUtil.normalizeFrameRange("1-10", 4);
        for (int i=0; i<frames.size(); i++) {
            assertEquals(knownResult[i], (int) frames.get(i));
        }

        /*
         * Frame range with duplicates...
         */
        knownResult = new int[] { 1,3,5,7,9,2,4,6,8,10 };
        frames = CueUtil.normalizeFrameRange("1-10x2,1-10", 1);
        for (int i=0; i<frames.size(); i++) {
            assertEquals(knownResult[i], (int) frames.get(i));
        }

        /*
         * Frame range with duplicates..with chunking!
         */
        knownResult = new int[] { 1,5,9,4,8 };
        frames = CueUtil.normalizeFrameRange("1-10x2,1-10", 2);
        for (int i=0; i<frames.size(); i++) {
            assertEquals(knownResult[i], (int) frames.get(i));
        }

        /*
         * Frame range with no duplicates..with chunking!
         */
        knownResult = new int[] { 1,5,9,4,8 };
        frames = CueUtil.normalizeFrameRange("1-10:2", 2);
        for (int i=0; i<frames.size(); i++) {
            assertEquals(knownResult[i], (int) frames.get(i));
        }
    }

    @Test
    public void testProcsToCores() {
        assertEquals(200,Convert.coresToCoreUnits(2.0f));
        assertEquals(235,Convert.coresToCoreUnits(2.35f));
        assertEquals(299,Convert.coresToCoreUnits(2.999f));
    }

    @Test
    public void testCoreUnitsToCores() {
        assertEquals(1.0f, Convert.coreUnitsToCores(100), 0.0001f);
    }

    @Test
    public void testCoreUnitsToCoresWithScale() {
        assertEquals(100, Convert.coresToWholeCoreUnits(1.132132f));
        assertEquals(19900, Convert.coresToWholeCoreUnits(199.232f));
    }

    @Test
    public void testBuildProcName() {
        assertEquals("drack100/1.00/1", CueUtil.buildProcName("drack100",100,1));
        assertEquals("drack100/1.40/0", CueUtil.buildProcName("drack100",140,0));
        assertEquals("drack100/2.01/2", CueUtil.buildProcName("drack100",201,2));
    }

    @Test
    public void testCoreUnitsToWholecores() {
        float cores = Convert.coreUnitsToWholeCores(149);
        assertEquals(1.0f, cores);

    }
}

