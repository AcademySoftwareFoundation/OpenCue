
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

import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Set;

import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.LogManager;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.AllocationEntity;
import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.DepartmentInterface;
import com.imageworks.spcue.FacilityEntity;
import com.imageworks.spcue.FacilityInterface;
import com.imageworks.spcue.GroupDetail;
import com.imageworks.spcue.LimitEntity;
import com.imageworks.spcue.LimitExitStatusClaimedException;
import com.imageworks.spcue.LimitInterface;
import com.imageworks.spcue.LimitRule;
import com.imageworks.spcue.ShowEntity;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.SubscriptionEntity;
import com.imageworks.spcue.SubscriptionInterface;
import com.imageworks.spcue.dao.AllocationDao;
import com.imageworks.spcue.dao.DepartmentDao;
import com.imageworks.spcue.dao.FacilityDao;
import com.imageworks.spcue.dao.LimitDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.dao.SubscriptionDao;
import com.imageworks.spcue.grpc.limit.LimitBindSource;
import com.imageworks.spcue.grpc.limit.LimitBinding;
import com.imageworks.spcue.grpc.limit.LimitEnforcement;
import com.imageworks.spcue.grpc.limit.LimitHold;
import com.imageworks.spcue.grpc.limit.LimitHostUsage;
import com.imageworks.spcue.grpc.limit.LimitReport;
import com.imageworks.spcue.grpc.limit.LimitReportSkip;
import com.imageworks.spcue.grpc.limit.LimitReportSkipReason;
import com.imageworks.spcue.grpc.limit.LimitType;
import com.imageworks.spcue.service.JobSpec;

@Transactional
public class AdminManagerService implements AdminManager {

    @SuppressWarnings("unused")
    private static final Logger logger = LogManager.getLogger(AdminManagerService.class);

    @Autowired
    private Environment env;

    private ShowDao showDao;

    private AllocationDao allocationDao;

    private SubscriptionDao subscriptionDao;

    private DepartmentDao departmentDao;

    private FacilityDao facilityDao;

    private GroupManager groupManager;

    private LimitDao limitDao;

    public void setShowActive(ShowInterface show, boolean value) {
        showDao.updateActive(show, value);
    }

    public boolean showExists(String name) {
        return showDao.showExists(name);
    }

    public void createShow(ShowEntity show) {

        show.name = JobSpec.conformShowName(show.name);

        DepartmentInterface dept = getDefaultDepartment();
        showDao.insertShow(show);

        /*
         * This is for the show's default group
         */
        GroupDetail newGroup = new GroupDetail();
        newGroup.name = show.getName();
        newGroup.parentId = null;
        newGroup.showId = show.getShowId();
        newGroup.deptId = dept.getId();
        groupManager.createGroup(newGroup, null);
    }

    @Override
    public void createAllocation(FacilityInterface facility, AllocationEntity alloc) {
        allocationDao.insertAllocation(facility, alloc);
    }

    public void deleteAllocation(AllocationInterface alloc) {
        allocationDao.deleteAllocation(alloc);
    }

    public void setAllocationName(AllocationInterface a, String name) {
        allocationDao.updateAllocationName(a, name);
    }

    @Transactional(propagation = Propagation.NEVER)
    public void setAllocationTag(AllocationInterface a, String tag) {
        allocationDao.updateAllocationTag(a, tag);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly = true)
    public AllocationEntity getDefaultAllocation() {
        return allocationDao.getDefaultAllocationEntity();
    }

    @Override
    public void setDefaultAllocation(AllocationInterface a) {
        allocationDao.setDefaultAllocation(a);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly = true)
    public ShowEntity findShowEntity(String name) {
        return showDao.findShowDetail(name);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly = true)
    public ShowEntity getShowEntity(String id) {
        return showDao.getShowDetail(id);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED)
    public void updateShowCommentEmail(ShowInterface s, String[] emails) {
        showDao.updateShowCommentEmail(s, emails);
    }

