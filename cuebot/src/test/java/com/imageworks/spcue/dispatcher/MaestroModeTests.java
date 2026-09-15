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

import org.junit.Test;
import org.springframework.mock.env.MockEnvironment;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/** Unit tests for the {@link MaestroMode} tri-state switch. */
public class MaestroModeTests {

    private static MockEnvironment env(String value) {
        return new MockEnvironment().withProperty("maestro.enabled", value);
    }

    @Test
    public void offValues() {
        assertFalse(MaestroMode.enabled(env("no")));
        assertFalse(MaestroMode.enabled(env("false")));
        assertFalse(MaestroMode.enabled(new MockEnvironment())); // unset defaults to no
    }

    @Test
    public void facilityValues() {
        for (String v : new String[] {"facility", "true", "Facility", "TRUE"}) {
            assertTrue(MaestroMode.enabled(env(v)));
            assertTrue(MaestroMode.facility(env(v)));
            assertFalse(MaestroMode.managed(env(v)));
        }
    }

    @Test
    public void managedValue() {
        assertTrue(MaestroMode.enabled(env("managed")));
        assertTrue(MaestroMode.managed(env("managed")));
        assertFalse(MaestroMode.facility(env("managed")));
    }

    @Test
    public void unrecognizedValueFailsSafeToOff() {
        // A typo must never flip dispatch ownership: unknown values count as off.
        assertFalse(MaestroMode.enabled(env("mnaged")));
        assertFalse(MaestroMode.enabled(env("yes")));
        assertFalse(MaestroMode.facility(env("yes")));
        assertFalse(MaestroMode.managed(env("yes")));
    }
}
