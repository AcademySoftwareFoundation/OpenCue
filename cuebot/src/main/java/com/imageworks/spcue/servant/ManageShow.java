
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

import com.google.common.collect.Sets;
import io.grpc.Status;
import io.grpc.stub.StreamObserver;

import com.imageworks.spcue.AllocationEntity;
import com.imageworks.spcue.FilterEntity;
import com.imageworks.spcue.ServiceOverrideEntity;
import com.imageworks.spcue.ShowEntity;
import com.imageworks.spcue.SubscriptionInterface;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.dao.criteria.JobSearchFactory;
import com.imageworks.spcue.grpc.filter.FilterSeq;
import com.imageworks.spcue.grpc.filter.FilterType;
import com.imageworks.spcue.grpc.job.Group;
import com.imageworks.spcue.grpc.job.GroupSeq;
import com.imageworks.spcue.grpc.job.JobSeq;
import com.imageworks.spcue.grpc.service.Service;
import com.imageworks.spcue.grpc.service.ServiceOverride;
import com.imageworks.spcue.grpc.show.Show;
import com.imageworks.spcue.grpc.show.ShowCreateFilterRequest;
import com.imageworks.spcue.grpc.show.ShowCreateFilterResponse;
import com.imageworks.spcue.grpc.show.ShowCreateOwnerRequest;
import com.imageworks.spcue.grpc.show.ShowCreateOwnerResponse;
import com.imageworks.spcue.grpc.show.ShowCreateServiceOverrideRequest;
import com.imageworks.spcue.grpc.show.ShowCreateServiceOverrideResponse;
import com.imageworks.spcue.grpc.show.ShowCreateShowRequest;
import com.imageworks.spcue.grpc.show.ShowCreateShowResponse;
import com.imageworks.spcue.grpc.show.ShowCreateSubscriptionRequest;
import com.imageworks.spcue.grpc.show.ShowCreateSubscriptionResponse;
import com.imageworks.spcue.grpc.show.ShowDeleteRequest;
import com.imageworks.spcue.grpc.show.ShowDeleteResponse;
import com.imageworks.spcue.grpc.show.ShowEnableBookingRequest;
import com.imageworks.spcue.grpc.show.ShowEnableBookingResponse;
import com.imageworks.spcue.grpc.show.ShowEnableDispatchingRequest;
import com.imageworks.spcue.grpc.show.ShowEnableDispatchingResponse;
import com.imageworks.spcue.grpc.show.ShowFindFilterRequest;
import com.imageworks.spcue.grpc.show.ShowFindFilterResponse;
import com.imageworks.spcue.grpc.show.ShowFindShowRequest;
import com.imageworks.spcue.grpc.show.ShowFindShowResponse;
import com.imageworks.spcue.grpc.show.ShowGetActiveShowsRequest;
import com.imageworks.spcue.grpc.show.ShowGetActiveShowsResponse;
import com.imageworks.spcue.grpc.show.ShowGetDeedsRequest;
import com.imageworks.spcue.grpc.show.ShowGetDeedsResponse;
import com.imageworks.spcue.grpc.show.ShowGetFiltersRequest;
import com.imageworks.spcue.grpc.show.ShowGetFiltersResponse;
import com.imageworks.spcue.grpc.show.ShowGetGroupsRequest;
import com.imageworks.spcue.grpc.show.ShowGetGroupsResponse;
import com.imageworks.spcue.grpc.show.ShowGetJobWhiteboardRequest;
import com.imageworks.spcue.grpc.show.ShowGetJobWhiteboardResponse;
import com.imageworks.spcue.grpc.show.ShowGetJobsRequest;
import com.imageworks.spcue.grpc.show.ShowGetJobsResponse;
import com.imageworks.spcue.grpc.show.ShowGetRootGroupRequest;
import com.imageworks.spcue.grpc.show.ShowGetRootGroupResponse;
import com.imageworks.spcue.grpc.show.ShowGetServiceOverrideRequest;
import com.imageworks.spcue.grpc.show.ShowGetServiceOverrideResponse;
import com.imageworks.spcue.grpc.show.ShowGetServiceOverridesRequest;
import com.imageworks.spcue.grpc.show.ShowGetServiceOverridesResponse;
import com.imageworks.spcue.grpc.show.ShowGetShowsRequest;
import com.imageworks.spcue.grpc.show.ShowGetShowsResponse;
import com.imageworks.spcue.grpc.show.ShowGetSubscriptionRequest;
import com.imageworks.spcue.grpc.show.ShowGetSubscriptionResponse;
import com.imageworks.spcue.grpc.show.ShowInterfaceGrpc;
import com.imageworks.spcue.grpc.show.ShowSetActiveRequest;
import com.imageworks.spcue.grpc.show.ShowSetActiveResponse;
import com.imageworks.spcue.grpc.show.ShowSetCommentEmailRequest;
import com.imageworks.spcue.grpc.show.ShowSetCommentEmailResponse;
import com.imageworks.spcue.grpc.show.ShowSetDefaultMaxCoresRequest;
import com.imageworks.spcue.grpc.show.ShowSetDefaultMaxCoresResponse;
import com.imageworks.spcue.grpc.show.ShowSetDefaultMinCoresRequest;
import com.imageworks.spcue.grpc.show.ShowSetDefaultMinCoresResponse;
import com.imageworks.spcue.grpc.subscription.Subscription;
import com.imageworks.spcue.grpc.subscription.SubscriptionSeq;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.FilterManager;
import com.imageworks.spcue.service.OwnerManager;
import com.imageworks.spcue.service.ServiceManager;
import com.imageworks.spcue.service.Whiteboard;
import com.imageworks.spcue.util.Convert;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class ManageShow extends ShowInterfaceGrpc.ShowInterfaceImplBase {

    @Autowired
    private AdminManager adminManager;

    @Autowired
    private Whiteboard whiteboard;

    @Autowired
    private ShowDao showDao;

    @Autowired
    private FilterManager filterManager;

    @Autowired
    private OwnerManager ownerManager;

    @Autowired
    private ServiceManager serviceManager;

    @Autowired
    private JobSearchFactory jobSearchFactory;

    @Override
    public void createShow(ShowCreateShowRequest request, StreamObserver<ShowCreateShowResponse> responseObserver) {
        try {
            ShowEntity show = new ShowEntity();
            show.name = request.getName();
            adminManager.createShow(show);
            responseObserver.onNext(ShowCreateShowResponse.newBuilder()
                    .setShow(whiteboard.getShow(show.getShowId()))
                    .build());
            responseObserver.onCompleted();
        } catch (Exception e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Show could not be created." + e.getMessage())
                    .withCause(e)
                    .asRuntimeException());
        }
    }

    @Override
    public void findShow(ShowFindShowRequest request, StreamObserver<ShowFindShowResponse> responseObserver) {
        responseObserver.onNext(ShowFindShowResponse.newBuilder()
                .setShow(whiteboard.findShow(request.getName()))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getActiveShows(ShowGetActiveShowsRequest request,
                               StreamObserver<ShowGetActiveShowsResponse> responseObserver) {
        responseObserver.onNext(ShowGetActiveShowsResponse.newBuilder()
                .setShows(whiteboard.getActiveShows())
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getShows(ShowGetShowsRequest request, StreamObserver<ShowGetShowsResponse> responseObserver) {
        responseObserver.onNext(ShowGetShowsResponse.newBuilder()
                .setShows(whiteboard.getShows())
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getFilters(ShowGetFiltersRequest request, StreamObserver<ShowGetFiltersResponse> responseObserver) {
        FilterSeq filterSeq = whiteboard.getFilters(getShowEntity(request.getShow()));
        ShowGetFiltersResponse response = ShowGetFiltersResponse.newBuilder()
                .setFilters(filterSeq)
                .build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void getSubscriptions(ShowGetSubscriptionRequest request,
                                 StreamObserver<ShowGetSubscriptionResponse> responseObserver) {
        SubscriptionSeq subscriptionSeq = whiteboard.getSubscriptions(getShowEntity(request.getShow()));
        ShowGetSubscriptionResponse response = ShowGetSubscriptionResponse.newBuilder()
                .setSubscriptions(subscriptionSeq)
                .build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void getRootGroup(ShowGetRootGroupRequest request,
                             StreamObserver<ShowGetRootGroupResponse> responseObserver) {
        Group rootGroup = whiteboard.getRootGroup(getShowEntity(request.getShow()));
        ShowGetRootGroupResponse response = ShowGetRootGroupResponse.newBuilder().setGroup(rootGroup).build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void createSubscription(ShowCreateSubscriptionRequest request,
                                   StreamObserver<ShowCreateSubscriptionResponse> responseObserver) {
        AllocationEntity allocationEntity = adminManager.getAllocationDetail(request.getAllocationId());
        SubscriptionInterface s = adminManager.createSubscription(
                getShowEntity(request.getShow()),
                allocationEntity,
                Convert.coresToCoreUnits(request.getSize()),
                Convert.coresToCoreUnits(request.getBurst()));
        Subscription subscription = whiteboard.getSubscription(s.getSubscriptionId());
        ShowCreateSubscriptionResponse response = ShowCreateSubscriptionResponse.newBuilder()
                .setSubscription(subscription)
                .build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void getGroups(ShowGetGroupsRequest request, StreamObserver<ShowGetGroupsResponse> responseObserver) {
        GroupSeq groupSeq = whiteboard.getGroups(getShowEntity(request.getShow()));
        ShowGetGroupsResponse response = ShowGetGroupsResponse.newBuilder().setGroups(groupSeq).build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void getJobWhiteboard(ShowGetJobWhiteboardRequest request,
                                 StreamObserver<ShowGetJobWhiteboardResponse> responseObserver) {
        ShowEntity show = getShowEntity(request.getShow());
        ShowGetJobWhiteboardResponse response = ShowGetJobWhiteboardResponse.newBuilder()
                .setWhiteboard(whiteboard.getJobWhiteboard(show))
                .build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void getJobs(ShowGetJobsRequest request, StreamObserver<ShowGetJobsResponse> responseObserver) {
        ShowEntity show = getShowEntity(request.getShow());
        JobSeq jobSeq = whiteboard.getJobs(jobSearchFactory.create(show));
        ShowGetJobsResponse response = ShowGetJobsResponse.newBuilder().setJobs(jobSeq).build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void setDefaultMaxCores(ShowSetDefaultMaxCoresRequest request,
                                   StreamObserver<ShowSetDefaultMaxCoresResponse> responseObserver) {
        ShowEntity show = getShowEntity(request.getShow());
        showDao.updateShowDefaultMaxCores(show, Convert.coresToWholeCoreUnits(request.getMaxCores()));
        responseObserver.onNext(ShowSetDefaultMaxCoresResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setDefaultMinCores(ShowSetDefaultMinCoresRequest request,
                                   StreamObserver<ShowSetDefaultMinCoresResponse> responseObserver) {
        ShowEntity show = getShowEntity(request.getShow());
        showDao.updateShowDefaultMinCores(show, Convert.coresToWholeCoreUnits(request.getMinCores()));
        responseObserver.onNext(ShowSetDefaultMinCoresResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void findFilter(ShowFindFilterRequest request,
                                   StreamObserver<ShowFindFilterResponse> responseObserver) {
        ShowEntity show = getShowEntity(request.getShow());
        ShowFindFilterResponse response = ShowFindFilterResponse.newBuilder()
                .setFilter(whiteboard.findFilter(show, request.getName()))
                .build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void createFilter(ShowCreateFilterRequest request,
                             StreamObserver<ShowCreateFilterResponse> responseObserver) {
        ShowEntity show = getShowEntity(request.getShow());
        FilterEntity filter = new FilterEntity();
        filter.name = request.getName();
        filter.showId = show.id;
        filter.type = FilterType.MATCH_ALL;
        filter.order = 0;
        filterManager.createFilter(filter);
        ShowCreateFilterResponse response = ShowCreateFilterResponse.newBuilder()
                .setFilter(whiteboard.findFilter(show, request.getName()))
                .build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void enableBooking(ShowEnableBookingRequest request,
                              StreamObserver<ShowEnableBookingResponse> responseObserver) {
        ShowEntity show = getShowEntity(request.getShow());
        showDao.updateBookingEnabled(show, request.getEnabled());
        responseObserver.onNext(ShowEnableBookingResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void enableDispatching(ShowEnableDispatchingRequest request,
                                  StreamObserver<ShowEnableDispatchingResponse> responseObserver) {
        ShowEntity show = getShowEntity(request.getShow());
        showDao.updateDispatchingEnabled(show, request.getEnabled());
        responseObserver.onNext(ShowEnableDispatchingResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void getDeeds(ShowGetDeedsRequest request, StreamObserver<ShowGetDeedsResponse> responseObserver) {
        ShowEntity show = getShowEntity(request.getShow());
        responseObserver.onNext(ShowGetDeedsResponse.newBuilder()
                .setDeeds(whiteboard.getDeeds(show))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void createOwner(ShowCreateOwnerRequest request, StreamObserver<ShowCreateOwnerResponse> responseObserver) {
        ownerManager.createOwner(request.getName(), getShowEntity(request.getShow()));
        ShowCreateOwnerResponse response = ShowCreateOwnerResponse.newBuilder()
                .setOwner(whiteboard.getOwner(request.getName()))
                .build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void setActive(ShowSetActiveRequest request, StreamObserver<ShowSetActiveResponse> responseObserver) {
        adminManager.setShowActive(getShowEntity(request.getShow()), request.getValue());
        responseObserver.onNext(ShowSetActiveResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void createServiceOverride(ShowCreateServiceOverrideRequest request,
                                      StreamObserver<ShowCreateServiceOverrideResponse> responseObserver) {
        ShowEntity show = getShowEntity(request.getShow());
        Service requestService = request.getService();
        ServiceOverrideEntity service = new ServiceOverrideEntity();
        service.showId = show.getId();
        service.name = requestService.getName();
        service.minCores = requestService.getMinCores();
        service.maxCores = requestService.getMaxCores();
        service.minMemory = requestService.getMinMemory();
        service.minGpu = requestService.getMinGpu();
        service.tags = Sets.newLinkedHashSet(requestService.getTagsList());
        service.threadable = requestService.getThreadable();
        serviceManager.createService(service);
        ServiceOverride serviceOverride = whiteboard.getServiceOverride(show, service.name);
        responseObserver.onNext(ShowCreateServiceOverrideResponse.newBuilder()
                .setServiceOverride(serviceOverride)
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getServiceOverrides(ShowGetServiceOverridesRequest request,
                                   StreamObserver<ShowGetServiceOverridesResponse> responseObserver) {
        ShowEntity show = getShowEntity(request.getShow());
        responseObserver.onNext(ShowGetServiceOverridesResponse.newBuilder()
                .setServiceOverrides(whiteboard.getServiceOverrides(show))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void delete(ShowDeleteRequest request, StreamObserver<ShowDeleteResponse> responseObserver) {
        showDao.delete(getShowEntity(request.getShow()));
        responseObserver.onNext(ShowDeleteResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void getServiceOverride(ShowGetServiceOverrideRequest request,
                                   StreamObserver<ShowGetServiceOverrideResponse> responseObserver) {
        ServiceOverride serviceOverride = whiteboard.getServiceOverride(
                getShowEntity(request.getShow()),
                request.getName());
        responseObserver.onNext(ShowGetServiceOverrideResponse.newBuilder()
                .setServiceOverride(serviceOverride)
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void setCommentEmail(ShowSetCommentEmailRequest request, StreamObserver<ShowSetCommentEmailResponse> responseObserver) {
        adminManager.updateShowCommentEmail(
                getShowEntity(request.getShow()),
                request.getEmail().split(","));
        responseObserver.onNext(ShowSetCommentEmailResponse.newBuilder().build());
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

    private ShowEntity getShowEntity(Show show) {
        return adminManager.getShowEntity(show.getId());
    }

    public JobSearchFactory getJobSearchFactory() {
        return jobSearchFactory;
    }

    public void setJobSearchFactory(JobSearchFactory jobSearchFactory) {
        this.jobSearchFactory = jobSearchFactory;
    }
}

