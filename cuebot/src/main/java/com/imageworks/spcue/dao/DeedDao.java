
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

package com.imageworks.spcue.dao;

import java.util.List;

import com.imageworks.spcue.DeedEntity;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.OwnerEntity;

public interface DeedDao {

    /**
     * Create a new deed to the host.
     */
    DeedEntity insertDeed(OwnerEntity owner, HostInterface host);

    /**
     * Delete the given deed. Return true if a row was actually deleted, false if one was not.
     *
     * @param deed
     * @return
     */
    boolean deleteDeed(DeedEntity deed);

    /**
     * Delete the given deed. Return true if a row was actually deleted, false if one was not.
     *
     * @param deed
     * @return
     */
    boolean deleteDeed(HostInterface host);

    /**
     * Return the deed by its given id.
     *
     * @param id
     * @return
     */
    DeedEntity getDeed(String id);

    /**
     * Return all deed's from the given owner.
     *
     * @param owner
     * @return
     */
    List<DeedEntity> getDeeds(OwnerEntity owner);

    /**
     *
     *
     * @param owner
     */
    void deleteDeeds(OwnerEntity owner);
}
