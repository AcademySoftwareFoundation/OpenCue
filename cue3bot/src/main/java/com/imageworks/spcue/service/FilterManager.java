
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



package com.imageworks.spcue.service;

import java.util.List;

import com.imageworks.spcue.Action;
import com.imageworks.spcue.ActionDetail;
import com.imageworks.spcue.Filter;
import com.imageworks.spcue.FilterDetail;
import com.imageworks.spcue.Group;
import com.imageworks.spcue.Job;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.Matcher;
import com.imageworks.spcue.MatcherDetail;

public interface FilterManager {

    void runFiltersOnJob(JobDetail job);
    void runFilterOnJob(FilterDetail filter, JobDetail job);
    void runFilterOnJob(FilterDetail filter, String id);
    void runFilterOnGroup(FilterDetail filter, Group group);

    void lowerFilterOrder(Filter f);
    void raiseFilterOrder(Filter f);
    void setFilterOrder(Filter f, double order);

    void createFilter(FilterDetail filter);
    void createAction(ActionDetail action);
    void createMatcher(MatcherDetail action);

    void deleteFilter(Filter f);
    void deleteAction(Action action);
    void deleteMatcher(Matcher matcher);

    void updateMatcher(MatcherDetail matcher);
    void updateAction(ActionDetail action);

    FilterDetail getFilter(String id);
    MatcherDetail getMatcher(String id);
    ActionDetail getAction(String id);

    FilterDetail getFilter(Filter filter);
    MatcherDetail getMatcher(Matcher matcher);
    ActionDetail getAction(Action action);

    boolean applyAction(ActionDetail action, JobDetail job);
    boolean applyAction(ActionDetail action, JobDetail job, FilterManagerService.Context context);
    boolean applyActions(List<ActionDetail> actions, JobDetail job, FilterManagerService.Context context);
    boolean applyActions(List<ActionDetail> actions, JobDetail job);

    public boolean isMatch(MatcherDetail matcher, JobDetail job);

}

