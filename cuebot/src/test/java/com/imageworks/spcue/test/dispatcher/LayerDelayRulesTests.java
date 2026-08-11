
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

package com.imageworks.spcue.test.dispatcher;

import java.time.Duration;
import java.util.Map;

import org.junit.Test;

import com.imageworks.spcue.dispatcher.LayerDelayRules;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

/**
 * Pure unit tests for the dispatcher.layer_delay.rules parser. No Spring context or database
 * required.
 */
public class LayerDelayRulesTests {

    @Test
    public void testEmptyDisablesFeature() {
        assertTrue(LayerDelayRules.parse("").isEmpty());
        assertTrue(LayerDelayRules.parse("   ").isEmpty());
        assertTrue(LayerDelayRules.parse(null).isEmpty());
    }

    @Test
    public void testSingleRule() {
        Map<Integer, Duration> rules = LayerDelayRules.parse("330:5");
        assertEquals(1, rules.size());
        assertEquals(Duration.ofMinutes(5), rules.get(330));
    }

    @Test
    public void testMultipleRules() {
        Map<Integer, Duration> rules = LayerDelayRules.parse("330:5,332:60");
        assertEquals(2, rules.size());
        assertEquals(Duration.ofMinutes(5), rules.get(330));
        assertEquals(Duration.ofMinutes(60), rules.get(332));
    }

    @Test
    public void testWhitespaceTolerated() {
        Map<Integer, Duration> rules = LayerDelayRules.parse(" 330 : 5 , 332 : 60 ");
        assertEquals(2, rules.size());
        assertEquals(Duration.ofMinutes(5), rules.get(330));
    }

    @Test
    public void testMalformedEntriesSkippedNotFatal() {
        // A bad entry is dropped with a warning; valid entries around it survive.
        Map<Integer, Duration> rules = LayerDelayRules.parse("330:5,bogus,332:sixty,333");
        assertEquals(1, rules.size());
        assertEquals(Duration.ofMinutes(5), rules.get(330));
    }

    @Test
    public void testNonPositiveMinutesSkipped() {
        Map<Integer, Duration> rules = LayerDelayRules.parse("330:0,332:-5,334:10");
        assertEquals(1, rules.size());
        assertEquals(Duration.ofMinutes(10), rules.get(334));
    }

    @Test
    public void testExitStatusZeroSkipped() {
        // Exit status 0 is success: delaying a layer on every successful frame is nonsense, so
        // the entry is dropped with a warning like any other malformed one.
        Map<Integer, Duration> rules = LayerDelayRules.parse("0:5,330:5");
        assertEquals(1, rules.size());
        assertNull(rules.get(0));
        assertEquals(Duration.ofMinutes(5), rules.get(330));
    }

    @Test
    public void testOverflowingMinutesSkipped() {
        // Long.MAX_VALUE parses as a long but overflows when Duration converts minutes to
        // seconds. The entry must be dropped like any other malformed one rather than throwing
        // out of parse() and failing dispatcher startup.
        Map<Integer, Duration> rules = LayerDelayRules.parse("330:" + Long.MAX_VALUE + ",332:5");
        assertEquals(1, rules.size());
        assertNull(rules.get(330));
        assertEquals(Duration.ofMinutes(5), rules.get(332));
    }

    @Test
    public void testTrailingCommaTolerated() {
        assertEquals(1, LayerDelayRules.parse("330:5,").size());
    }
}
