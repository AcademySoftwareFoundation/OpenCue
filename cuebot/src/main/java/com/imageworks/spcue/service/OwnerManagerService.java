
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

import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.DeedEntity;
import com.imageworks.spcue.Entity;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.OwnerEntity;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.SpcueRuntimeException;
import com.imageworks.spcue.dao.DeedDao;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dao.OwnerDao;

@Transactional
public class OwnerManagerService implements OwnerManager {

    private OwnerDao ownerDao;
    private DeedDao deedDao;
    private HostDao hostDao;

    @Override
    public OwnerEntity createOwner(String user, ShowInterface show) {
        OwnerEntity owner = new OwnerEntity(user);
        ownerDao.insertOwner(owner, show);
        return owner;
    }

    @Override
    public boolean deleteOwner(Entity owner) {
        return ownerDao.deleteOwner(owner);
    }

    @Override
    public OwnerEntity findOwner(String name) {
        return ownerDao.findOwner(name);
    }

    @Override
    public OwnerEntity getOwner(String id) {
        return ownerDao.getOwner(id);
    }

    @Override
    public void setShow(Entity owner, ShowInterface show) {
        ownerDao.updateShow(owner, show);
    }

    @Override
    public DeedEntity getDeed(String id) {
        return deedDao.getDeed(id);
    }

    @Override
    public DeedEntity takeOwnership(OwnerEntity owner, HostInterface host) {
        if (!hostDao.isNimbyHost(host)) {
            throw new SpcueRuntimeException("Cannot setup deeeds on non-NIMBY hosts.");
        }

        deedDao.deleteDeed(host);
        return deedDao.insertDeed(owner, host);
    }

    @Override
    public void removeDeed(HostInterface host) {
        deedDao.deleteDeed(host);
    }

    @Override
    public void removeDeed(DeedEntity deed) {
        deedDao.deleteDeed(deed);
    }

    @Override
    public boolean isOwner(OwnerEntity owner, HostInterface host) {
        return ownerDao.isOwner(owner, host);
    }

    public OwnerDao getOwnerDao() {
        return ownerDao;
    }

    public void setOwnerDao(OwnerDao ownerDao) {
        this.ownerDao = ownerDao;
    }

    public DeedDao getDeedDao() {
        return deedDao;
    }

    public void setDeedDao(DeedDao deedDao) {
        this.deedDao = deedDao;
    }

    public HostDao getHostDao() {
        return hostDao;
    }

    public void setHostDao(HostDao hostDao) {
        this.hostDao = hostDao;
    }
}
