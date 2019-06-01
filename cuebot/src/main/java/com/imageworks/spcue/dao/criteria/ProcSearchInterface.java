
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

package com.imageworks.spcue.dao.criteria;

import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.grpc.criterion.GreaterThanIntegerSearchCriterion;
import com.imageworks.spcue.grpc.criterion.InRangeIntegerSearchCriterion;
import com.imageworks.spcue.grpc.criterion.LessThanIntegerSearchCriterion;
import com.imageworks.spcue.grpc.host.ProcSearchCriteria;

import java.util.List;

public interface ProcSearchInterface extends CriteriaInterface {
    ProcSearchCriteria getCriteria();
    void setCriteria(ProcSearchCriteria criteria);
    void notJobs(List<JobInterface> jobs);
    void notGroups(List<GroupInterface> groups);
    void filterByDurationRange(LessThanIntegerSearchCriterion criterion);
    void filterByDurationRange(GreaterThanIntegerSearchCriterion criterion);
    void filterByDurationRange(InRangeIntegerSearchCriterion criterion);
    void filterByHost(HostInterface host);
    void sortByHostName();
    void sortByDispatchedTime();
    void sortByBookedTime();

    static ProcSearchCriteria criteriaFactory() {
        return ProcSearchCriteria.newBuilder().build();
    }
}
