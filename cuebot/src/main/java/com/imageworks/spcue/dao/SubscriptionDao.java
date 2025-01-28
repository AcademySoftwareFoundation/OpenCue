
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

import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.SubscriptionEntity;
import com.imageworks.spcue.SubscriptionInterface;
import com.imageworks.spcue.VirtualProc;

public interface SubscriptionDao {

    /**
     * returns true if the subscription has running procs
     *
     * @param sub SubscriptionInterface
     * @return boolean
     */
    boolean hasRunningProcs(SubscriptionInterface sub);

    /**
     * Return true if the given show is at or over its size value for the given allocation.
     *
     * @param show ShowInterface
     * @param alloc AllocationInterface
     * @return boolean
     */
    boolean isShowAtOrOverSize(ShowInterface show, AllocationInterface alloc);

    /**
     * Return true if the given show is over its size value for the given allocation.
     *
     * @param show ShowInterface
     * @param alloc AllocationInterface
     * @return boolean
     */
    boolean isShowOverSize(ShowInterface show, AllocationInterface alloc);

    /**
     * Return true if adding the given coreUnits would put the show over its burst value for the
     * given allocation.
     *
     * @param show ShowInterface
     * @param alloc AllocationInterface
     * @param coreUnits int
     * @return boolean
     */
    boolean isShowOverBurst(ShowInterface show, AllocationInterface alloc, int coreUnits);

    /**
     * Return true if the given show is at or over its burst value for the given allocation.
     *
     * @param show ShowInterface
     * @param alloc AllocationInterface
     * @return boolean
     */
    boolean isShowAtOrOverBurst(ShowInterface show, AllocationInterface alloc);

    /**
     * Return true if the show that is utilizing the given proc has exceeded its burst.
     *
     * @param proc VirtualProc
     * @return boolean
     */
    boolean isShowOverSize(VirtualProc proc);

    /**
     * Return a SubscriptionDetail from its unique id
     *
     * @param id String
     * @return SubscriptionEntity
     */
    SubscriptionEntity getSubscriptionDetail(String id);

    /**
     * Insert a new subscription
     *
     * @param detail SubscriptionEntity
     */
    void insertSubscription(SubscriptionEntity detail);

    /**
     * Delete specified subscription
     *
     * @param sub SubscriptionInterface
     */
    void deleteSubscription(SubscriptionInterface sub);

    /**
     * update the size of a subscription
     *
     * @param sub SubscriptionInterface
     * @param size int
     */
    void updateSubscriptionSize(SubscriptionInterface sub, int size);

    /**
     * update the subscription burst
     *
     * @param sub SubscriptionInterface
     * @param size int
     */
    void updateSubscriptionBurst(SubscriptionInterface sub, int size);
}
