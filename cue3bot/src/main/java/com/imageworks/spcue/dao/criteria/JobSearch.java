
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

import com.imageworks.spcue.Show;
import com.imageworks.spcue.CueClientIce.JobSearchCriteria;

public final class JobSearch extends Criteria {

    private JobSearchCriteria criteria;

    /**
     * Easy factory method for grabbing jobs by show;
     *
     * @param show
     * @return
     */
    public static final JobSearch byShow(Show s) {
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
        JobSearchCriteria c = new JobSearchCriteria(
                new HashSet<String>(),
                new HashSet<String>(),
                new HashSet<String>(),
                new HashSet<String>(),
                new HashSet<String>(),
                new HashSet<String>(),
                new HashSet<String>(),
                false);
        return c;
    }

    public void buildWhereClause() {
        addPhrase("job.pk_job", criteria.ids);
        addPhrase("job.str_name", criteria.jobs);
        addLikePhrase("job.str_name", criteria.substr);
        addRegexPhrase("job.str_name", criteria.regex);
        addPhrase("job.str_shot", criteria.shots);
        addPhrase("show.str_name", criteria.shows);
        addPhrase("job.str_user", criteria.users);
        if (criteria.includeFinished) {
            chunks.add(new StringBuilder(" ROWNUM < 200"));
        } else {
            addPhrase("job.str_state", "Pending");
        }
    }
}

