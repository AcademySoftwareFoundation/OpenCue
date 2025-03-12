
/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */

package com.imageworks.spcue.service;

import java.util.List;

import com.imageworks.spcue.ActionEntity;
import com.imageworks.spcue.ActionInterface;
import com.imageworks.spcue.FilterEntity;
import com.imageworks.spcue.FilterInterface;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.MatcherEntity;
import com.imageworks.spcue.MatcherInterface;

public interface FilterManager {

    void runFiltersOnJob(JobDetail job);

    void runFilterOnJob(FilterEntity filter, JobDetail job);

    void runFilterOnJob(FilterEntity filter, String id);

    void runFilterOnGroup(FilterEntity filter, GroupInterface group);

    void lowerFilterOrder(FilterInterface f);

    void raiseFilterOrder(FilterInterface f);

    void setFilterOrder(FilterInterface f, double order);

    void createFilter(FilterEntity filter);

    void createAction(ActionEntity action);

    void createMatcher(MatcherEntity action);

    void deleteFilter(FilterInterface f);

    void deleteAction(ActionInterface action);

    void deleteMatcher(MatcherInterface matcher);

    void updateMatcher(MatcherEntity matcher);

    void updateAction(ActionEntity action);

    FilterEntity getFilter(String id);

    MatcherEntity getMatcher(String id);

    ActionEntity getAction(String id);

    FilterEntity getFilter(FilterInterface filter);

    MatcherEntity getMatcher(MatcherInterface matcher);

    ActionEntity getAction(ActionInterface action);

    boolean applyAction(ActionEntity action, JobDetail job);

    boolean applyAction(ActionEntity action, JobDetail job, FilterManagerService.Context context);

    boolean applyActions(List<ActionEntity> actions, JobDetail job,
            FilterManagerService.Context context);

    boolean applyActions(List<ActionEntity> actions, JobDetail job);

    public boolean isMatch(MatcherEntity matcher, JobDetail job);

}
