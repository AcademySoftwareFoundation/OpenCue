
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
import com.imageworks.spcue.ActionDetail;
import com.imageworks.spcue.CueClientIce.ActionData;
import com.imageworks.spcue.CueClientIce.Filter;
import com.imageworks.spcue.CueClientIce._ActionInterfaceDisp;
import com.imageworks.spcue.service.FilterManager;
import com.imageworks.spcue.service.Whiteboard;

public class ManageActionI extends _ActionInterfaceDisp implements
        InitializingBean {

    private FilterManager filterManager;
    private Whiteboard whiteboard;

    private final String id;
    private ActionDetail action;

    public ManageActionI(Ice.Identity i) {
        id = i.name;
    }

    public void afterPropertiesSet() throws Exception {
        action = filterManager.getAction(id);
    }

    public void delete(Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                filterManager.deleteAction(action);
            }
        }.execute();
    }

    public Filter getParentFilter(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Filter>() {
            public Filter throwOnlyIceExceptions() {
                return whiteboard.getFilter(action);
            }
        }.execute();
    }

    public void commit(final ActionData data, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                ActionDetail newAction = ActionDetail.build(
                        filterManager.getFilter(action), data, id);
                filterManager.updateAction(newAction);
            }
        }.execute();
    }

    public FilterManager getFilterManager() {
        return filterManager;
    }

    public void setFilterManager(FilterManager filterManager) {
        this.filterManager = filterManager;
    }

    public Whiteboard getWhiteboard() {
        return whiteboard;
    }

    public void setWhiteboard(Whiteboard whiteboard) {
        this.whiteboard = whiteboard;
    }
}

