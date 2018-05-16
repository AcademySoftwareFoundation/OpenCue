
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

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import com.imageworks.spcue.Allocation;
import com.imageworks.spcue.CueClientIce.HostSearchCriteria;
import com.imageworks.spcue.CueIce.HardwareState;

public class HostSearch extends Criteria {

    private HostSearchCriteria criteria;

    public HostSearch() {
        this.criteria = criteriaFactory();
    }

    public HostSearch(HostSearchCriteria criteria) {
        this.criteria = criteria;
    }

    public HostSearchCriteria getCriteria() {
        return this.criteria;
    }

    public static final HostSearch byAllocation(Allocation a) {
        HostSearch r = new HostSearch();
        r.addPhrase("host.pk_alloc",a.getAllocationId());
        return r;
    }

    public static final HostSearchCriteria criteriaFactory() {
        HostSearchCriteria c = new HostSearchCriteria(
                new HashSet<String>(),
                new HashSet<String>(),
                new HashSet<String>(),
                new HashSet<String>(),
                new HashSet<String>(),
                new ArrayList<HardwareState>());
        return c;
    }

    public void addHardwareStates(List<HardwareState> s) {
        // Convert into list of strings and call the
        // super class addPhrase
        Set<String> items = new HashSet<String>(s.size());
        for (HardwareState w: s) {
            items.add(w.toString());
        }
        addPhrase("host_stat.str_state",items);
    }

    @Override
    public void buildWhereClause() {
        addPhrase("host.pk_host",criteria.ids);
        addPhrase("host.str_name",criteria.hosts);
        addLikePhrase("host.str_name",criteria.substr);
        addRegexPhrase("host.str_name",criteria.regex);
        addPhrase("alloc.str_name",criteria.allocs);
        addHardwareStates(criteria.states);
    }
}

