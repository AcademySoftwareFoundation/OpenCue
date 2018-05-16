
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

import com.imageworks.spcue.AllocationDetail;
import com.imageworks.spcue.Facility;
import com.imageworks.spcue.CueClientIce.Allocation;
import com.imageworks.spcue.CueClientIce._FacilityInterfaceDisp;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.Whiteboard;
import com.imageworks.spcue.util.CueUtil;

public class ManageFacilityI extends _FacilityInterfaceDisp
    implements InitializingBean {

    private final String id;
    private Facility facility;

    private AdminManager adminManager;
    private Whiteboard whiteboard;

    public ManageFacilityI(Ice.Identity i) {
        this.id = i.name;
    }

    @Override
    public void afterPropertiesSet() {
        facility = adminManager.getFacility(id);
    }

    @Override
    public Allocation createAllocation(final String name, final String tag,
            Current __current) throws SpiIceException {

        return new CueIceExceptionTemplate<Allocation>() {
            public Allocation throwOnlyIceExceptions()  {

                String new_name = name;
                // If they pass in a fac.name, then just remove
                // the facility.
                if (CueUtil.verifyAllocationNameFormat(name)) {
                    new_name = CueUtil.splitAllocationName(name)[1];
                }

                AllocationDetail detail = new AllocationDetail();
                detail.name = new_name;
                detail.tag = tag;
                adminManager.createAllocation(facility, detail);
                return whiteboard.getAllocation(detail.id);
            }
        }.execute();
    }

    @Override
    public void delete(Current arg0) throws SpiIceException {
        new CueIceExceptionWrapper() {
            public void throwOnlyIceExceptions()  {
                adminManager.deleteFacility(facility);
            }
        }.execute();
    }

    @Override
    public List<Allocation> getAllocations(Current __current) throws SpiIceException {
        return new CueIceExceptionTemplate<List<Allocation>>() {
            public List<Allocation> throwOnlyIceExceptions()  {
                return whiteboard.getAllocations(facility);
            }
        }.execute();
    }

    @Override
    public void rename(final String name, Current arg1) throws SpiIceException {
        new CueIceExceptionWrapper() {
            public void throwOnlyIceExceptions()  {
                adminManager.setFacilityName(facility, name);
            }
        }.execute();
    }

    public AdminManager getAdminManager() {
        return adminManager;
    }

    public void setAdminManager(AdminManager adminManager) {
        this.adminManager = adminManager;
    }

    public Whiteboard getWhiteboard() {
        return whiteboard;
    }

    public void setWhiteboard(Whiteboard whiteboard) {
        this.whiteboard = whiteboard;
    }
}

