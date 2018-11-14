
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

import com.imageworks.common.SpiIce.IntegerSearchCriterion;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.grpc.host.ProcSearchCriteria;


public class ProcSearch extends Criteria {

    private final ProcSearchGeneratorInterface procSearchGenerator;

    private ProcSearchCriteria criteria;
    private Set<Phrase> notJobs = new HashSet<Phrase>();
    private Set<Phrase> notGroups = new HashSet<Phrase>();

    ProcSearch(ProcSearchGeneratorInterface procSearchGenerator) {
        super(procSearchGenerator);
        this.procSearchGenerator = procSearchGenerator;
        criteria = ProcSearch.criteriaFactory();
    }

    ProcSearch(ProcSearchGeneratorInterface procSearchGenerator, ProcSearchCriteria criteria) {
        super(procSearchGenerator);
        this.procSearchGenerator = procSearchGenerator;
        this.criteria = criteria;
    }

    ProcSearch(ProcSearchGeneratorInterface procSearchGenerator, ProcSearchCriteria criteria, Sort sort) {
        super(procSearchGenerator);
        this.procSearchGenerator = procSearchGenerator;
        this.criteria = criteria;
        addSort(sort);
    }

    public ProcSearchCriteria getCriteria() {
        return criteria;
    }

    public void setCriteria(ProcSearchCriteria criteria) {
        this.criteria = criteria;
    }

    public static ProcSearchCriteria criteriaFactory() {
        return ProcSearchCriteria.newBuilder().build();
    }

    public void addDurationRange(IntegerSearchCriterion criterion) {
        procSearchGenerator.addDurationRange(criterion);
    }

    public ProcSearch notJobs(List<JobInterface> jobs) {
        for (JobInterface job: jobs) {
            notJobs.add(procSearchGenerator.notJob(job));
        }
        return this;
    }

    public ProcSearch notGroups(List<GroupInterface> groups) {
        for (GroupInterface group: groups) {
            notGroups.add(procSearchGenerator.notGroup(group));
        }
        return this;
    }

    public void filterByHost(HostInterface host) {
        procSearchGenerator.filterByHost(host);
    }

    public void sortByHostName() {
        procSearchGenerator.sortByHostName();
    }

    public void sortByDispatchedTime() {
        procSearchGenerator.sortByDispatchedTime();
    }

    public void sortByBookedTime() {
        procSearchGenerator.sortByBookedTime();
    }

    @Override
    public void buildWhereClause() {

        procSearchGenerator.buildWhereClause(criteria, notJobs, notGroups);

        setFirstResult(criteria.getFirstResult());
        if (criteria.getMaxResultsCount() > 0) {
            setMaxResults(criteria.getMaxResults(0));
        }
    }
}

