
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
import com.imageworks.common.spring.remoting.SpiIceExceptionMinimalTemplate;
import com.imageworks.spcue.TaskDetail;
import com.imageworks.spcue.CueClientIce._TaskInterfaceDisp;
import com.imageworks.spcue.service.DepartmentManager;
import com.imageworks.spcue.util.Convert;

public class ManageTaskI extends _TaskInterfaceDisp implements InitializingBean {

    private final String id;
    private TaskDetail task;
    private DepartmentManager departmentManager;

    public ManageTaskI(Ice.Identity i) {
        this.id = i.name;
    }

    @Override
    public void afterPropertiesSet() throws Exception {
        task = departmentManager.getTaskDetail(id);
    }

    @Override
    public void delete(Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                departmentManager.removeTask(task);
            }
        }.execute();
    }


    public void setMinCores(final float minCores, Current __curent) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                departmentManager.setMinCores(task, Convert.coresToWholeCoreUnits(minCores));
            }
        }.execute();
    }

    @Override
    public void clearAdjustment(Current arg0) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                departmentManager.clearTaskAdjustment(task);
            }
        }.execute();
    }

    public DepartmentManager getDepartmentManager() {
        return departmentManager;
    }

    public void setDepartmentManager(DepartmentManager departmentManager) {
        this.departmentManager = departmentManager;
    }
}

