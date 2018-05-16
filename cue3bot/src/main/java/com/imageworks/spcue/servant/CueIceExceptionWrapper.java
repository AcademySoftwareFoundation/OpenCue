
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

import java.util.ArrayList;

import org.springframework.dao.EmptyResultDataAccessException;

import com.imageworks.common.SpiIce.SpiIceCause;
import com.imageworks.spcue.CueIce.CueIceException;
import com.imageworks.spcue.CueIce.EntityNotFoundException;
import com.imageworks.common.spring.remoting.IceServer;

public abstract class CueIceExceptionWrapper {

    public CueIceExceptionWrapper() {}

    public abstract void throwOnlyIceExceptions() throws CueIceException;

    public void execute() throws CueIceException {
        try {

            IceServer.dataRequests.incrementAndGet();
            throwOnlyIceExceptions();

        } catch (EmptyResultDataAccessException erdae) {
            throw new EntityNotFoundException("Error retrieving object: " +
                    erdae.getMessage(), getStackTrace(erdae),
                    new ArrayList<SpiIceCause>(0));

        } catch (java.lang.Throwable t) {

            IceServer.errors.incrementAndGet();

            throw new EntityNotFoundException("Error executing Ice method " +
                    t.getMessage(), getStackTrace(t), new ArrayList<SpiIceCause>(0));
        }
    }

    public String[] getStackTrace(Throwable t) {

        String[] stackTrace = new String[t.getStackTrace().length];

        int traceLength = t.getStackTrace().length;
        for (int i = 0; i < traceLength; i++) {
            stackTrace[i] = t.getStackTrace()[i].toString();
        }

        return stackTrace;
    }
}

