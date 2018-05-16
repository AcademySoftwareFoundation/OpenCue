
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
import java.util.List;
import java.util.Map;

import org.springframework.beans.factory.InitializingBean;

import Ice.Current;

import com.imageworks.common.SpiIce.SpiIceException;
import com.imageworks.common.spring.remoting.SpiIceExceptionGenericTemplate;
import com.imageworks.common.spring.remoting.SpiIceExceptionMinimalTemplate;
import com.imageworks.spcue.PointDetail;
import com.imageworks.spcue.TaskDetail;
import com.imageworks.spcue.CueClientIce.Task;
import com.imageworks.spcue.CueClientIce._DepartmentInterfaceDisp;
import com.imageworks.spcue.service.DepartmentManager;
import com.imageworks.spcue.service.Whiteboard;
import com.imageworks.spcue.util.Convert;

public class ManageDepartmentI extends _DepartmentInterfaceDisp implements InitializingBean {

    private final String id;
    private PointDetail departmentConfig;
    private DepartmentManager departmentManager;
    private Whiteboard whiteboard;

    public ManageDepartmentI(Ice.Identity i) {
        this.id = i.name;
    }

    @Override
    public void afterPropertiesSet() throws Exception {
        departmentConfig = departmentManager.getDepartmentConfigDetail(id);
    }

    public Task addTask(final String shot, final float minCores, Current arg2)
            throws SpiIceException {

        return new SpiIceExceptionGenericTemplate<Task>() {
            public Task throwOnlyIceExceptions() {
                TaskDetail t = new TaskDetail(departmentConfig, shot, Convert.coresToCoreUnits(minCores));
                departmentManager.createTask(t);
                // TODO: Fix this to take an ID
                return whiteboard.getTask(departmentConfig, departmentConfig, shot);
            }
        }.execute();
    }

    @Override
    public List<Task> addTasks(final Map<String, Integer> arg0, Current arg1)
            throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Task>>() {
            public List<Task> throwOnlyIceExceptions() {
                List<Task> result = new ArrayList<Task>(arg0.size());
                for(Map.Entry<String,Integer> e: arg0.entrySet()) {
                    TaskDetail t = new TaskDetail(departmentConfig, e.getKey(),e.getValue());
                    departmentManager.createTask(t);
                    result.add(whiteboard.getTask(departmentConfig, departmentConfig, e.getKey()));
                }
                return result;
            }
        }.execute();
    }

    @Override
    public void clearTasks(Current arg0) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                departmentManager.clearTasks(departmentConfig);
            }
        }.execute();
    }

    @Override
    public void disableTiManaged(Current arg0) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                departmentManager.disableTiManaged(departmentConfig);
            }
        }.execute();
    }


    public void enableTiManaged(final String task, final float cores, Current arg2)
            throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                departmentManager.enableTiManaged(departmentConfig, task,
                        Convert.coresToWholeCoreUnits(cores));
            }
        }.execute();
    }

    @Override
    public List<Task> getTasks(Current arg0) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Task>>() {
            public List<Task> throwOnlyIceExceptions() {
                return whiteboard.getTasks(departmentConfig, departmentConfig);
            }
        }.execute();
    }

    @Override
    public List<Task> replaceTasks(Map<String, Integer> arg0, Current __current)
            throws SpiIceException {
        clearTasks(__current);
        return addTasks(arg0, __current);
    }


    public void setManagedCores(final float cores, Current arg1) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                departmentManager.setManagedCores(departmentConfig,
                        Convert.coresToWholeCoreUnits(cores));
            }
        }.execute();
    }

    @Override
    public void clearTaskAdjustments(Current arg0) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                departmentManager.clearTaskAdjustments(departmentConfig);
            }
        }.execute();
    }

    public DepartmentManager getDepartmentManager() {
        return departmentManager;
    }

    public void setDepartmentManager(DepartmentManager departmentManager) {
        this.departmentManager = departmentManager;
    }

    public Whiteboard getWhiteboard() {
        return whiteboard;
    }

    public void setWhiteboard(Whiteboard whiteboard) {
        this.whiteboard = whiteboard;
    }
}

