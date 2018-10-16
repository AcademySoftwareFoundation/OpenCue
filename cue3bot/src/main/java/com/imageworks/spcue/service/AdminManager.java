
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

import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.AllocationEntity;
import com.imageworks.spcue.Department;
import com.imageworks.spcue.FacilityInterface;
import com.imageworks.spcue.Show;
import com.imageworks.spcue.ShowDetail;
import com.imageworks.spcue.Subscription;
import com.imageworks.spcue.SubscriptionDetail;

public interface AdminManager {

    /*
     * Shows
     */
    boolean showExists(String name);
    void createShow(ShowDetail show);
    ShowDetail findShowDetail(String name);
    ShowDetail getShowDetail(String id);
    void setShowActive(Show show, boolean value);
    void updateShowCommentEmail(Show s, String[] emails);

    /*
     * Facilities
     */
    FacilityInterface createFacility(String name);
    void deleteFacility(FacilityInterface facility);
    void setFacilityName(FacilityInterface facility, String name);
    FacilityInterface getFacility(String id);
    FacilityInterface getDefaultFacility();
    /*
     * Allocations
     */
    void createAllocation(FacilityInterface facility, AllocationEntity alloc);
    void deleteAllocation(AllocationInterface alloc);
    void setAllocationName(AllocationInterface a, String name);
    void setAllocationTag(AllocationInterface a, String tag);
    AllocationEntity findAllocationDetail(String facility, String name);
    AllocationEntity getAllocationDetail(String id);
    void setAllocationBillable(AllocationInterface alloc, boolean value);

    /*
     * Subscriptions
     */
    Subscription createSubscription(Show show, AllocationInterface alloc, int size, int burst);
    Subscription createSubscription(SubscriptionDetail sub);
    void deleteSubscription(Subscription sub);
    void setSubscriptionBurst(Subscription sub, int burst);
    void setSubscriptionSize(Subscription sub, int size);
    SubscriptionDetail getSubscriptionDetail(String id);

    /*
     * Departments
     */
    Department findDepartment(String name);
    Department getDefaultDepartment();
    Department getDepartment(Department d);
    Department createDepartment(String name);
    void removeDepartment(Department d);
}

