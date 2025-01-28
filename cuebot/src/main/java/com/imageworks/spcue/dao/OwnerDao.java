
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

import com.imageworks.spcue.Entity;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.OwnerEntity;
import com.imageworks.spcue.ShowInterface;

public interface OwnerDao {

    /**
     * Return true if the given owner owns the particualar host.
     *
     * @param owner
     * @param host
     * @return
     */
    boolean isOwner(OwnerEntity owner, HostInterface host);

    /**
     * Get an owner record by ID.
     *
     * @param id
     */
    OwnerEntity getOwner(String id);

    /**
     * Return the owner of the given host.
     *
     * @param host
     * @return
     */
    OwnerEntity getOwner(HostInterface host);

    /**
     * Return an owner record by name.
     *
     * @param name
     */
    OwnerEntity findOwner(String name);

    /**
     * Delete the specified owner and all his/her deeds. Return true if the owner was actually
     * deleted. False if not.
     */
    boolean deleteOwner(Entity owner);

    /**
     * Insert a new owner record.
     *
     * @param owner
     */
    void insertOwner(OwnerEntity owner, ShowInterface show);

    /**
     * Set the owner's show. This can be null.
     *
     * @param owner
     * @param show
     */
    void updateShow(Entity owner, ShowInterface show);
}