    @Override
    public void updateShowsStatus() {
        showDao.updateShowsStatus();
    }

    public SubscriptionInterface createSubscription(SubscriptionEntity sub) {
        subscriptionDao.insertSubscription(sub);
        return sub;
    }

    public SubscriptionInterface createSubscription(ShowInterface show, AllocationInterface alloc,
            int size, int burst) {
        SubscriptionEntity s = new SubscriptionEntity();
        s.size = size;
        s.burst = burst;
        s.showId = show.getShowId();
        s.allocationId = alloc.getAllocationId();
        subscriptionDao.insertSubscription(s);
        return s;
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly = true)
    public AllocationEntity findAllocationDetail(String facility, String name) {
        return allocationDao.findAllocationEntity(facility, name);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly = true)
    public AllocationEntity getAllocationDetail(String id) {
        return allocationDao.getAllocationEntity(id);
    }

    public void deleteSubscription(SubscriptionInterface sub) {
        subscriptionDao.deleteSubscription(sub);
    }

    public void setSubscriptionBurst(SubscriptionInterface sub, int burst) {
        subscriptionDao.updateSubscriptionBurst(sub, burst);
    }

    public void setSubscriptionSize(SubscriptionInterface sub, int size) {
        subscriptionDao.updateSubscriptionSize(sub, size);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly = true)
    public SubscriptionEntity getSubscriptionDetail(String id) {
        return subscriptionDao.getSubscriptionDetail(id);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly = true)
    public DepartmentInterface findDepartment(String name) {
        return departmentDao.findDepartment(name);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly = true)
    public DepartmentInterface getDefaultDepartment() {
        return departmentDao.getDefaultDepartment();
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly = true)
    public DepartmentInterface getDepartment(DepartmentInterface d) {
        return departmentDao.getDepartment(d.getDepartmentId());
    }

    @Override
    public DepartmentInterface createDepartment(String name) {
        departmentDao.insertDepartment(name);
        return findDepartment(name);
    }

    @Override
    public void removeDepartment(DepartmentInterface d) {
        departmentDao.deleteDepartment(d);
    }

    @Override
    public FacilityInterface createFacility(String name) {
        FacilityEntity facility = new FacilityEntity();
        facility.name = name;
        return facilityDao.insertFacility(facility);
    }

    @Override
    public void deleteFacility(FacilityInterface facility) {
        facilityDao.deleteFacility(facility);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly = true)
    public FacilityInterface getFacility(String id) {
        return facilityDao.getFacility(id);
    }

    @Override
    public void setFacilityName(FacilityInterface facility, String name) {
        facilityDao.updateFacilityName(facility, name);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly = true)
    public FacilityInterface getDefaultFacility() {
        return facilityDao.getDefaultFacility();
    }

    @Override
    public void setAllocationBillable(AllocationInterface alloc, boolean value) {
        allocationDao.updateAllocationBillable(alloc, value);
    }

    @Override
    public String createLimit(String name, int maxValue) {
        return limitDao.createLimit(name, maxValue, LimitType.FRAME, LimitEnforcement.ENFORCED, -1);
    }

    @Override
    public String createLimit(String name, int maxValue, LimitType type,
            LimitEnforcement enforcement, int softValue, Integer exitStatus, int delayMinutes,
            boolean autoTag) {
        String limitId = limitDao.createLimit(name, maxValue, type, enforcement, softValue);
        if (exitStatus != null && exitStatus != 0) {
            setLimitFailureRule(limitDao.getLimit(limitId), exitStatus, delayMinutes, autoTag);
        }
        return limitId;
    }

    public void deleteLimit(LimitInterface limit) {
        limitDao.deleteLimit(limit);
    }

    @Override
    public LimitInterface findLimit(String name) {
        return limitDao.findLimit(name);
    }

    @Override
    public List<String> findMissingLimitNames(Collection<String> names) {
        return limitDao.findMissingLimitNames(names);
    }

