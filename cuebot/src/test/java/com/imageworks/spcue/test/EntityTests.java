
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

package com.imageworks.spcue.test;

import org.junit.Test;

import com.imageworks.spcue.Entity;

import junit.framework.TestCase;

/**
 * Some tests for the com.imageworks.spcue.Entity class which is the base class for all entities
 * used internally.
 */
public class EntityTests extends TestCase {

    @Test
    public void testEntityEquality() {
        Entity a = new Entity("id", "name");
        Entity b = new Entity("id", "name");
        assertEquals(a, b);

        a = new Entity("id", "name");
        b = new Entity("id_a", "name");
        assertFalse(a.equals(b));

        a = new Entity("id", "name");
        b = new Entity("id_a", "name_a");
        assertFalse(a.equals(b));
    }

    @Test
    public void testEntityHashCode() {

        Entity a = new Entity("id", "name");
        Entity b = new Entity("id", "name");
        assertEquals(a.hashCode(), b.hashCode());

        a = new Entity("id", "name");
        b = new Entity("id_a", "name");
        assertFalse(a.hashCode() == b.hashCode());

        a = new Entity();
        b = new Entity();
        assertFalse(a.hashCode() == b.hashCode());
    }

    @Test
    public void testEntityToString() {
        Entity a = new Entity("id", "name");
        Entity b = new Entity("id", "name");
        assertEquals(a.toString(), b.toString());

        a = new Entity("id_a", "name");
        b = new Entity("id", "name");
        assertNotSame(a.toString(), b.toString());
    }
}
