
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

package com.imageworks.spcue.dao.criteria;

public class Sort {

    private final String col;
    private final Direction dir;

    public Sort(String col, Direction dir) {
        this.col = col;
        this.dir = dir;
    }

    public static final Sort asc(String col) {
        return new Sort(col, Direction.ASC);
    }

    public static final Sort desc(String col) {
        return new Sort(col, Direction.DESC);
    }

    public String getColumn() {
        return this.col;
    }

    public Direction getDirection() {
        return this.dir;
    }
}
