
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

import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.apache.log4j.Logger;

import com.imageworks.spcue.Frame;
import com.imageworks.spcue.Job;
import com.imageworks.spcue.Layer;
import com.imageworks.spcue.CueClientIce.FrameSearchCriteria;
import com.imageworks.spcue.CueIce.FrameState;
import com.imageworks.spcue.util.CueUtil;
import com.imageworks.spcue.util.FrameSet;


public class FrameSearch extends Criteria {
    private static final Logger logger = Logger.getLogger(FrameSearch.class);

    private FrameSearchCriteria criteria;
    private int page = 1;
    private int limit = 1000;

    private Job job;
    private Layer layer;
    private String jobCol = "job.pk_job";
    private String sortedQuery;

    public FrameSearch(List<String> list) {
        this.criteria = criteriaFactory();
        this.criteria.ids.addAll(list);
    }

    public FrameSearch(Job job) {
        this.criteria = criteriaFactory();
        this.job = job;
    }

    public FrameSearch(Frame frame) {
        this.criteria = criteriaFactory();
        this.job = frame;
        this.criteria.ids.add(frame.getFrameId());
    }

    public FrameSearch(Job job, FrameSearchCriteria criteria) {
        this.criteria = criteria;
        this.job = job;
    }

    public FrameSearch(Layer layer) {
        this.criteria = criteriaFactory();
        this.layer = layer;
    }

    public FrameSearch(Layer layer, FrameSearchCriteria criteria) {
        this.criteria = criteria;
        this.layer = layer;
    }

    public FrameSearchCriteria getCriteria() {
        return criteria;
    }

    public Job getJob() {
        if (job == null) {
            return (Job) layer;
        }
        return job;
    }

    public void setJobCol(String jobCol) {
        this.jobCol = jobCol;
    }

    public static final FrameSearchCriteria criteriaFactory() {
        FrameSearchCriteria c = new FrameSearchCriteria(
                new HashSet<String>(),
                new HashSet<String>(),
                new HashSet<String>(),
                new ArrayList<FrameState>(),
                null,
                null,
                null,
                1, 1000, 0);
        return c;
    }

    private static final int MAX_RESULTS = 1000;

    public String getSortedQuery(String query) {

        if (built) {
            return sortedQuery;
        }

        String q = getQuery(query);
        if (limit <=0 || limit >= MAX_RESULTS) {
            criteria.limit = MAX_RESULTS;
        }
        if (page <= 0) {
            page = 1;
        }

        /**
         * ROW is a special value we are setting up in
         * the frame query.  ROW_NUM cannot be used to do
         * LIMIT/OFFSET behavior.
         */
        StringBuilder sb = new StringBuilder(q.length() + 256);
        sb.append("SELECT * FROM (");
        sb.append(q);
        if (getDatabaseEngine().equals("postgres")) {
            sb.append(" ) AS getSortedQueryT WHERE row_number > ?");
        } else {
            sb.append(" ) WHERE row_number > ?");
        }
        sb.append(" AND row_number <= ?");
        values.add((page-1) * limit);
        values.add(page * limit);
        sortedQuery = sb.toString();
        return sortedQuery;
    }

    public void addFrameStates(List<FrameState> s) {
        // Convert into list of strings and call the
        // super class addPhrase
        Set<String> items = new HashSet<String>(s.size());
        for (FrameState w: s) {
            items.add(w.toString());
        }
        addPhrase("frame.str_state",items);
    }

    private static final Pattern PATTERN_SINGLE_FRAME = Pattern.compile("^([0-9]+)$");
    private static final Pattern PATTERN_RANGE = Pattern.compile("^([0-9]+)\\-([0-9]+)$");
    private static final int RANGE_MAX_SIZE = 1000;

    public void addFrameSet(String frameSet) {
        StringBuilder sb = new StringBuilder(8096);
        Matcher matchRange = PATTERN_RANGE.matcher(frameSet);
        Matcher matchSingle = PATTERN_SINGLE_FRAME.matcher(frameSet);

        if (matchSingle.matches()) {
            sb.append("frame.int_number=?");
            values.add(matchSingle.group(1));
        }
        else if (matchRange.matches()) {
            sb.append(" ( frame.int_number >= ? AND ");
            sb.append(" frame.int_number <= ? )");
            values.add(matchRange.group(1));
            values.add(matchRange.group(2));
        }
        else {
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

    private static final Pattern PATTERN_FLOAT_RANGE = Pattern.compile("^([0-9\\.]+)\\-([0-9\\.]+)$");

    public void addMemoryRange(String range) {
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

    public void addDurationRange(String range) {
        StringBuilder sb = new StringBuilder(128);
        Matcher matchRange = PATTERN_FLOAT_RANGE.matcher(range);
        try {
            if (matchRange.matches()) {
                values.add((int) (3600 * Float.valueOf(matchRange.group(1))));
                values.add((int) (3600 * Float.valueOf(matchRange.group(2))));
                sb.append(" (frame.str_state != 'Waiting' ");
                sb.append(" AND find_duration(frame.ts_started, frame.ts_stopped) ");
                sb.append(" BETWEEN ? AND ? )");
            }
            else {
                values.add((int) (3600 * Float.valueOf(range)));
                sb.append(" (frame.str_state != 'Waiting' AND ");
                sb.append("find_duration(frame.ts_started, frame.ts_stopped) >= ?) ");
            }
        } catch (RuntimeException e) {
            logger.warn("Failed to convert float range: " + range + "," + e);
            // a cast failed, ignore for now.
        }
        chunks.add(sb);
    }

    public void addChangeDate(int changeDate) {
        StringBuilder sb = new StringBuilder();
        sb.append("frame.ts_updated > ?");
        chunks.add(sb);
        values.add(new java.sql.Timestamp( changeDate * 1000l));
    }

    @Override
    public void buildWhereClause() {

        addPhrase("frame.pk_frame",criteria.ids);

        if (layer != null) {
            addPhrase("layer.pk_layer",layer.getLayerId());
        }
        if (job != null) {
            addPhrase(jobCol,job.getJobId());
        }

        addPhrase("frame.str_name", criteria.frames);
        addPhrase("layer.str_name",criteria.layers);
        addFrameStates(criteria.states);
        if (isValid(criteria.frameRange)) { addFrameSet(criteria.frameRange); }
        if (isValid(criteria.memoryRange)) { addMemoryRange(criteria.memoryRange); }
        if (isValid(criteria.durationRange)) { addDurationRange(criteria.durationRange); }
        if (criteria.changeDate > 0) { addChangeDate(criteria.changeDate); }

        limit = criteria.limit;
        page = criteria.page;

    }
}

