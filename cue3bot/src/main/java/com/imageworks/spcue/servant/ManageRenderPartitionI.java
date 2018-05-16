
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
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.CueClientIce._RenderPartitionInterfaceDisp;
import com.imageworks.spcue.CueIce.CueIceException;
import com.imageworks.spcue.service.BookingManager;

public class ManageRenderPartitionI extends _RenderPartitionInterfaceDisp
    implements InitializingBean {

    private final String id;
    private LocalHostAssignment localJobAssign;

    private BookingManager bookingManager;

    public ManageRenderPartitionI(Ice.Identity i) {
        id = i.name;
    }

    @Override
    public void afterPropertiesSet() throws Exception {
       localJobAssign = bookingManager.getLocalHostAssignment(id);
    }

    @Override
    public void delete(Current __current) throws CueIceException {
        new CueIceExceptionWrapper() {
            public void throwOnlyIceExceptions() {
                bookingManager.deactivateLocalHostAssignment(localJobAssign);
            }
        }.execute();
    }

    @Override
    public void setMaxResources(final int cores, final long memory, final long gpu, Current arg2)
            throws SpiIceException {
        new CueIceExceptionWrapper() {
            public void throwOnlyIceExceptions() {
                bookingManager.setMaxResources(localJobAssign, cores, memory, gpu);
            }
        }.execute();
    }

    public BookingManager getBookingManager() {
        return bookingManager;
    }

    public void setBookingManager(BookingManager bookingManager) {
        this.bookingManager = bookingManager;
    }
}

