package com.imageworks.spcue.dao.criteria.oracle;

import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

import org.apache.log4j.Logger;

import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.dao.criteria.FrameSearchGeneratorInterface;
import com.imageworks.spcue.grpc.job.FrameSearchCriteria;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.util.CueUtil;
import com.imageworks.spcue.util.FrameSet;

public class FrameSearchGenerator extends CriteriaGenerator implements FrameSearchGeneratorInterface {
    private static final Logger logger = Logger.getLogger(FrameSearchGenerator.class);
    private static final Pattern PATTERN_SINGLE_FRAME = Pattern.compile("^([0-9]+)$");
    private static final Pattern PATTERN_RANGE = Pattern.compile("^([0-9]+)\\-([0-9]+)$");
    private static final Pattern PATTERN_FLOAT_RANGE = Pattern.compile("^([0-9\\.]+)\\-([0-9\\.]+)$");
    private static final int RANGE_MAX_SIZE = 1000;

    public String getSortedQuery(String query, int page, int limit) {
        StringBuilder sb = new StringBuilder(query.length() + 256);
        sb.append("SELECT * FROM (");
        sb.append(query);
        // TODO(cipriano) Remove this check. (b/117847423)
        if ("postgres".equals(getDatabaseEngine())) {
            sb.append(" ) AS getSortedQueryT WHERE row_number > ?");
        } else {
            sb.append(" ) WHERE row_number > ?");
        }
        sb.append(" AND row_number <= ?");
        values.add((page-1) * limit);
        values.add(page * limit);
        return sb.toString();
    }

    public void addFrameStates(List<FrameState> s) {
        // Convert into list of strings and call the
        // super class addPhrase
        Set<String> items = new HashSet<String>(s.size());
        for (FrameState w: s) {
            items.add(w.toString());
        }
        addPhrase("frame.str_state", items);
    }

    public void addFrameSet(String frameSet) {
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

    public void addLayers(List<LayerInterface> layers) {
        addPhrase(
                "layer.pk_layer",
                layers.stream().map(LayerInterface::getLayerId).collect(Collectors.toList()));
    }

    public void buildWhereClause(
            FrameSearchCriteria criteria, JobInterface job, LayerInterface layer) {
        addPhrase("frame.pk_frame", criteria.getIdsList());

        if (layer != null) {
            addPhrase("layer.pk_layer", layer.getLayerId());
        }
        if (job != null) {
            addPhrase("job.pk_job", job.getJobId());
        }

        addPhrase("frame.str_name", criteria.getFramesList());
        addPhrase("layer.str_name", criteria.getLayersList());
        addFrameStates(criteria.getStates().getFrameStatesList());
        if (isValid(criteria.getFrameRange())) { addFrameSet(criteria.getFrameRange()); }
        if (isValid(criteria.getMemoryRange())) { addMemoryRange(criteria.getMemoryRange()); }
        if (isValid(criteria.getDurationRange())) { addDurationRange(criteria.getDurationRange()); }
        if (criteria.getChangeDate() > 0) { addChangeDate(criteria.getChangeDate()); }
    }
}
