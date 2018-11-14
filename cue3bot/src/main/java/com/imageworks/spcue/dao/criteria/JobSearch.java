
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

import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.grpc.job.Job;
import com.imageworks.spcue.grpc.job.JobSearchCriteria;

public final class JobSearch extends Criteria {

    private final JobSearchGeneratorInterface jobSearchGenerator;

    private JobSearchCriteria criteria;

    JobSearch(JobSearchGeneratorInterface jobSearchGenerator, JobSearchCriteria criteria) {
        super(jobSearchGenerator);
        this.jobSearchGenerator = jobSearchGenerator;
        this.criteria = criteria;
    }

    JobSearch(JobSearchGeneratorInterface jobSearchGenerator) {
        super(jobSearchGenerator);
        this.jobSearchGenerator = jobSearchGenerator;
        this.criteria = criteriaFactory();
    }

    JobSearch(JobSearchGeneratorInterface jobSearchGenerator, ShowInterface show) {
        super(jobSearchGenerator);
        this.jobSearchGenerator = jobSearchGenerator;
        jobSearchGenerator.filterByShow(show);
    }

    public JobSearchCriteria getGetCriteria() {
        return this.criteria;
    }

    public static JobSearchCriteria criteriaFactory() {
        return JobSearchCriteria.newBuilder()
                .setIncludeFinished(false)
                .build();
    }

    public void buildWhereClause() {
        jobSearchGenerator.buildWhereClause(criteria);
    }
}

