
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

import org.apache.log4j.Logger;
import org.springframework.beans.factory.InitializingBean;

import Ice.Current;

import com.imageworks.common.SpiIce.SpiIceException;
import com.imageworks.common.spring.remoting.SpiIceExceptionMinimalTemplate;
import com.imageworks.spcue.LightweightDependency;
import com.imageworks.spcue.CueClientIce._DependInterfaceDisp;
import com.imageworks.spcue.dispatcher.DispatchQueue;
import com.imageworks.spcue.service.DependManager;

public class ManageDependI extends _DependInterfaceDisp implements InitializingBean {

    private static final Logger logger = Logger.getLogger(ManageDependI.class);

    private final String id;
    private LightweightDependency depend;
    private DependManager dependManager;
    private DispatchQueue manageQueue;

    public ManageDependI(Ice.Identity i) {
        this.id = i.name;
    }

    @Override
    public Ice.DispatchStatus __dispatch(IceInternal.Incoming in,
                                         Current current) {
        ServantInterceptor.__dispatch(this, in, current);
        return super.__dispatch(in, current);
    }

    public void satisfy(Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                manageQueue.execute(new Runnable() {
                    public void run() {
                        try {
                            logger.info("dropping dependency: " + depend.id);
                            dependManager.satisfyDepend(depend);
                        } catch (Exception e) {
                            logger.error("error satisfying dependency: "
                                    + id.toString() + " , " + e);
                        }
                    }
                });
            }
        }.execute();
    }

    public void unsatisfy(Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                dependManager.unsatisfyDepend(depend);
            }
        }.execute();
    }

    public void afterPropertiesSet() throws Exception {
        depend = dependManager.getDepend(id);
    }

    public DependManager getDependManager() {
        return dependManager;
    }

    public void setDependManager(DependManager dependManager) {
        this.dependManager = dependManager;
    }

    public DispatchQueue getManageQueue() {
        return manageQueue;
    }

    public void setManageQueue(DispatchQueue manageQueue) {
        this.manageQueue = manageQueue;
    }
}

