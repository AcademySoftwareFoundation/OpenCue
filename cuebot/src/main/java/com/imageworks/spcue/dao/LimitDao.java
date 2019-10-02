
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



package com.imageworks.spcue.dao;

import com.imageworks.spcue.LimitEntity;
import com.imageworks.spcue.LimitInterface;

public interface LimitDao {

    /**
     * Insert and return a facility.
     *
     * @param limit
     * @return
     */
    public String createLimit(String name, int maxValue);

    /**
     * Deletes a limit record, if possible.
     *
     * @param limit
     * @return
     */
    public void deleteLimit(LimitInterface limit);

    /**
     * Find a limit by it's name
     *
     * @param name
     * @return LimitEntity
     */
    public LimitEntity findLimit(String name);

    /**
     * Gets a limit by Id
     *
     * @param id
     * @return LimitEntity
     */
    public LimitEntity getLimit(String id);

    /**
     * Set the specified limit's name.
     *
     * @param limit
     * @param name
     * @return
     */
    public void setLimitName(LimitInterface limit, String name);

    /**
     * Set the specified limit's max value.
     *
     * @param limit
     * @param value
     * @return
     */
    public void setMaxValue(LimitInterface limit, int value);
}