    @Override
    public LimitInterface getLimit(String id) {
        return limitDao.getLimit(id);
    }

    @Override
    public void setLimitName(LimitInterface limit, String name) {
        limitDao.setLimitName(limit, name);
    }

    @Override
    public void setLimitMaxValue(LimitInterface limit, int maxValue) {
        limitDao.setMaxValue(limit, maxValue);
    }

    @Override
    public void setLimitType(LimitInterface limit, LimitType type) {
        limitDao.setLimitType(limit, type);
    }

    @Override
    public void setLimitEnforcement(LimitInterface limit, LimitEnforcement enforcement) {
        limitDao.setEnforcement(limit, enforcement);
    }

    @Override
    public void setLimitSoftValue(LimitInterface limit, int softValue) {
        limitDao.setSoftValue(limit, softValue);
    }

    @Override
    public void setLimitReportTtl(LimitInterface limit, int seconds) {
        limitDao.setReportTtl(limit, seconds);
    }

    @Override
    public void setLimitFailureRule(LimitInterface limit, int exitStatus, int delayMinutes,
            boolean autoTag) {
        if (delayMinutes < 0) {
            throw new IllegalArgumentException("delay minutes must be >= 0");
        }
        if (exitStatus == 0) {
            // Clear the rule. Existing AUTO bindings are left in place: turning a rule off is
            // not the same as declaring everything it learned to be wrong.
            limitDao.setFailureRule(limit, null, delayMinutes, autoTag);
            return;
        }
        if (exitStatus <= 1) {
            // Status 0 is success and 1 is the conventional catch-all failure; claiming either
            // would tag nearly every failing layer on the farm.
            throw new IllegalArgumentException("Exit status must be greater than 1: status 0 is "
                    + "success and status 1 is the generic failure code.");
        }
        LimitRule claimed = limitDao.getFailureRules().get(exitStatus);
        if (claimed != null && !claimed.limitId.equals(limit.getLimitId())) {
            throw new LimitExitStatusClaimedException(exitStatus, claimed.limitName);
        }
        limitDao.setFailureRule(limit, exitStatus, delayMinutes, autoTag);
    }

    @Override
    public List<LimitBinding> getLimitBindings(LimitInterface limit, Set<LimitBindSource> sources,
            Collection<String> layerIds) {
        return limitDao.getBindings(limit, sources, layerIds);
    }

    @Override
    public int clearLimitBindings(LimitInterface limit, Set<LimitBindSource> sources) {
        if (sources != null && sources.contains(LimitBindSource.SPEC)) {
            throw new IllegalArgumentException(
                    "SPEC bindings are declared by the submitter and cannot be bulk-removed.");
        }
        return limitDao.clearBindings(limit, sources);
    }

