
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

import com.imageworks.spcue.AllocationEntity;
import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.FacilityInterface;

/**
 * Allocation DAO
 *
 * @category DAO
 */
public interface AllocationDao {

    /**
     * returns an AllocationEntity from its unique ID
     *
     * @param id
     * @return AllocationEntity
     */
    AllocationEntity getAllocationEntity(String id);

    /**
     * Return an AllocationEntity for the given facility and unique allocation name.
     *
     * @param name
     * @return AllocationEntity
     */
    AllocationEntity findAllocationEntity(String facility, String name);

    /**
     * Return an AllocationEntity from its fully qualified name which should be formatted as
     * facility.name.
     *
     * @param name
     * @return
     */
    AllocationEntity findAllocationEntity(String name);

    /**
     * Creates a new allocation
     *
     * @param detail
     */
    void insertAllocation(FacilityInterface facility, AllocationEntity detail);

    /**
     * Deletes an allocation
     *
     * @param alloc
     */
    void deleteAllocation(AllocationInterface alloc);

    /**
     * Updates the name of the allocation. This method also updates all child host allocation tags
     * so you'll need to run allocDao.recalculateTags(alloc)
     *
     * @param alloc
     * @param name
     */
    void updateAllocationName(AllocationInterface alloc, String name);

    /**
     * Updates the allocation tag. All hosts in the allocation are retagged.
     *
     * @param a
     * @param tag
     */
    void updateAllocationTag(AllocationInterface a, String tag);

    /**
     * Sets the default allocation, AKA where procs go first.
     *
     * @param a
     */
    void setDefaultAllocation(AllocationInterface a);

    /**
     * Returns the current default allocation.
     *
     * @return
     */
    AllocationEntity getDefaultAllocationEntity();

    /**
     * Set the allocation as billable or not billble.
     *
     * @param alloc
     * @param value
     */
    void updateAllocationBillable(AllocationInterface alloc, boolean value);
}
