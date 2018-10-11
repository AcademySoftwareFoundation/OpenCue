
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

import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.SubscriptionInterface;
import com.imageworks.spcue.SubscriptionEntity;
import com.imageworks.spcue.VirtualProc;

public interface SubscriptionDao {

    /**
     * returns true if the subscription has running procs
     *
     * @param sub
     * @return
     */
    boolean hasRunningProcs(SubscriptionInterface sub);

    /**
     * Return true if the given show is at or over its size value for the given
     * allocation.
     *
     * @param show
     * @param alloc
     * @return
     */
    boolean isShowAtOrOverSize(ShowInterface show, AllocationInterface alloc);

    /**
     * Return true if the given show is over its size value for the given
     * allocation.
     *
     * @param alloc
     * @param show
     * @return
     */
    boolean isShowOverSize(ShowInterface show, AllocationInterface alloc);

    /**
     * Return true if adding the given coreUnits would put the show over its
     * burst value for the given allocation.
     *
     * @param show
     * @param alloc
     * @param coreUnits
     * @return
     */
    boolean isShowOverBurst(ShowInterface show, AllocationInterface alloc, int coreUnits);

    /**
     * Return true if the given show is at or over its burst value for the given
     * allocation.
     *
     * @param show
     * @param alloc
     * @return
     */
    boolean isShowAtOrOverBurst(ShowInterface show, AllocationInterface alloc);

    /**
     * Return true if the show that is utilizing the given proc has exceeded its
     * burst.
     *
     * @param proc
     * @return
     */
    boolean isShowOverSize(VirtualProc proc);

    /**
     * Return a SubscriptionDetail from its unique id
     *
     * @param id
     * @return
     */
    SubscriptionEntity getSubscriptionDetail(String id);

    /**
     * Insert a new subscription
     *
     * @param detail
     */
    void insertSubscription(SubscriptionEntity detail);

    /**
     * Delete specified subscription
     *
     * @param sub
     */
    void deleteSubscription(SubscriptionInterface sub);

    /**
     * update the size of a subscription
     *
     * @param sub
     * @param size
     */
    void updateSubscriptionSize(SubscriptionInterface sub, int size);

    /**
     * update the subscription burst
     *
     * @param sub
     * @param size
     */
    void updateSubscriptionBurst(SubscriptionInterface sub, int size);
}

