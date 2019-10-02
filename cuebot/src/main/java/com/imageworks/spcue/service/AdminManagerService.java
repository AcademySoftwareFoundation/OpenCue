
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

import org.apache.log4j.Logger;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.AllocationEntity;
import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.DepartmentInterface;
import com.imageworks.spcue.FacilityEntity;
import com.imageworks.spcue.FacilityInterface;
import com.imageworks.spcue.GroupDetail;
import com.imageworks.spcue.LimitInterface;
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

@Transactional
public class AdminManagerService implements AdminManager {

    @SuppressWarnings("unused")
    private static final Logger logger = Logger.getLogger(AdminManagerService.class);

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
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public ShowEntity findShowEntity(String name) {
        return showDao.findShowDetail(name);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public ShowEntity getShowEntity(String id) {
        return showDao.getShowDetail(id);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED)
    public void updateShowCommentEmail(ShowInterface s, String[] emails) {
        showDao.updateShowCommentEmail(s, emails);
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
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public AllocationEntity findAllocationDetail(String facility, String name) {
        return allocationDao.findAllocationEntity(facility, name);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
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
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public SubscriptionEntity getSubscriptionDetail(String id) {
        return  subscriptionDao.getSubscriptionDetail(id);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public DepartmentInterface findDepartment(String name) {
        return departmentDao.findDepartment(name);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public DepartmentInterface getDefaultDepartment() {
        return departmentDao.getDefaultDepartment();
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
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
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public FacilityInterface getFacility(String id) {
        return facilityDao.getFacility(id);
    }

    @Override
    public void setFacilityName(FacilityInterface facility, String name) {
        facilityDao.updateFacilityName(facility, name);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public FacilityInterface getDefaultFacility() {
        return facilityDao.getDefaultFacility();
    }

    @Override
    public void setAllocationBillable(AllocationInterface alloc, boolean value) {
        allocationDao.updateAllocationBillable(alloc, value);
    }

    @Override
    public String createLimit(String name, int maxValue) {
        return limitDao.createLimit(name, maxValue);
    }

    public void deleteLimit(LimitInterface limit) {
        limitDao.deleteLimit(limit);
    }

    @Override
    public LimitInterface findLimit(String name) {
        return limitDao.findLimit(name);
    }

    @Override
    public LimitInterface getLimit(String id){
        return limitDao.getLimit(id);
    }

    @Override
    public void setLimitName(LimitInterface limit, String name){
        limitDao.setLimitName(limit, name);
    }

    @Override
    public void setLimitMaxValue(LimitInterface limit, int maxValue) {
        limitDao.setMaxValue(limit, maxValue);
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

