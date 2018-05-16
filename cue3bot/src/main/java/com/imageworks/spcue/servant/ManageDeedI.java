
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

import com.imageworks.common.SpiIce.SpiIceException;
import com.imageworks.common.spring.remoting.SpiIceExceptionGenericTemplate;
import com.imageworks.common.spring.remoting.SpiIceExceptionMinimalTemplate;
import com.imageworks.spcue.Deed;
import com.imageworks.spcue.CueClientIce.Host;
import com.imageworks.spcue.CueClientIce.Owner;
import com.imageworks.spcue.CueClientIce._DeedInterfaceDisp;
import com.imageworks.spcue.service.OwnerManager;
import com.imageworks.spcue.service.Whiteboard;

public class ManageDeedI extends _DeedInterfaceDisp implements
    InitializingBean {

    private OwnerManager ownerManager;
    private Whiteboard whiteboard;

    private final String id;
    private Deed deed;

    public ManageDeedI(Ice.Identity i) {
        id = i.name;
    }

    public void afterPropertiesSet() throws Exception {
        deed = ownerManager.getDeed(id);
    }

    @Override
    public Host getHost(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Host>() {
            public Host throwOnlyIceExceptions() throws SpiIceException {
                return whiteboard.getHost(deed);
            }
        }.execute();
    }

    @Override
    public Owner getOwner(Current __curent) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Owner>() {
            public Owner throwOnlyIceExceptions() throws SpiIceException {
                return whiteboard.getOwner(deed);
            }
        }.execute();
    }

    @Override
    public void setBlackoutTimeEnabled(final boolean bool, Current arg1)
            throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                ownerManager.setBlackoutTimeEnabled(deed, bool);
            }
        }.execute();
    }

    @Override
    public void setBlackoutTime(final int epochStart,
            final int epochStop, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                ownerManager.setBlackoutTime(deed, epochStart, epochStart);
            }
        }.execute();
    }

    @Override
    public void delete(Current arg0) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                ownerManager.removeDeed(deed);
            }
        }.execute();
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
}

