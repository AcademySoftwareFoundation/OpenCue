
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



package com.imageworks.spcue.servant;

import org.springframework.beans.factory.InitializingBean;

import Ice.Current;

import com.google.common.collect.Sets;
import com.imageworks.common.SpiIce.SpiIceException;
import com.imageworks.common.spring.remoting.SpiIceExceptionMinimalTemplate;
import com.imageworks.spcue.Service;
import com.imageworks.spcue.CueClientIce.ServiceData;
import com.imageworks.spcue.CueClientIce._ServiceInterfaceDisp;
import com.imageworks.spcue.service.ServiceManager;

public class ManageServiceI extends _ServiceInterfaceDisp
    implements InitializingBean {

    private static final long serialVersionUID = 1L;
    private ServiceManager serviceManager;

    private final String id;
    private Service service;

    public ManageServiceI(Ice.Identity i) {
        id = i.name;
    }

    @Override
    public void delete(Current arg0) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                serviceManager.deleteService(service);
            }
        }.execute();
    }

    @Override
    public void update(final ServiceData update, Current arg1) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                Service updated = new Service();
                updated.id = service.id;
                updated.name = update.name;
                updated.minCores = update.minCores;
                updated.maxCores = update.maxCores;
                updated.minMemory = update.minMemory;
                updated.minGpu = update.minGpu;
                updated.tags = Sets.newLinkedHashSet(update.tags);
                updated.threadable = update.threadable;
                serviceManager.updateService(updated);
            }
        }.execute();
    }

    @Override
    public void afterPropertiesSet() throws Exception {
        service = serviceManager.getService(id);
    }

    public ServiceManager getServiceManager() {
        return serviceManager;
    }

    public void setServiceManager(ServiceManager serviceManager) {
        this.serviceManager = serviceManager;
    }
}

