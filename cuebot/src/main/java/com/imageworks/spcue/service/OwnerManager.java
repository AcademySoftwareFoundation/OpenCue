
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

package com.imageworks.spcue.service;

import com.imageworks.spcue.DeedEntity;
import com.imageworks.spcue.Entity;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.OwnerEntity;
import com.imageworks.spcue.ShowInterface;

public interface OwnerManager {

    /**
     * Return true if the given users owns the particular host.
     *
     * @param owner
     * @param host
     * @return
     */
    boolean isOwner(OwnerEntity owner, HostInterface host);

    /**
     * Create a new owner.
     *
     * @param user
     * @param email
     */
    OwnerEntity createOwner(String user, ShowInterface show);

    /**
     * Get an owner record by ID.
     *
     * @param id
     */
    OwnerEntity getOwner(String id);

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
     * Set the show of the given user.
     *
     * @param owner
     * @param show
     */
    void setShow(Entity owner, ShowInterface show);

    /**
     * Assigns the given host to the owner.
     *
     * @param owner
     * @param host
     */
    DeedEntity takeOwnership(OwnerEntity owner, HostInterface host);

    /**
     *
     * @param id
     * @return
     */
    DeedEntity getDeed(String id);

    /**
     * Deletes a deed for the specified host.
     *
     * @param host
     */
    void removeDeed(HostInterface host);

    /**
     * Remove the given deed.
     *
     * @param deed
     */
    void removeDeed(DeedEntity deed);
}
