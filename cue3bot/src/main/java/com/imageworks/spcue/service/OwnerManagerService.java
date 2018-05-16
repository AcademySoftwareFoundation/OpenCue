
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

import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.Deed;
import com.imageworks.spcue.Entity;
import com.imageworks.spcue.Host;
import com.imageworks.spcue.Owner;
import com.imageworks.spcue.Show;
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
    public Owner createOwner(String user, Show show) {
        Owner owner = new Owner(user);
        ownerDao.insertOwner(owner, show);
        return owner;
    }

    @Override
    public boolean deleteOwner(Entity owner) {
        return ownerDao.deleteOwner(owner);
    }

    @Override
    public Owner findOwner(String name) {
        return ownerDao.findOwner(name);
    }

    @Override
    public Owner getOwner(String id) {
        return ownerDao.getOwner(id);
    }

    @Override
    public void setShow(Entity owner, Show show) {
        ownerDao.updateShow(owner, show);
    }

    @Override
    public Deed getDeed(String id) {
        return deedDao.getDeed(id);
    }

    @Override
    public void setBlackoutTime(Deed deed, int startSeconds, int stopSeconds) {
        deedDao.setBlackoutTime(deed, startSeconds, stopSeconds);
    }

    @Override
    public void setBlackoutTimeEnabled(Deed deed, boolean value) {
        deedDao.updateBlackoutTimeEnabled(deed, value);
    }

    @Override
    public Deed takeOwnership(Owner owner, Host host) {
        if (!hostDao.isNimbyHost(host)) {
            throw new SpcueRuntimeException(
                    "Cannot setup deeeds on non-NIMBY hosts.");
        }

        deedDao.deleteDeed(host);
        return deedDao.insertDeed(owner, host);
    }

    @Override
    public void removeDeed(Host host) {
        deedDao.deleteDeed(host);
    }

    @Override
    public void removeDeed(Deed deed) {
        deedDao.deleteDeed(deed);
    }

    @Override
    public boolean isOwner(Owner owner, Host host) {
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

