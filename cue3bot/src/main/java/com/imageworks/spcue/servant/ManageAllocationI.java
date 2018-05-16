
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

import java.util.List;

import org.springframework.beans.factory.InitializingBean;

import Ice.Current;

import com.imageworks.common.SpiIce.SpiIceException;
import com.imageworks.common.spring.remoting.SpiIceExceptionGenericTemplate;
import com.imageworks.common.spring.remoting.SpiIceExceptionMinimalTemplate;
import com.imageworks.spcue.AllocationDetail;
import com.imageworks.spcue.CueClientIce.Host;
import com.imageworks.spcue.CueClientIce.HostInterfacePrx;
import com.imageworks.spcue.CueClientIce.HostSearchCriteria;
import com.imageworks.spcue.CueClientIce.Subscription;
import com.imageworks.spcue.CueClientIce._AllocationInterfaceDisp;
import com.imageworks.spcue.dao.AllocationDao;
import com.imageworks.spcue.dao.criteria.HostSearch;
import com.imageworks.spcue.dispatcher.DispatchQueue;
import com.imageworks.spcue.dispatcher.commands.ManageReparentHosts;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.Whiteboard;

public class ManageAllocationI  extends _AllocationInterfaceDisp implements InitializingBean {

    private final String id;
    private AllocationDetail allocation;
    private AllocationDao allocationDao;
    private DispatchQueue manageQueue;
    private Whiteboard whiteboard;
    private AdminManager adminManager;
    private HostManager hostManager;

    public ManageAllocationI(Ice.Identity i) {
        this.id = i.name;
    }

    @Override
    public Ice.DispatchStatus __dispatch(IceInternal.Incoming in,
                                         Current current) {
        ServantInterceptor.__dispatch(this, in, current);
        return super.__dispatch(in, current);
    }

    @Override
    public void afterPropertiesSet() throws Exception {
        allocation = allocationDao.getAllocationDetail(id);
    }

    @Override
    public void setName(final String name, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                adminManager.setAllocationName(allocation, name);
            }
        }.execute();
    }

    @Override
    public void setTag(final String tag, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                adminManager.setAllocationTag(allocation,tag);
            }
        }.execute();
    }

    @Override
    public void delete(Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                adminManager.deleteAllocation(allocation);
            }
        }.execute();
    }

    @Override
    public void reparentHosts(final List<HostInterfacePrx> hosts, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                manageQueue.execute(new ManageReparentHosts(allocation,
                        ServantUtil.convertHostProxyList(hosts), hostManager));
            }
        }.execute();
    }

    @Override
    public List<Subscription> getSubscriptions(Current arg0)
            throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Subscription>>() {
            public List<Subscription> throwOnlyIceExceptions() {
                return whiteboard.getSubscriptions(allocation);
            }
        }.execute();
    }

    @Override
    public List<Host> findHosts(final HostSearchCriteria r, Current arg1)
            throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Host>>() {
            public List<Host> throwOnlyIceExceptions() {
                r.allocs.add(allocation.getAllocationId());
                return whiteboard.getHosts(new HostSearch(r));
            }
        }.execute();
    }

    @Override
    public List<Host> getHosts(Current arg0) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Host>>() {
            public List<Host> throwOnlyIceExceptions() {
                return whiteboard.getHosts(HostSearch.byAllocation(allocation));
            }
        }.execute();
    }

    @Override
    public void setBillable(final boolean value, Current arg1) throws SpiIceException {
        new CueIceExceptionWrapper() {
            public void throwOnlyIceExceptions()  {
                adminManager.setAllocationBillable(allocation, value);
            }
        }.execute();
    }

    public AdminManager getAdminManager() {
        return adminManager;
    }

    public void setAdminManager(AdminManager adminManager) {
        this.adminManager = adminManager;
    }

    public AllocationDao getAllocationDao() {
        return allocationDao;
    }

    public void setAllocationDao(AllocationDao allocationDao) {
        this.allocationDao = allocationDao;
    }

    public DispatchQueue getManageQueue() {
        return manageQueue;
    }

    public void setManageQueue(DispatchQueue manageQueue) {
        this.manageQueue = manageQueue;
    }

    public Whiteboard getWhiteboard() {
        return whiteboard;
    }

    public void setWhiteboard(Whiteboard whiteboard) {
        this.whiteboard = whiteboard;
    }

    public HostManager getHostManager() {
        return hostManager;
    }

    public void setHostManager(HostManager hostManager) {
        this.hostManager = hostManager;
    }
}

