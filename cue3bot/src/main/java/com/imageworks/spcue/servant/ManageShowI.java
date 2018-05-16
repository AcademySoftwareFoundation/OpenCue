
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

import com.google.common.collect.Sets;
import com.imageworks.common.SpiIce.SpiIceException;
import com.imageworks.common.spring.remoting.SpiIceExceptionGenericTemplate;
import com.imageworks.common.spring.remoting.SpiIceExceptionMinimalTemplate;
import com.imageworks.spcue.AllocationDetail;

import com.imageworks.spcue.FilterDetail;
import com.imageworks.spcue.ShowDetail;
import com.imageworks.spcue.CueClientIce.AllocationInterfacePrx;
import com.imageworks.spcue.CueClientIce.Deed;
import com.imageworks.spcue.CueClientIce.Department;
import com.imageworks.spcue.CueClientIce.Filter;
import com.imageworks.spcue.CueClientIce.Group;
import com.imageworks.spcue.CueClientIce.Job;
import com.imageworks.spcue.CueClientIce.NestedGroup;
import com.imageworks.spcue.CueClientIce.Owner;
import com.imageworks.spcue.CueClientIce.ServiceData;
import com.imageworks.spcue.CueClientIce.ServiceOverride;
import com.imageworks.spcue.CueIce.EntityNotFoundException;
import com.imageworks.spcue.CueIce.FilterType;
import com.imageworks.spcue.CueClientIce.Subscription;
import com.imageworks.spcue.CueClientIce._ShowInterfaceDisp;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.dao.criteria.JobSearch;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.FilterManager;
import com.imageworks.spcue.service.DepartmentManager;
import com.imageworks.spcue.service.OwnerManager;
import com.imageworks.spcue.service.ServiceManager;
import com.imageworks.spcue.service.Whiteboard;
import com.imageworks.spcue.util.Convert;

public class ManageShowI  extends _ShowInterfaceDisp implements InitializingBean  {

    private final String id;
    private ShowDetail show;
    private AdminManager adminManager;
    private Whiteboard whiteboard;
    private ShowDao showDao;
    private DepartmentManager departmentManager;
    private FilterManager filterManager;
    private OwnerManager ownerManager;
    private ServiceManager serviceManager;

    public ManageShowI(Ice.Identity id) {
        this.id = id.name;
    }

    @Override
    public Ice.DispatchStatus __dispatch(IceInternal.Incoming in,
                                         Current current) {
        ServantInterceptor.__dispatch(this, in, current);
        return super.__dispatch(in, current);
    }


    public void afterPropertiesSet() throws Exception {
        show = adminManager.getShowDetail(id);
    }

    public List<Filter> getFilters(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Filter>>() {
            public List<Filter> throwOnlyIceExceptions() {
                return whiteboard.getFilters(show);
            }
        }.execute();
    }

    public List<Subscription> getSubscriptions(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Subscription>>() {
            public List<Subscription> throwOnlyIceExceptions() {
                return whiteboard.getSubscriptions(show);
            }
        }.execute();
    }

    public Group getRootGroup(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Group>() {
            public Group throwOnlyIceExceptions() {
                return whiteboard.getRootGroup(show);
            }
        }.execute();
    }

    public Subscription createSubscription(final AllocationInterfacePrx alloc,
            final float size, final float burst, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Subscription>() {
            public Subscription throwOnlyIceExceptions() {
                AllocationDetail a = adminManager.getAllocationDetail(
                        alloc.ice_getIdentity().name);
                com.imageworks.spcue.Subscription s =
                    adminManager.createSubscription(show, a,
                        Convert.coresToCoreUnits(size),
                        Convert.coresToCoreUnits(burst));

                return whiteboard.getSubscription(s.getSubscriptionId());
            }
        }.execute();
    }

    public List<Group> getGroups(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Group>>() {
            public List<Group> throwOnlyIceExceptions() {
                return whiteboard.getGroups(show);
            }
        }.execute();
    }

    public NestedGroup getJobWhiteboard(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<NestedGroup>() {
            public NestedGroup throwOnlyIceExceptions() {
                return whiteboard.getJobWhiteboard(show);
            }
        }.execute();
    }

    public List<Job> getJobs(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Job>>() {
            public List<Job> throwOnlyIceExceptions() {
                return whiteboard.getJobs(JobSearch.byShow(show));
            }
        }.execute();
    }

