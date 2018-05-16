
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

import com.imageworks.spcue.Allocation;
import com.imageworks.spcue.AllocationDetail;
import com.imageworks.spcue.Department;
import com.imageworks.spcue.Facility;
import com.imageworks.spcue.FacilityEntity;
import com.imageworks.spcue.GroupDetail;
import com.imageworks.spcue.Show;
import com.imageworks.spcue.ShowDetail;
import com.imageworks.spcue.Subscription;
import com.imageworks.spcue.SubscriptionDetail;
import com.imageworks.spcue.dao.AllocationDao;
import com.imageworks.spcue.dao.DepartmentDao;
import com.imageworks.spcue.dao.FacilityDao;
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

    public void setShowActive(Show show, boolean value) {
        showDao.updateActive(show, value);
    }

    public boolean showExists(String name) {
        return showDao.showExists(name);
    }

    public void createShow(ShowDetail show) {

        Department dept = getDefaultDepartment();
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
    public void createAllocation(Facility facility, AllocationDetail alloc) {
        allocationDao.insertAllocation(facility, alloc);
    }

    public void deleteAllocation(Allocation alloc) {
        allocationDao.deleteAllocation(alloc);
    }

    public void setAllocationName(Allocation a, String name) {
        allocationDao.updateAllocationName(a, name);
    }

    @Transactional(propagation = Propagation.NEVER)
    public void setAllocationTag(Allocation a, String tag) {
        allocationDao.updateAllocationTag(a, tag);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public ShowDetail findShowDetail(String name) {
        return showDao.findShowDetail(name);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public ShowDetail getShowDetail(String id) {
        return showDao.getShowDetail(id);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED)
    public void updateShowCommentEmail(Show s, String[] emails) {
        showDao.updateShowCommentEmail(s, emails);
    }

    public Subscription createSubscription(SubscriptionDetail sub) {
        subscriptionDao.insertSubscription(sub);
        return sub;
    }

    public Subscription createSubscription(Show show, Allocation alloc,
            int size, int burst) {
        SubscriptionDetail s = new SubscriptionDetail();
        s.size = size;
        s.burst = burst;
        s.showId = show.getShowId();
        s.allocationId = alloc.getAllocationId();
        subscriptionDao.insertSubscription(s);
        return s;
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public AllocationDetail findAllocationDetail(String facility, String name) {
        return allocationDao.findAllocationDetail(facility, name);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public AllocationDetail getAllocationDetail(String id) {
        return allocationDao.getAllocationDetail(id);
    }

    public void deleteSubscription(Subscription sub) {
        subscriptionDao.deleteSubscription(sub);
    }

    public void setSubscriptionBurst(Subscription sub, int burst) {
        subscriptionDao.updateSubscriptionBurst(sub, burst);
    }

    public void setSubscriptionSize(Subscription sub, int size) {
        subscriptionDao.updateSubscriptionSize(sub, size);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public SubscriptionDetail getSubscriptionDetail(String id) {
        return  subscriptionDao.getSubscriptionDetail(id);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public Department findDepartment(String name) {
        return departmentDao.findDepartment(name);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public Department getDefaultDepartment() {
        return departmentDao.getDefaultDepartment();
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public Department getDepartment(Department d) {
        return departmentDao.getDepartment(d.getDepartmentId());
    }

    @Override
    public Department createDepartment(String name) {
        departmentDao.insertDepartment(name);
        return findDepartment(name);
    }

    @Override
    public void removeDepartment(Department d) {
        departmentDao.deleteDepartment(d);
    }

    @Override
    public Facility createFacility(String name) {
        FacilityEntity facility = new FacilityEntity();
        facility.name = name;
        return facilityDao.insertFacility(facility);
    }

    @Override
    public void deleteFacility(Facility facility) {
        facilityDao.deleteFacility(facility);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public Facility getFacility(String id) {
        return facilityDao.getFacility(id);
    }

    @Override
    public void setFacilityName(Facility facility, String name) {
        facilityDao.updateFacilityName(facility, name);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public Facility getDefaultFacility() {
        return facilityDao.getDefaultFacility();
    }

    @Override
    public void setAllocationBillable(Allocation alloc, boolean value) {
        allocationDao.updateAllocationBillable(alloc, value);
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
}

