
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

package com.imageworks.spcue.dao.criteria.postgres;

import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.dao.criteria.JobSearchInterface;
import com.imageworks.spcue.grpc.job.JobSearchCriteria;

import java.util.HashSet;

public final class JobSearch extends Criteria implements JobSearchInterface {
    private JobSearchCriteria criteria;

    public JobSearch() {
        criteria = JobSearchInterface.criteriaFactory();
    }

    @Override
    public JobSearchCriteria getCriteria() {
        return criteria;
    }

    @Override
    public void setCriteria(JobSearchCriteria criteria) {
        this.criteria = criteria;
    }

    @Override
    public void filterByShow(ShowInterface show) {
        addPhrase("job.pk_show", show.getShowId());
    }

    @Override
    void buildWhereClause() {
        addPhrase("job.pk_job", criteria.getIdsList());
        addPhrase("job.str_name", criteria.getJobsList());
        addLikePhrase("job.str_name", new HashSet<>(criteria.getSubstrList()));
        addRegexPhrase("job.str_name", new HashSet<>(criteria.getRegexList()));
        addPhrase("job.str_shot", criteria.getShotsList());
        addPhrase("show.str_name", criteria.getShowsList());
        addPhrase("job.str_user", criteria.getUsersList());
        if (!criteria.getIncludeFinished()) {
            addPhrase("job.str_state", "PENDING");
        }
    }
}
