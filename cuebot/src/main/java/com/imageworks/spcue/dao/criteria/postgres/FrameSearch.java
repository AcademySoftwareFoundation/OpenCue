
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

import com.google.common.collect.ImmutableList;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.dao.criteria.FrameSearchInterface;
import com.imageworks.spcue.grpc.job.FrameSearchCriteria;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.util.CueUtil;
import com.imageworks.spcue.util.FrameSet;
import org.apache.log4j.Logger;

import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

public class FrameSearch extends Criteria implements FrameSearchInterface {
    private static final int MAX_RESULTS = 1000;
    private static final Logger logger = Logger.getLogger(FrameSearch.class);
    private static final Pattern PATTERN_SINGLE_FRAME = Pattern.compile("^([0-9]+)$");
    private static final Pattern PATTERN_RANGE = Pattern.compile("^([0-9]+)\\-([0-9]+)$");
    private static final Pattern PATTERN_FLOAT_RANGE = Pattern.compile("^([0-9\\.]+)\\-([0-9\\.]+)$");
    private static final int RANGE_MAX_SIZE = 1000;

    private FrameSearchCriteria criteria;
    private String sortedQuery;

    public FrameSearch() {
        criteria = FrameSearchInterface.criteriaFactory();
    }

    @Override
    public FrameSearchCriteria getCriteria() {
        return criteria;
    }

    @Override
    public void setCriteria(FrameSearchCriteria criteria) {
        this.criteria = criteria;
    }

    @Override
    public String getSortedQuery(String query) {
        if (built) {
            return sortedQuery;
        }

        int limit = criteria.getLimit();
        int page = criteria.getPage();

        if (limit <= 0 || limit >= MAX_RESULTS) {
            criteria = criteria.toBuilder().setLimit(MAX_RESULTS).build();
        }
        if (page <= 0) {
            page = 1;
        }

        StringBuilder sb = new StringBuilder(query.length() + 256);
        sb.append("SELECT * FROM (");
        sb.append(getFilteredQuery(query));
        sb.append(" ) AS getSortedQueryT WHERE row_number > ?");
        sb.append(" AND row_number <= ?");
        values.add((page - 1) * limit);
        values.add(page * limit);
        sortedQuery = sb.toString();
        return sortedQuery;
    }

    @Override
    public void filterByFrameIds(List<String> frameIds) {
        criteria = criteria.toBuilder().addAllIds(frameIds).build();
    }

    @Override
    public void filterByJob(JobInterface job) {
        addPhrase("job.pk_job", job.getJobId());
    }

    @Override
    public void filterByFrame(FrameInterface frame) {
        filterByFrameIds(ImmutableList.of(frame.getFrameId()));
    }

    @Override
    public void filterByLayer(LayerInterface layer) {
        addPhrase("layer.pk_layer", layer.getLayerId());
    }

    @Override
    public void filterByLayers(List<LayerInterface> layers) {
        addPhrase(
                "layer.pk_layer",
                layers.stream().map(LayerInterface::getLayerId).collect(Collectors.toList()));
    }

    @Override
    public void filterByFrameStates(List<FrameState> frameStates) {
        addPhrase(
                "frame.str_state",
                frameStates.stream().map(FrameState::toString).collect(Collectors.toSet()));
    }

    @Override
    public void filterByFrameSet(String frameSet) {
        StringBuilder sb = new StringBuilder(8096);
        Matcher matchRange = PATTERN_RANGE.matcher(frameSet);
        Matcher matchSingle = PATTERN_SINGLE_FRAME.matcher(frameSet);

        if (matchSingle.matches()) {
            sb.append("frame.int_number=?");
            values.add(Integer.valueOf(matchSingle.group(1)));
        } else if (matchRange.matches()) {
            sb.append(" ( frame.int_number >= ? AND ");
            sb.append(" frame.int_number <= ? )");
            values.add(Integer.valueOf(matchRange.group(1)));
            values.add(Integer.valueOf(matchRange.group(2)));
        } else {
            FrameSet set = new FrameSet(frameSet);
            int num_frames = set.size();
            if (num_frames <= RANGE_MAX_SIZE) {
                sb.append("(");
                for (int i=0; i<num_frames; i++)  {
                    sb.append("frame.int_number=? OR ");
                    values.add(set.get(i));
                }
                sb.delete(sb.length()-4, sb.length());
                sb.append(") ");
            }
        }
        chunks.add(sb);
    }

    @Override
    public void filterByMemoryRange(String range) {
        StringBuilder sb = new StringBuilder(128);
        Matcher matchRange = PATTERN_FLOAT_RANGE.matcher(range);
        try {
            if (matchRange.matches()) {
                values.add(CueUtil.GB * Float.valueOf(matchRange.group(1)));
                values.add(CueUtil.GB * Float.valueOf(matchRange.group(2)));
                sb.append(" (frame.int_mem_max_used >= ? AND frame.int_mem_max_used <= ?) ");
            }
            else {
                values.add(CueUtil.GB * Float.valueOf(range));
                sb.append(" frame.int_mem_max_used >= ? ");
            }
        } catch (RuntimeException e) {
            logger.warn("Failed to convert float range: " + range + "," + e);
        }
        chunks.add(sb);
    }

    @Override
    public void filterByDurationRange(String range) {
        StringBuilder sb = new StringBuilder(128);
        Matcher matchRange = PATTERN_FLOAT_RANGE.matcher(range);
        try {
            if (matchRange.matches()) {
                values.add((int) (3600 * Float.valueOf(matchRange.group(1))));
                values.add((int) (3600 * Float.valueOf(matchRange.group(2))));
                sb.append(" (frame.str_state != 'WAITING' ");
                sb.append(" AND find_duration(frame.ts_started, frame.ts_stopped) ");
                sb.append(" BETWEEN ? AND ? )");
            }
            else {
                values.add((int) (3600 * Float.valueOf(range)));
                sb.append(" (frame.str_state != 'WAITING' AND ");
                sb.append("find_duration(frame.ts_started, frame.ts_stopped) >= ?) ");
            }
        } catch (RuntimeException e) {
            logger.warn("Failed to convert float range: " + range + "," + e);
            // a cast failed, ignore for now.
        }
        System.out.println(sb.toString());
        System.out.println(values);
        chunks.add(sb);
    }

    @Override
    public void filterByChangeDate(int changeDate) {
        StringBuilder sb = new StringBuilder();
        sb.append("frame.ts_updated > ?");
        chunks.add(sb);
        values.add(new java.sql.Timestamp( changeDate * 1000L));
    }

    @Override
    void buildWhereClause() {
        addPhrase("frame.pk_frame", criteria.getIdsList());

        addPhrase("frame.str_name", criteria.getFramesList());
        addPhrase("layer.str_name", criteria.getLayersList());
        filterByFrameStates(criteria.getStates().getFrameStatesList());
        if (isValid(criteria.getFrameRange())) { filterByFrameSet(criteria.getFrameRange()); }
        if (isValid(criteria.getMemoryRange())) { filterByMemoryRange(criteria.getMemoryRange()); }
        if (isValid(criteria.getDurationRange())) { filterByDurationRange(criteria.getDurationRange()); }
        if (criteria.getChangeDate() > 0) { filterByChangeDate(criteria.getChangeDate()); }
    }
}
