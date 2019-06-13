
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

import io.grpc.stub.StreamObserver;

import com.imageworks.spcue.ActionEntity;
import com.imageworks.spcue.FilterEntity;
import com.imageworks.spcue.MatcherEntity;
import com.imageworks.spcue.dao.FilterDao;
import com.imageworks.spcue.dao.GroupDao;
import com.imageworks.spcue.dispatcher.DispatchQueue;
import com.imageworks.spcue.grpc.filter.Action;
import com.imageworks.spcue.grpc.filter.Filter;
import com.imageworks.spcue.grpc.filter.FilterCreateActionRequest;
import com.imageworks.spcue.grpc.filter.FilterCreateActionResponse;
import com.imageworks.spcue.grpc.filter.FilterCreateMatcherRequest;
import com.imageworks.spcue.grpc.filter.FilterCreateMatcherResponse;
import com.imageworks.spcue.grpc.filter.FilterDeleteRequest;
import com.imageworks.spcue.grpc.filter.FilterDeleteResponse;
import com.imageworks.spcue.grpc.filter.FilterFindFilterRequest;
import com.imageworks.spcue.grpc.filter.FilterFindFilterResponse;
import com.imageworks.spcue.grpc.filter.FilterGetActionsRequest;
import com.imageworks.spcue.grpc.filter.FilterGetActionsResponse;
import com.imageworks.spcue.grpc.filter.FilterGetMatchersRequest;
import com.imageworks.spcue.grpc.filter.FilterGetMatchersResponse;
import com.imageworks.spcue.grpc.filter.FilterInterfaceGrpc;
import com.imageworks.spcue.grpc.filter.FilterLowerOrderRequest;
import com.imageworks.spcue.grpc.filter.FilterLowerOrderResponse;
import com.imageworks.spcue.grpc.filter.FilterOrderFirstRequest;
import com.imageworks.spcue.grpc.filter.FilterOrderFirstResponse;
import com.imageworks.spcue.grpc.filter.FilterOrderLastRequest;
import com.imageworks.spcue.grpc.filter.FilterOrderLastResponse;
import com.imageworks.spcue.grpc.filter.FilterRaiseOrderRequest;
import com.imageworks.spcue.grpc.filter.FilterRaiseOrderResponse;
import com.imageworks.spcue.grpc.filter.FilterRunFilterOnGroupRequest;
import com.imageworks.spcue.grpc.filter.FilterRunFilterOnGroupResponse;
import com.imageworks.spcue.grpc.filter.FilterRunFilterOnJobsRequest;
import com.imageworks.spcue.grpc.filter.FilterRunFilterOnJobsResponse;
import com.imageworks.spcue.grpc.filter.FilterSetEnabledRequest;
import com.imageworks.spcue.grpc.filter.FilterSetEnabledResponse;
import com.imageworks.spcue.grpc.filter.FilterSetNameRequest;
import com.imageworks.spcue.grpc.filter.FilterSetNameResponse;
import com.imageworks.spcue.grpc.filter.FilterSetOrderRequest;
import com.imageworks.spcue.grpc.filter.FilterSetOrderResponse;
import com.imageworks.spcue.grpc.filter.FilterSetTypeRequest;
import com.imageworks.spcue.grpc.filter.FilterSetTypeResponse;
import com.imageworks.spcue.grpc.filter.Matcher;
import com.imageworks.spcue.grpc.job.Job;
import com.imageworks.spcue.service.FilterManager;
import com.imageworks.spcue.service.Whiteboard;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class ManageFilter extends FilterInterfaceGrpc.FilterInterfaceImplBase {

    @Autowired
    private Whiteboard whiteboard;

    @Autowired
    private FilterManager filterManager;

    @Autowired
    private FilterDao filterDao;

    @Autowired
    private GroupDao groupDao;

    @Autowired
    private DispatchQueue manageQueue;

    @Override
    public void findFilter(FilterFindFilterRequest request, StreamObserver<FilterFindFilterResponse> responseObserver) {
        responseObserver.onNext(FilterFindFilterResponse.newBuilder()
                .setFilter(whiteboard.findFilter(request.getShow(), request.getName()))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void createAction(FilterCreateActionRequest request,
                             StreamObserver<FilterCreateActionResponse> responseObserver) {
        ActionEntity actionDetail = ActionEntity.build(getFilterEntity(request.getFilter()), request.getData());
        filterManager.createAction(actionDetail);
        Action action = whiteboard.getAction(actionDetail);
        FilterCreateActionResponse response = FilterCreateActionResponse.newBuilder().setAction(action).build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void createMatcher(FilterCreateMatcherRequest request,
                              StreamObserver<FilterCreateMatcherResponse> responseObserver) {
        FilterEntity filter = getFilterEntity(request.getFilter());
        MatcherEntity matcherDetail = MatcherEntity.build(filter, request.getData());
        matcherDetail.filterId = filter.id;
        filterManager.createMatcher(matcherDetail);
        Matcher newMatcher = whiteboard.getMatcher(matcherDetail);
        FilterCreateMatcherResponse response = FilterCreateMatcherResponse.newBuilder()
                .setMatcher(newMatcher)
                .build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void delete(FilterDeleteRequest request, StreamObserver<FilterDeleteResponse> responseObserver) {
        FilterEntity filter = getFilterEntity(request.getFilter());
        manageQueue.execute(new Runnable() {
            public void run() {
                filterManager.deleteFilter(filter);
            }
        });
        responseObserver.onNext(FilterDeleteResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void getActions(FilterGetActionsRequest request, StreamObserver<FilterGetActionsResponse> responseObserver) {
        FilterEntity filter = getFilterEntity(request.getFilter());
        FilterGetActionsResponse response = FilterGetActionsResponse.newBuilder()
                .setActions(whiteboard.getActions(filter))
                .build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void getMatchers(FilterGetMatchersRequest request,
                            StreamObserver<FilterGetMatchersResponse> responseObserver) {
        FilterEntity filter = getFilterEntity(request.getFilter());
        FilterGetMatchersResponse response = FilterGetMatchersResponse.newBuilder()
                .setMatchers(whiteboard.getMatchers(filter))
                .build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void lowerOrder(FilterLowerOrderRequest request, StreamObserver<FilterLowerOrderResponse> responseObserver) {
        FilterEntity filter = getFilterEntity(request.getFilter());
        filterManager.lowerFilterOrder(filter);
        responseObserver.onNext(FilterLowerOrderResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void raiseOrder(FilterRaiseOrderRequest request, StreamObserver<FilterRaiseOrderResponse> responseObserver) {
        FilterEntity filter = getFilterEntity(request.getFilter());
        filterManager.raiseFilterOrder(filter);
        responseObserver.onNext(FilterRaiseOrderResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void orderFirst(FilterOrderFirstRequest request, StreamObserver<FilterOrderFirstResponse> responseObserver) {
        FilterEntity filter = getFilterEntity(request.getFilter());
        filterManager.setFilterOrder(filter, 0);
        responseObserver.onNext(FilterOrderFirstResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void orderLast(FilterOrderLastRequest request, StreamObserver<FilterOrderLastResponse> responseObserver) {
        FilterEntity filter = getFilterEntity(request.getFilter());
        filterManager.setFilterOrder(filter, 9999);
        responseObserver.onNext(FilterOrderLastResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void runFilterOnGroup(FilterRunFilterOnGroupRequest request,
                                 StreamObserver<FilterRunFilterOnGroupResponse> responseObserver) {
        FilterEntity filter = getFilterEntity(request.getFilter());
        filterManager.runFilterOnGroup(filter, groupDao.getGroup(request.getGroup().getId()));
        responseObserver.onNext(FilterRunFilterOnGroupResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setEnabled(FilterSetEnabledRequest request, StreamObserver<FilterSetEnabledResponse> responseObserver) {
        FilterEntity filter = getFilterEntity(request.getFilter());
        filterDao.updateSetFilterEnabled(filter, request.getEnabled());
        responseObserver.onNext(FilterSetEnabledResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setName(FilterSetNameRequest request, StreamObserver<FilterSetNameResponse> responseObserver) {
        FilterEntity filter = getFilterEntity(request.getFilter());
        filterDao.updateSetFilterName(filter, request.getName());
        responseObserver.onNext(FilterSetNameResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setType(FilterSetTypeRequest request, StreamObserver<FilterSetTypeResponse> responseObserver) {
        FilterEntity filter = getFilterEntity(request.getFilter());
        filterDao.updateSetFilterType(filter, request.getType());
        responseObserver.onNext(FilterSetTypeResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    public void setOrder(FilterSetOrderRequest request, StreamObserver<FilterSetOrderResponse> responseObserver) {
        FilterEntity filter = getFilterEntity(request.getFilter());
        filterManager.setFilterOrder(filter, (double) request.getOrder());
        responseObserver.onNext(FilterSetOrderResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    public void runFilterOnJobs(FilterRunFilterOnJobsRequest request,
                                StreamObserver<FilterRunFilterOnJobsResponse> responseObserver) {
        FilterEntity filter = getFilterEntity(request.getFilter());
        for (Job job: request.getJobs().getJobsList()) {
            filterManager.runFilterOnJob(filter, job.getId());
        }
        responseObserver.onNext(FilterRunFilterOnJobsResponse.newBuilder().build());
        responseObserver.onCompleted();
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

    private FilterEntity getFilterEntity(Filter filter) {
        return filterManager.getFilter(filter.getId());
    }

    private ActionEntity toActionEntity(Action action) {
        ActionEntity entity = new ActionEntity();
        entity.id = action.getId();
        entity.type = action.getType();
        entity.valueType = action.getValueType();
        entity.groupValue = action.getGroupValue();
        entity.stringValue = action.getStringValue();
        entity.intValue = action.getIntegerValue();
        entity.floatValue = action.getFloatValue();
        entity.booleanValue = action.getBooleanValue();
        return entity;
    }
}