    public void setDefaultMaxCores(final float cores, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                showDao.updateShowDefaultMaxCores(show, Convert.coresToWholeCoreUnits(cores));
            }
        }.execute();
    }

    public void setDefaultMinCores(final float cores, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                showDao.updateShowDefaultMinCores(show, Convert.coresToWholeCoreUnits(cores));
            }
        }.execute();
    }

    public Filter findFilter(final String name, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Filter>() {
            public Filter throwOnlyIceExceptions() throws EntityNotFoundException {
                try {
                    return whiteboard.findFilter(show, name);
                } catch (org.springframework.dao.EmptyResultDataAccessException e) {
                    throw new EntityNotFoundException(
                            "filter not found " + name + " on show " + show.name, null, null);
                }
            }
        }.execute();
    }

    public Filter createFilter(final String name, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Filter>() {
            public Filter throwOnlyIceExceptions() {
                FilterDetail filter = new FilterDetail();
                filter.name = name;
                filter.showId = show.id;
                filter.type = FilterType.MatchAll;
                filter.order = 0;
                filterManager.createFilter(filter);
                return whiteboard.findFilter(show, name);
            }
        }.execute();
    }

    @Override
    public Department getDepartment(final String name, Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Department>() {
            public Department throwOnlyIceExceptions() {
                return whiteboard.getDepartment(show, name);
            }
        }.execute();
    }

    @Override
    public List<Department> getDepartments(Current arg0) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Department>>() {
            public List<Department> throwOnlyIceExceptions() {
                return whiteboard.getDepartments(show);
            }
        }.execute();
    }


    @Override
    public void enableBooking(final boolean arg0, Current arg1)
            throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                showDao.updateBookingEnabled(show, arg0);
            }
        }.execute();
    }

    @Override
    public void enableDispatching(final boolean arg0, Current arg1)
            throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                showDao.updateDispatchingEnabled(show, arg0);
            }
        }.execute();
    }

    @Override
    public List<Deed> getDeeds(Current arg0) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Deed>>() {
            public List<Deed> throwOnlyIceExceptions() {
                List<Deed> deeds =  whiteboard.getDeeds(show);
                return deeds;
            }
        }.execute();
    }

    @Override
    public Owner createOwner(final String user, Current __arg) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<Owner>() {
            public Owner throwOnlyIceExceptions() {
                ownerManager.createOwner(user, show);
                return whiteboard.getOwner(user);
            }
        }.execute();
    }

    @Override
    public void setActive(final boolean value, Current __current)
        throws SpiIceException {
        new CueIceExceptionWrapper() {
            public void throwOnlyIceExceptions() {
                adminManager.setShowActive(show, value);
            }
        }.execute();
    }

    @Override
    public ServiceOverride createServiceOverride(final ServiceData srv, Current arg1)
            throws SpiIceException {
        return new CueIceExceptionTemplate<ServiceOverride>() {
            public ServiceOverride throwOnlyIceExceptions() {
                com.imageworks.spcue.ServiceOverride service =
                    new com.imageworks.spcue.ServiceOverride();
                service.showId = show.getId();
                service.name = srv.name;
                service.minCores = srv.minCores;
                service.maxCores = srv.maxCores;
                service.minMemory = srv.minMemory;
                service.minGpu = srv.minGpu;
                service.tags = Sets.newLinkedHashSet(srv.tags);
                service.threadable = srv.threadable;
                serviceManager.createService(service);
                return whiteboard.getServiceOverride(show, service.name);
            }
        }.execute();
    }

    @Override
    public List<ServiceOverride> getServiceOverrides(Current arg0)
            throws SpiIceException {
        return new CueIceExceptionTemplate<List<ServiceOverride>>() {
            public List<ServiceOverride> throwOnlyIceExceptions() {
                return whiteboard.getServiceOverrides(show);
            }
        }.execute();
    }

    @Override
    public void delete(Current arg0) throws SpiIceException {
        showDao.delete(show);
    }

    @Override
    public ServiceOverride getServiceOverride(final String id, Current arg1)
            throws SpiIceException {
        return new CueIceExceptionTemplate<ServiceOverride>() {
            public ServiceOverride throwOnlyIceExceptions() {
                return whiteboard.getServiceOverride(show, id);
            }
        }.execute();
    }

    @Override
    public void setCommentEmail(final String email, Current arg1)
            throws SpiIceException {
        new CueIceExceptionWrapper() {
            public void throwOnlyIceExceptions() {
                adminManager.updateShowCommentEmail(show, email.split(","));
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

    public ShowDao getShowDao() {
        return showDao;
    }

    public void setShowDao(ShowDao showDao) {
        this.showDao = showDao;
    }

    public FilterManager getFilterManager() {
        return filterManager;
    }

    public void setFilterManager(FilterManager filterManager) {
        this.filterManager = filterManager;
    }

    public DepartmentManager getDepartmentManager() {
        return departmentManager;
    }

    public void setDepartmentManager(DepartmentManager departmentManager) {
        this.departmentManager = departmentManager;
    }

    public OwnerManager getOwnerManager() {
        return ownerManager;
    }

    public void setOwnerManager(OwnerManager ownerManager) {
        this.ownerManager = ownerManager;
    }

    public ServiceManager getServiceManager() {
        return serviceManager;
    }

    public void setServiceManager(ServiceManager serviceManager) {
        this.serviceManager = serviceManager;
    }
}

