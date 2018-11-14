
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

import java.util.List;

import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.grpc.job.FrameSearchCriteria;
import com.imageworks.spcue.grpc.job.FrameState;


public class FrameSearch extends Criteria {
    private static final int MAX_RESULTS = 1000;

    private final FrameSearchGeneratorInterface frameSearchGenerator;

    private FrameSearchCriteria criteria;
    private int page = 1;
    private int limit = 1000;

    private JobInterface job;
    private LayerInterface layer;
    private String sortedQuery;

    FrameSearch(FrameSearchGeneratorInterface frameSearchGenerator, List<String> list) {
        super(frameSearchGenerator);
        this.frameSearchGenerator = frameSearchGenerator;
        this.criteria = criteriaFactory().toBuilder().addAllIds(list).build();
    }

    FrameSearch(FrameSearchGeneratorInterface frameSearchGenerator, JobInterface job) {
        super(frameSearchGenerator);
        this.frameSearchGenerator = frameSearchGenerator;
        this.criteria = criteriaFactory();
        this.job = job;
    }

    FrameSearch(FrameSearchGeneratorInterface frameSearchGenerator, FrameInterface frame) {
        super(frameSearchGenerator);
        this.frameSearchGenerator = frameSearchGenerator;
        this.criteria = criteriaFactory().toBuilder().addIds(frame.getFrameId()).build();
        this.job = frame;
    }

    FrameSearch(
            FrameSearchGeneratorInterface frameSearchGenerator,
            JobInterface job,
            FrameSearchCriteria criteria) {
        super(frameSearchGenerator);
        this.frameSearchGenerator = frameSearchGenerator;
        this.criteria = criteria;
        this.job = job;
    }

    FrameSearch(FrameSearchGeneratorInterface frameSearchGenerator, LayerInterface layer) {
        super(frameSearchGenerator);
        this.frameSearchGenerator = frameSearchGenerator;
        this.criteria = criteriaFactory();
        this.layer = layer;
    }

    FrameSearch(
            FrameSearchGeneratorInterface frameSearchGenerator,
            LayerInterface layer,
            FrameSearchCriteria criteria) {
        super(frameSearchGenerator);
        this.frameSearchGenerator = frameSearchGenerator;
        this.criteria = criteria;
        this.layer = layer;
    }

    public FrameSearchCriteria getCriteria() {
        return criteria;
    }

    public void setCriteria(FrameSearchCriteria criteria) {
        this.criteria = criteria;
    }

    public JobInterface getJob() {
        if (job == null) {
            return layer;
        }
        return job;
    }

    private static FrameSearchCriteria criteriaFactory() {
        return FrameSearchCriteria.newBuilder()
                .setPage(1)
                .setLimit(1000)
                .setChangeDate(0)
                .build();
    }


    public String getSortedQuery(String query) {
        if (built) {
            return sortedQuery;
        }

        if (limit <= 0 || limit >= MAX_RESULTS) {
            criteria = criteria.toBuilder().setLimit(MAX_RESULTS).build();
        }
        if (page <= 0) {
            page = 1;
        }

        sortedQuery = frameSearchGenerator.getSortedQuery(getQuery(query), page, limit);
        return sortedQuery;
    }

    public void addFrameStates(List<FrameState> frameStates) {
        frameSearchGenerator.addFrameStates(frameStates);
    }

    public void addFrameSet(String frameSet) {
        frameSearchGenerator.addFrameSet(frameSet);
    }

    public void addMemoryRange(String range) {
        frameSearchGenerator.addMemoryRange(range);
    }

    public void addDurationRange(String range) {
        frameSearchGenerator.addDurationRange(range);
    }

    public void addChangeDate(int changeDate) {
        frameSearchGenerator.addChangeDate(changeDate);
    }

    public void addLayers(List<LayerInterface> layers) {
        frameSearchGenerator.addLayers(layers);
    }

    @Override
    public void buildWhereClause() {
        frameSearchGenerator.buildWhereClause(criteria, job, layer);

        limit = criteria.getLimit();
        page = criteria.getPage();
    }
}

