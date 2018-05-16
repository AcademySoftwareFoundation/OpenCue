
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
import com.imageworks.spcue.ActionDetail;
import com.imageworks.spcue.FilterDetail;
import com.imageworks.spcue.MatcherDetail;
import com.imageworks.spcue.CueClientIce.Action;
import com.imageworks.spcue.CueClientIce.ActionData;
import com.imageworks.spcue.CueClientIce.GroupInterfacePrx;
import com.imageworks.spcue.CueClientIce.JobInterfacePrx;
import com.imageworks.spcue.CueClientIce.Matcher;
import com.imageworks.spcue.CueClientIce.MatcherData;
import com.imageworks.spcue.CueClientIce._FilterInterfaceDisp;
import com.imageworks.spcue.CueIce.FilterType;
import com.imageworks.spcue.dao.FilterDao;
import com.imageworks.spcue.dao.GroupDao;
import com.imageworks.spcue.dispatcher.DispatchQueue;
import com.imageworks.spcue.service.FilterManager;
import com.imageworks.spcue.service.Whiteboard;

public class ManageFilterI extends _FilterInterfaceDisp implements
        InitializingBean {

    private Whiteboard whiteboard;
    private FilterManager filterManager;
    private FilterDao filterDao;
    private GroupDao groupDao;
    private DispatchQueue manageQueue;

    private final String id;
    private FilterDetail filter;

    public ManageFilterI(Ice.Identity i) {
        this.id = i.name;
    }

    public void afterPropertiesSet() throws Exception {
        filter = filterManager.getFilter(id);
    }

    public Action createAction(final ActionData action, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Action>() {
            public Action throwOnlyIceExceptions() {
                ActionDetail actionDetail = ActionDetail.build(filter, action);
                filterManager.createAction(actionDetail);
                return whiteboard.getAction(actionDetail);
            }
        }.execute();
    }

    public Matcher createMatcher(final MatcherData matcher, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Matcher>() {
            public Matcher throwOnlyIceExceptions() {
                MatcherDetail matcherDetail = MatcherDetail.build(filter, matcher);
                matcherDetail.filterId = filter.id;
                filterManager.createMatcher(matcherDetail);
                return whiteboard.getMatcher(matcherDetail);
            }
        }.execute();
    }

    public void delete(Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                manageQueue.execute(new Runnable() {
                    public void run() {
                        filterManager.deleteFilter(filter);
                    }
                });
            }
        }.execute();
    }

    public List<Action> getActions(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Action>>() {
            public List<Action> throwOnlyIceExceptions() {
                return whiteboard.getActions(filter);
            }
        }.execute();
    }

    public List<Matcher> getMatchers(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Matcher>>() {
            public List<Matcher> throwOnlyIceExceptions() {
                return whiteboard.getMatchers(filter);
            }
        }.execute();
    }

    public void lowerOrder(Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                filterManager.lowerFilterOrder(filter);
            }
        }.execute();
    }

    public void raiseOrder(Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                filterManager.raiseFilterOrder(filter);
            }
        }.execute();
    }

    public void orderFirst(Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                filterManager.setFilterOrder(filter, 0);
            }
        }.execute();
    }

    public void orderLast(Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                filterManager.setFilterOrder(filter, 9999);
            }
        }.execute();
    }

    public void runFilterOnGroup(final GroupInterfacePrx proxy,
            Current __current) throws SpiIceException {
        filterManager.runFilterOnGroup(
                filterManager.getFilter(id),
                groupDao.getGroup(proxy.ice_getIdentity().name));
    }

    public void setEnabled(final boolean enabled, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                filterDao.updateSetFilterEnabled(filter, enabled);
            }
        }.execute();
    }

    public void setName(final String name, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                filterDao.updateSetFilterName(filter, name);
            }
        }.execute();
    }

    public void setType(final FilterType type, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                filterDao.updateSetFilterType(filter,type);
            }
        }.execute();
    }

    public void setOrder(final int order, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                filterManager.setFilterOrder(filter, (double) order);
            }
        }.execute();
    }

    public void runFilterOnJobs(final List<JobInterfacePrx> proxies,
            Current __current) throws SpiIceException {
        for (JobInterfacePrx proxy: proxies) {
            filterManager.runFilterOnJob(filterManager.getFilter(id),
                    proxy.ice_getIdentity().name);
        }
    }

    public FilterDao getFilterDao() {
        return filterDao;
    }

    public void setFilterDao(FilterDao filterDao) {
        this.filterDao = filterDao;
    }

    public FilterManager getFilterManager() {
        return filterManager;
    }

    public void setFilterManager(FilterManager filterManager) {
        this.filterManager = filterManager;
    }

    public GroupDao getGroupDao() {
        return groupDao;
    }

    public void setGroupDao(GroupDao groupDao) {
        this.groupDao = groupDao;
    }

    public DispatchQueue getManageQueue() {
        return manageQueue;
    }

    public void setManageQueue(DispatchQueue manageQueue) {
        this.manageQueue = manageQueue;
    }

    public Whiteboard getWhiteboard() {
        return whiteboard;
    }

    public void setWhiteboard(Whiteboard whiteboard) {
        this.whiteboard = whiteboard;
    }

}

