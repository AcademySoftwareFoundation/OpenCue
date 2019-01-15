
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
import com.imageworks.spcue.config.DatabaseEngine;
import com.imageworks.spcue.grpc.job.JobSearchCriteria;
import com.imageworks.spcue.dao.criteria.postgres.JobSearch;

public class JobSearchFactory {
    private DatabaseEngine dbEngine;

    public JobSearchInterface create() {
        if (dbEngine.equals(DatabaseEngine.POSTGRES)) {
            return new JobSearch();
        } else if (dbEngine.equals(DatabaseEngine.ORACLE)) {
            return new com.imageworks.spcue.dao.criteria.oracle.JobSearch();
        } else {
            throw new RuntimeException(
                    "current database engine is not supported by JobSearchFactory");
        }
    }

    public JobSearchInterface create(JobSearchCriteria criteria) {
        JobSearchInterface jobSearch = create();
        jobSearch.setCriteria(criteria);
        return jobSearch;
    }

    public JobSearchInterface create(ShowInterface show) {
        JobSearchInterface jobSearch = create();
        jobSearch.filterByShow(show);
        return jobSearch;
    }

    public DatabaseEngine getDbEngine() {
        return dbEngine;
    }

    public void setDbEngine(DatabaseEngine dbEngine) {
        this.dbEngine = dbEngine;
    }
}
