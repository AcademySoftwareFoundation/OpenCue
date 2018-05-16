
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
import java.util.List;
import java.util.Set;

import com.imageworks.common.SpiIce.GreaterThanIntegerSearchCriterion;
import com.imageworks.common.SpiIce.InRangeIntegerSearchCriterion;
import com.imageworks.common.SpiIce.IntegerSearchCriterion;
import com.imageworks.common.SpiIce.LessThanIntegerSearchCriterion;
import com.imageworks.spcue.Group;
import com.imageworks.spcue.Job;
import com.imageworks.spcue.CueClientIce.ProcSearchCriteria;

public class ProcSearch extends Criteria {

    private ProcSearchCriteria criteria;
    private Set<Phrase> notJobs = new HashSet<Phrase>();
    private Set<Phrase> notGroups = new HashSet<Phrase>();

    public ProcSearch() {
        criteria = ProcSearch.criteriaFactory();
    }

    public ProcSearch(ProcSearchCriteria criteria) {
        this.criteria = criteria;
    }

    public ProcSearch(ProcSearchCriteria criteria, Sort o) {
        this.criteria = criteria;
        this.addSort(o);
    }

    public ProcSearchCriteria getCriteria() {
        return criteria;
    }

    public static final ProcSearchCriteria criteriaFactory() {
        ProcSearchCriteria c = new ProcSearchCriteria(
                1, new int[] {},
                new HashSet<String>(),
                new HashSet<String>(),
                new HashSet<String>(),
                new HashSet<String>(),
                new HashSet<String>(),
                new IntegerSearchCriterion[] { },
                new IntegerSearchCriterion[] { });
        return c;
    }

    public void addDurationRange(IntegerSearchCriterion e) {
        StringBuilder sb = new StringBuilder(128);
        final Class<? extends IntegerSearchCriterion> c = e.getClass();

        if (c == LessThanIntegerSearchCriterion.class) {
            LessThanIntegerSearchCriterion r = (LessThanIntegerSearchCriterion) e;
            values.add(r.value);
            sb.append(" (find_duration(proc.ts_dispatched, null) <= ?) ");
        }
        else if (c == GreaterThanIntegerSearchCriterion.class) {
            GreaterThanIntegerSearchCriterion r = (GreaterThanIntegerSearchCriterion) e;
            values.add(r.value);
            sb.append(" (find_duration(proc.ts_dispatched, null) >= ?) ");
        }
        else if (c == InRangeIntegerSearchCriterion.class) {
            InRangeIntegerSearchCriterion r = (InRangeIntegerSearchCriterion) e;
            values.add(r.min);
            values.add(r.max);
            sb.append(" (find_duration(proc.ts_dispatched, null) BETWEEN ? AND ? )");
        }
        else {
            throw new CriteriaException("Invalid criteria class used for duration range search: "
                    + e.getClass().getCanonicalName());
        }
        chunks.add(sb);
    }

    public ProcSearch notJobs(List<Job> jobs) {
        for (Job job: jobs) {
            notJobs.add(new Phrase("proc.pk_job","!=",job.getJobId()));
        }
        return this;
    }

    public ProcSearch notGroups(List<Group> groups) {
        for (Group group: groups) {
            notGroups.add(new Phrase("folder.pk_folder","!=", group.getGroupId()));
        }
        return this;
    }

    @Override
    public void buildWhereClause() {

        addPhrases(notJobs, "AND");
        addPhrases(notGroups, "AND");

        addPhrase("host.str_name", criteria.hosts);
        addPhrase("job.str_name",criteria.jobs);
        addPhrase("layer.str_name",criteria.layers);
        addPhrase("show.str_name",criteria.shows);
        addPhrase("alloc.str_name",criteria.allocs);

        if (criteria.memoryRange.length > 0) {
            addRangePhrase("proc.int_mem_reserved", criteria.memoryRange[0]);
        }

        if (criteria.durationRange.length > 0) {
            addDurationRange(criteria.durationRange[0]);
        }

        setFirstResult(criteria.firstResult);
        if (criteria.maxResults.length > 0) {
            setMaxResults(criteria.maxResults[0]);
        }
    }
}

