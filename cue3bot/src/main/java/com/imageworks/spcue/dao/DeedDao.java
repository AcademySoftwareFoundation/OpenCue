
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

import java.util.List;

import com.imageworks.spcue.Deed;
import com.imageworks.spcue.Host;
import com.imageworks.spcue.Owner;

public interface DeedDao {

    /**
     * Create a new deed to the host.
     */
    Deed insertDeed(Owner owner, Host host);

    /**
     * Delete the given deed. Return true if a row was
     * actually deleted, false if one was not.
     *
     * @param deed
     * @return
     */
    boolean deleteDeed(Deed deed);

    /**
     * Delete the given deed. Return true if a row was
     * actually deleted, false if one was not.
     *
     * @param deed
     * @return
     */
    boolean deleteDeed(Host host);

    /**
     * Return the deed by its given id.
     *
     * @param id
     * @return
     */
    Deed getDeed(String id);

    /**
     * Return all deed's from the given owner.
     *
     * @param owner
     * @return
     */
    List<Deed> getDeeds(Owner owner);

    /**
     * Enable/Disable the blackout time.
     *
     * @param value
     */
    void updateBlackoutTimeEnabled(Deed deed, boolean value);

    /**
     * Set blackout times.  During blackout times, machines
     * cannot be booked.
     *
     * @param start
     * @param stop
     */
    void setBlackoutTime(Deed deed, int startSeconds, int stopSeconds);

    /**
     *
     *
     * @param owner
     */
    void deleteDeeds(Owner owner);
}

