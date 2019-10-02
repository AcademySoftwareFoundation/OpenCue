
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

import com.imageworks.spcue.AllocationEntity;
import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.DepartmentInterface;
import com.imageworks.spcue.FacilityInterface;
import com.imageworks.spcue.LimitInterface;
import com.imageworks.spcue.ShowEntity;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.SubscriptionEntity;
import com.imageworks.spcue.SubscriptionInterface;

public interface AdminManager {

    /*
     * Shows
     */
    boolean showExists(String name);
    void createShow(ShowEntity show);
    ShowEntity findShowEntity(String name);
    ShowEntity getShowEntity(String id);
    void setShowActive(ShowInterface show, boolean value);
    void updateShowCommentEmail(ShowInterface s, String[] emails);

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
    SubscriptionInterface createSubscription(ShowInterface show, AllocationInterface alloc, int size, int burst);
    SubscriptionInterface createSubscription(SubscriptionEntity sub);
    void deleteSubscription(SubscriptionInterface sub);
    void setSubscriptionBurst(SubscriptionInterface sub, int burst);
    void setSubscriptionSize(SubscriptionInterface sub, int size);
    SubscriptionEntity getSubscriptionDetail(String id);

    /*
     * Departments
     */
    DepartmentInterface findDepartment(String name);
    DepartmentInterface getDefaultDepartment();
    DepartmentInterface getDepartment(DepartmentInterface d);
    DepartmentInterface createDepartment(String name);
    void removeDepartment(DepartmentInterface d);

    /*
     * Limits
     */
    String createLimit(String name, int maxValue);
    void deleteLimit(LimitInterface limit);
    LimitInterface findLimit(String name);
    LimitInterface getLimit(String id);
    void setLimitName(LimitInterface limit, String name);
    void setLimitMaxValue(LimitInterface limit, int maxValue);

}

