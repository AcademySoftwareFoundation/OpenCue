
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

import java.util.Collection;
import java.util.List;
import java.util.Set;

import com.imageworks.spcue.AllocationEntity;
import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.DepartmentInterface;
import com.imageworks.spcue.FacilityInterface;
import com.imageworks.spcue.LimitInterface;
import com.imageworks.spcue.ShowEntity;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.SubscriptionEntity;
import com.imageworks.spcue.SubscriptionInterface;
import com.imageworks.spcue.grpc.limit.LimitBindSource;
import com.imageworks.spcue.grpc.limit.LimitBinding;
import com.imageworks.spcue.grpc.limit.LimitEnforcement;
import com.imageworks.spcue.grpc.limit.LimitHold;
import com.imageworks.spcue.grpc.limit.LimitReport;
import com.imageworks.spcue.grpc.limit.LimitReportSkip;
import com.imageworks.spcue.grpc.limit.LimitType;

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

    void updateShowsStatus();

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

    AllocationEntity getDefaultAllocation();

    void setDefaultAllocation(AllocationInterface a);

    AllocationEntity findAllocationDetail(String facility, String name);

    AllocationEntity getAllocationDetail(String id);

    void setAllocationBillable(AllocationInterface alloc, boolean value);

    /*
     * Subscriptions
     */
    SubscriptionInterface createSubscription(ShowInterface show, AllocationInterface alloc,
            int size, int burst);

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

    /**
     * Create a limit with full configuration, including an optional failure rule. An exitStatus of
     * null means no rule.
     */
    String createLimit(String name, int maxValue, LimitType type, LimitEnforcement enforcement,
            int softValue, Integer exitStatus, int delayMinutes, boolean autoTag);

    void deleteLimit(LimitInterface limit);

    LimitInterface findLimit(String name);

    /**
     * Returns the subset of the given limit names that have not been created yet.
     *
     * @param names
     * @return names that do not exist
     */
    List<String> findMissingLimitNames(Collection<String> names);

    LimitInterface getLimit(String id);

    void setLimitName(LimitInterface limit, String name);

    void setLimitMaxValue(LimitInterface limit, int maxValue);

    void setLimitType(LimitInterface limit, LimitType type);

    void setLimitEnforcement(LimitInterface limit, LimitEnforcement enforcement);

    void setLimitSoftValue(LimitInterface limit, int softValue);

    void setLimitReportTtl(LimitInterface limit, int seconds);

    /**
     * Set or clear the limit's failure rule. An exitStatus of 0 clears the rule and disables
     * auto-tagging; existing AUTO bindings are left in place. Validates the status per the
     * SetFailureRule contract: must be 0 or greater than 1, and unclaimed by another limit.
     */
    void setLimitFailureRule(LimitInterface limit, int exitStatus, int delayMinutes,
            boolean autoTag);

    List<LimitBinding> getLimitBindings(LimitInterface limit, Set<LimitBindSource> sources,
            Collection<String> layerIds);

    /**
     * Remove AUTO and/or MANUAL bindings from a limit. SPEC bindings are never removed.
     *
     * @return rows removed
     */
    int clearLimitBindings(LimitInterface limit, Set<LimitBindSource> sources);

    /**
     * Apply a batch of license-server reports: replace each named limit's hold set, advance its
     * settlement watermark and refresh its usage row synchronously. Unknown limit names are
     * collected, not thrown.
     */
    LimitReportResult reportLimitUsage(List<LimitReport> reports, String source);

    /** Current token holders, across every limit when limit is null. */
    List<LimitHold> getLimitHolds(LimitInterface limit, String hostName);

    /** Holder for the outcome of a usage report batch. */
    class LimitReportResult {
        public final List<String> appliedLimitIds;
        public final List<String> unknownLimits;
        /** Limits the batch left untouched, with the reason. Not an error. */
        public final List<LimitReportSkip> skippedLimits;

        public LimitReportResult(List<String> appliedLimitIds, List<String> unknownLimits,
                List<LimitReportSkip> skippedLimits) {
            this.appliedLimitIds = appliedLimitIds;
            this.unknownLimits = unknownLimits;
            this.skippedLimits = skippedLimits;
        }
    }
}
