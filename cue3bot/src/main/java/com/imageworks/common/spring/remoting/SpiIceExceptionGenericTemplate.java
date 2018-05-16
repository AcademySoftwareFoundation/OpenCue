
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



package com.imageworks.common.spring.remoting;

import java.util.ArrayList;

import com.imageworks.common.SpiIce.SpiIceCause;
import com.imageworks.common.SpiIce.SpiIceException;

public abstract class SpiIceExceptionGenericTemplate<T> {

    public SpiIceExceptionGenericTemplate() { }

    public abstract T throwOnlyIceExceptions() throws SpiIceException;

    public T execute() throws SpiIceException {
        try {
            IceServer.dataRequests.incrementAndGet();
            return this.throwOnlyIceExceptions();
        } catch (SpiIceException e) {
            IceServer.errors.incrementAndGet();
            throw e;
        } catch (java.lang.Throwable t) {
            IceServer.errors.incrementAndGet();
            String[] stackTrace = new String[t.getStackTrace().length];

            int traceLength = t.getStackTrace().length;
            for(int i=0; i<traceLength; i++) {
                stackTrace[i] = t.getStackTrace()[i].toString();
            }
            throw new SpiIceException(t.getMessage(), stackTrace, new ArrayList<SpiIceCause>(0));
        }
    }
}

