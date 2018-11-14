
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


package com.imageworks.spcue.dao.criteria.oracle;

import java.util.Set;

import com.imageworks.common.SpiIce.GreaterThanIntegerSearchCriterion;
import com.imageworks.common.SpiIce.InRangeIntegerSearchCriterion;
import com.imageworks.common.SpiIce.IntegerSearchCriterion;
import com.imageworks.common.SpiIce.LessThanIntegerSearchCriterion;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.dao.criteria.CriteriaException;
import com.imageworks.spcue.dao.criteria.Phrase;
import com.imageworks.spcue.dao.criteria.ProcSearchGeneratorInterface;
import com.imageworks.spcue.dao.criteria.postgres.CriteriaGenerator;
import com.imageworks.spcue.grpc.host.ProcSearchCriteria;


public class ProcSearchGenerator extends CriteriaGenerator implements ProcSearchGeneratorInterface {
    public void addDurationRange(IntegerSearchCriterion criterion) {
        StringBuilder sb = new StringBuilder(128);
        final Class<? extends IntegerSearchCriterion> c = criterion.getClass();

        if (c == LessThanIntegerSearchCriterion.class) {
            LessThanIntegerSearchCriterion r = (LessThanIntegerSearchCriterion) criterion;
            values.add(r.value);
            sb.append(" (find_duration(proc.ts_dispatched, null) <= ?) ");
        }
        else if (c == GreaterThanIntegerSearchCriterion.class) {
            GreaterThanIntegerSearchCriterion r = (GreaterThanIntegerSearchCriterion) criterion;
            values.add(r.value);
            sb.append(" (find_duration(proc.ts_dispatched, null) >= ?) ");
        }
        else if (c == InRangeIntegerSearchCriterion.class) {
            InRangeIntegerSearchCriterion r = (InRangeIntegerSearchCriterion) criterion;
            values.add(r.min);
            values.add(r.max);
            sb.append(" (find_duration(proc.ts_dispatched, null) BETWEEN ? AND ? )");
        }
        else {
            throw new CriteriaException("Invalid criteria class used for duration range search: "
                    + criterion.getClass().getCanonicalName());
        }
        chunks.add(sb);
    }

    public Phrase notJob(JobInterface job) {
        return new Phrase("proc.pk_job","!=", job.getJobId());
    }

    public Phrase notGroup(GroupInterface group) {
        return new Phrase("folder.pk_folder","!=", group.getGroupId());
    }

    public void buildWhereClause(ProcSearchCriteria criteria, Set<Phrase> notJobs, Set<Phrase> notGroups) {
        addPhrases(notJobs, "AND");
        addPhrases(notGroups, "AND");

        addPhrase("host.str_name", criteria.getHostsList());
        addPhrase("job.str_name", criteria.getJobsList());
        addPhrase("layer.str_name", criteria.getLayersList());
        addPhrase("show.str_name", criteria.getShowsList());
        addPhrase("alloc.str_name", criteria.getAllocsList());

        // TODO: (gdenton) b/117847423 reimplement the Criterion objects in grpc
        // if (criteria.getMemoryRangeCount() > 0) {
        //     addRangePhrase("proc.int_mem_reserved", criteria.getMemoryRange(0));
        // }
        //
        // if (criteria.getDurationRangeCount() > 0) {
        //     addDurationRange(criteria.getDurationRange(0));
        // }
    }
}
