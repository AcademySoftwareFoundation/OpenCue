
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

/**
 * Describes a simple phrase of a SQL WHERE clause. Examples:
 *
 * column / comparison/ value proc.ts_updated != 123456 user.str_name == 'bob'
 */
public class Phrase {

    private final String column;
    private final String comparison;
    private final String value;

    public Phrase(String column, String comparison, String value) {
        this.column = column;
        this.comparison = comparison;
        this.value = value;
    }

    public String getColumn() {
        return column;
    }

    public String getComparison() {
        return comparison;
    }

    public String getValue() {
        return value;
    }
}
