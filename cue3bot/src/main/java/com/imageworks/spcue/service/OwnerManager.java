
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



package com.imageworks.spcue.service;

import com.imageworks.spcue.Deed;
import com.imageworks.spcue.Entity;
import com.imageworks.spcue.Host;
import com.imageworks.spcue.Owner;
import com.imageworks.spcue.Show;

public interface OwnerManager {

    /**
     * Return true if the given users owns the particular host.
     *
     * @param owner
     * @param host
     * @return
     */
    boolean isOwner(Owner owner, Host host);

    /**
     * Create a new owner.
     *
     * @param user
     * @param email
     */
    Owner createOwner(String user, Show show);

    /**
     * Get an owner record by ID.
     *
     * @param id
     */
    Owner getOwner(String id);

    /**
     * Return an owner record by name.
     *
     * @param name
     */
    Owner findOwner(String name);

    /**
     * Delete the specified owner and all his/her deeds.
     * Return true if the owner was actually deleted.
     * False if not.
     */
    boolean deleteOwner(Entity owner);

    /**
     * Set the show of the given user.
     *
     * @param owner
     * @param show
     */
    void setShow(Entity owner, Show show);

    /**
     * Assigns the given host to the owner.
     *
     * @param owner
     * @param host
     */
    Deed takeOwnership(Owner owner, Host host);

    /**
     *
     * @param deed
     * @param value
     */
    void setBlackoutTimeEnabled(Deed deed, boolean value);

    /**
     *
     * @param id
     * @return
     */
    Deed getDeed(String id);

    /**
     *
     * @param deed
     * @param startSeconds
     * @param stopSeconds
     */
    void setBlackoutTime(Deed deed, int startSeconds, int stopSeconds);

    /**
     * Deletes a deed for the specified host.
     *
     * @param host
     */
    void removeDeed(Host host);

    /**
     * Remove the given deed.
     *
     * @param deed
     */
    void removeDeed(Deed deed);
}