    @Override
    public LimitReportResult reportLimitUsage(List<LimitReport> reports, String source) {
        long now = System.currentTimeMillis();
        long minIntervalMs =
                1000L * env.getProperty("limit.min_report_interval_seconds", Integer.class, 5);

        List<String> applied = new ArrayList<String>();
        List<String> unknown = new ArrayList<String>();
        List<LimitReportSkip> skipped = new ArrayList<LimitReportSkip>();

        // A malformed snapshot is a reporter bug, not a race, so it rejects the whole request.
        // Validate every report before writing anything: this class is @Transactional, and
        // throwing mid-loop would silently roll back the limits already applied.
        for (LimitReport report : reports) {
            for (LimitHostUsage hold : report.getHostsList()) {
                if (hold.getTokens() <= 0) {
                    throw new IllegalArgumentException(
                            "Host " + hold.getHostName() + " in limit " + report.getLimitName()
                                    + " reports tokens <= 0; omit hosts holding nothing.");
                }
            }
        }

        for (LimitReport report : reports) {
            LimitEntity limit;
            try {
                limit = limitDao.findLimit(report.getLimitName());
            } catch (EmptyResultDataAccessException e) {
                unknown.add(report.getLimitName());
                continue;
            }

            // The watermark decides which bookings count as pending; a reporter-supplied capture
            // time keeps it accurate when the reporter itself is slow. Never let it run ahead of
            // the clock.
            long captureMs =
                    report.getCaptureTime() > 0 ? Math.min(report.getCaptureTime() * 1000L, now)
                            : now;

            // Applying a snapshot older than the watermark would move ts_reported backwards,
            // which disarms the interval check and reads as stale at once -- the limit would
            // stop blocking immediately after a report landed. Checked before the interval so a
            // reporter that is both late and skewed hears about the clock, which is the durable
            // problem, rather than about a race that will clear on its own.
            if (captureMs < limit.reportedTime) {
                skipped.add(skip(limit.name, LimitReportSkipReason.OUT_OF_ORDER));
                continue;
            }

            // Losing the race to another reporter is normal and concerns only this limit; the
            // rest of the batch must still apply or they drift stale and stop blocking.
            if (limit.reportedTime > 0 && now - limit.reportedTime < minIntervalMs) {
                skipped.add(skip(limit.name, LimitReportSkipReason.RATE_LIMITED));
                continue;
            }
            Timestamp captureTime = new Timestamp(captureMs);

            // The checks above read the watermark without a lock, so two concurrent reporters
            // can both pass them. The conditional update is the authoritative admission: the
            // loser blocks on the row, re-evaluates against the winner's watermark, and skips.
            if (!limitDao.claimReportWatermark(limit, captureTime, source, minIntervalMs)) {
                long winner = limitDao.getLimit(limit.getLimitId()).reportedTime;
                skipped.add(skip(limit.name, captureMs < winner ? LimitReportSkipReason.OUT_OF_ORDER
                        : LimitReportSkipReason.RATE_LIMITED));
                continue;
            }

            limitDao.replaceExternalHolds(limit, report.getHostsList(), source, captureTime);
            if (report.getTotalLicenses() > 0) {
                limitDao.setMaxValue(limit, report.getTotalLicenses());
            }
            // Synchronous refresh so the report takes effect on the next dispatch, not the next
            // maintenance tick.
            limitDao.refreshUsage(limit);
            applied.add(limit.getLimitId());
        }
        return new LimitReportResult(applied, unknown, skipped);
    }

    private static LimitReportSkip skip(String limitName, LimitReportSkipReason reason) {
        return LimitReportSkip.newBuilder().setLimitName(limitName).setReason(reason).build();
    }

    @Override
    public List<LimitHold> getLimitHolds(LimitInterface limit, String hostName) {
        return limit == null ? limitDao.getHolds(hostName) : limitDao.getHolds(limit, hostName);
    }

    public AllocationDao getAllocationDao() {
        return allocationDao;
    }

    public void setAllocationDao(AllocationDao allocationDao) {
        this.allocationDao = allocationDao;
    }

    public ShowDao getShowDao() {
        return showDao;
    }

    public void setShowDao(ShowDao showDao) {
        this.showDao = showDao;
    }

    public SubscriptionDao getSubscriptionDao() {
        return subscriptionDao;
    }

    public void setSubscriptionDao(SubscriptionDao subscriptionDao) {
        this.subscriptionDao = subscriptionDao;
    }

    public DepartmentDao getDepartmentDao() {
        return departmentDao;
    }

    public void setDepartmentDao(DepartmentDao departmentDao) {
        this.departmentDao = departmentDao;
    }

    public GroupManager getGroupManager() {
        return groupManager;
    }

    public void setGroupManager(GroupManager groupManager) {
        this.groupManager = groupManager;
    }

    public FacilityDao getFacilityDao() {
        return facilityDao;
    }

    public void setFacilityDao(FacilityDao facilityDao) {
        this.facilityDao = facilityDao;
    }

    public LimitDao getLimitDao() {
        return limitDao;
    }

    public void setLimitDao(LimitDao limitDao) {
        this.limitDao = limitDao;
    }
}
