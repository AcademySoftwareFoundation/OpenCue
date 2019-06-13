
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

import com.imageworks.spcue.dao.criteria.postgres.ProcSearch;
import com.imageworks.spcue.grpc.host.ProcSearchCriteria;
import org.springframework.stereotype.Component;

@Component
public class ProcSearchFactory {

    public ProcSearchInterface create() {
        return new ProcSearch();
    }

    public ProcSearchInterface create(ProcSearchCriteria criteria) {
        ProcSearchInterface procSearch = create();
        procSearch.setCriteria(criteria);
        return procSearch;
    }

    public ProcSearchInterface create(ProcSearchCriteria criteria, Sort sort) {
        ProcSearchInterface procSearch = create();
        procSearch.setCriteria(criteria);
        procSearch.addSort(sort);
        return procSearch;
    }
}
