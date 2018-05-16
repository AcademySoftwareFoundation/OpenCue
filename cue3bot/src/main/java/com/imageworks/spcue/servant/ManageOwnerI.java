
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
import com.imageworks.spcue.CueClientIce.Deed;
import com.imageworks.spcue.CueClientIce.Host;
import com.imageworks.spcue.Owner;
import com.imageworks.spcue.CueClientIce._OwnerInterfaceDisp;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.OwnerManager;
import com.imageworks.spcue.service.Whiteboard;

public class ManageOwnerI extends _OwnerInterfaceDisp
    implements InitializingBean {

    private HostManager hostManager;
    private OwnerManager ownerManager;
    private Whiteboard whiteboard;
    private AdminManager adminManager;

    /**
     * The owner record unique Id
     */
    private final String id;
    private Owner owner;

    public ManageOwnerI(Ice.Identity i) {
        id = i.name;
    }

    public void afterPropertiesSet() throws Exception {
        owner = ownerManager.getOwner(id);
    }

    @Override
    public void delete(Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                ownerManager.deleteOwner(owner);
            }
        }.execute();
    }

    @Override
    public List<Deed> getDeeds(Current arg0) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Deed>>() {
            public List<Deed> throwOnlyIceExceptions() throws SpiIceException {
                return whiteboard.getDeeds(owner);
            }
        }.execute();
    }


    @Override
    public List<Host> getHosts(Current arg0) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Host>>() {
            public List<Host> throwOnlyIceExceptions() throws SpiIceException {
                return whiteboard.getHosts(owner);
            }
        }.execute();
    }

    @Override
    public void takeOwnership(final String host, Current __current)
            throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                ownerManager.takeOwnership(owner,
                        hostManager.findHost(host));
            }
        }.execute();
    }

    @Override
    public void setShow(final String show, Current arg1)
            throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                ownerManager.setShow(owner,
                        adminManager.findShowDetail(show));
            }
        }.execute();
    }

    public HostManager getHostManager() {
        return hostManager;
    }

    public void setHostManager(HostManager hostManager) {
        this.hostManager = hostManager;
    }

    public OwnerManager getOwnerManager() {
        return ownerManager;
    }

    public void setOwnerManager(OwnerManager ownerManager) {
        this.ownerManager = ownerManager;
    }

    public Whiteboard getWhiteboard() {
        return whiteboard;
    }

    public void setWhiteboard(Whiteboard whiteboard) {
        this.whiteboard = whiteboard;
    }

    public AdminManager getAdminManager() {
        return adminManager;
    }

    public void setAdminManager(AdminManager adminManager) {
        this.adminManager = adminManager;
    }
}

