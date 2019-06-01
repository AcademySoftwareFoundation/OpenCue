
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

import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.dao.criteria.HostSearchInterface;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.host.HostSearchCriteria;

import java.util.HashSet;
import java.util.Set;

public class HostSearch extends Criteria implements HostSearchInterface {
    private HostSearchCriteria criteria;

    public HostSearch(HostSearchCriteria criteria) {
        this.criteria = criteria;
    }

    public HostSearchCriteria getCriteria() {
        return this.criteria;
    }

    public void filterByAlloc(AllocationInterface alloc) {
        addPhrase("host.pk_alloc", alloc.getAllocationId());
    }

    @Override
    public void buildWhereClause() {
        addPhrase("host.pk_host", criteria.getIdsList());
        addPhrase("host.str_name", criteria.getHostsList());
        addPhrase("host.str_name", new HashSet<>(criteria.getSubstrList()));
        addRegexPhrase("host.str_name", new HashSet<>(criteria.getRegexList()));
        addPhrase("alloc.str_name", criteria.getAllocsList());
        Set<String> items = new HashSet<>(criteria.getStates().getStateCount());
        for (HardwareState w: criteria.getStates().getStateList()) {
            items.add(w.toString());
        }
        addPhrase("host_stat.str_state", items);
    }
}
