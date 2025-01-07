
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

import com.imageworks.spcue.FacilityEntity;
import com.imageworks.spcue.FacilityInterface;

public interface FacilityDao {

    /**
     * Returns the default facility
     *
     * @return
     */
    public FacilityInterface getDefaultFacility();

    /**
     * Gets a facility by Id
     *
     * @param id
     * @return
     */
    public FacilityInterface getFacility(String id);

    /**
     * Returns true if a facility exists
     *
     * @param name
     * @return
     */
    public boolean facilityExists(String name);

    /**
     * Insert and return a facility.
     *
     * @param name
     * @return
     */
    public FacilityInterface insertFacility(FacilityEntity facility);

    /**
     * Deletes a facility record, if possible.
     *
     * @param facility
     * @return
     */
    public int deleteFacility(FacilityInterface facility);

    /**
     * Rename the specified facility.
     *
     * @param facility
     * @param name
     * @return
     */
    int updateFacilityName(FacilityInterface facility, String name);
}
