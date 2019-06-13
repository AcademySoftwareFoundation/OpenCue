
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

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.ServiceEntity;
import com.imageworks.spcue.ServiceOverrideEntity;
import com.imageworks.spcue.dao.ServiceDao;

/**
 * Manages job services.
 */
@Service
@Transactional
public class ServiceManagerService implements ServiceManager {

    @Autowired
    private ServiceDao serviceDao;

    private static final String DEFAULT_SERVICE = "default";

    @Override
    public void createService(ServiceEntity s) {
        serviceDao.insert(s);
    }

    @Override
    public void createService(ServiceOverrideEntity s) {
        serviceDao.insert(s);
    }

    @Override
    public void deleteService(ServiceEntity s) {
        serviceDao.delete(s);
    }

    @Override
    public void deleteService(ServiceOverrideEntity s) {
        serviceDao.delete(s);
    }


    @Override
    public void updateService(ServiceEntity s) {
        serviceDao.update(s);
    }

    @Override
    public void updateService(ServiceOverrideEntity s) {
        serviceDao.update(s);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public ServiceEntity getService(String id, String show) {
        try {
            return serviceDao.getOverride(id, show);
        } catch (EmptyResultDataAccessException e ) {
            return serviceDao.get(id);
        }
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public ServiceOverrideEntity getServiceOverride(String id) {
        return serviceDao.getOverride(id);
    }


    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public ServiceEntity getService(String id) {
        return serviceDao.get(id);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public ServiceEntity getDefaultService() {
        return serviceDao.get(DEFAULT_SERVICE);
    }

    public ServiceDao getServiceDao() {
        return serviceDao;
    }

    public void setServiceDao(ServiceDao serviceDao) {
        this.serviceDao = serviceDao;
    }
}

