
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

import java.util.HashSet;

import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.grpc.job.JobSearchCriteria;

public final class JobSearch extends Criteria {

    private JobSearchCriteria criteria;

    /**
     * Easy factory method for grabbing jobs by show;
     *
     * @param s
     * @return
     */
    public static final JobSearch byShow(ShowInterface s) {
        JobSearch c = new JobSearch();
        c.addPhrase("job.pk_show", s.getShowId());
        return c;
    }

    public JobSearch(JobSearchCriteria criteria) {
        this.criteria = criteria;
    }

    public JobSearch() {
        this.criteria = criteriaFactory();
    }

    public JobSearchCriteria getGetCriteria() {
        return this.criteria;
    }

    public static final JobSearchCriteria criteriaFactory() {
        return JobSearchCriteria.newBuilder()
                .setIncludeFinished(false)
                .build();
    }

    public void buildWhereClause() {
        addPhrase("job.pk_job", criteria.getIdsList());
        addPhrase("job.str_name", criteria.getJobsList());
        addLikePhrase("job.str_name", new HashSet<String>(criteria.getSubstrList()));
        addRegexPhrase("job.str_name", new HashSet<String>(criteria.getRegexList()));
        addPhrase("job.str_shot", criteria.getShotsList());
        addPhrase("show.str_name", criteria.getShowsList());
        addPhrase("job.str_user", criteria.getUsersList());
        if (criteria.getIncludeFinished()) {
            chunks.add(new StringBuilder(" ROWNUM < 200"));
        } else {
            addPhrase("job.str_state", "Pending");
        }
    }
}

