
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



package com.imageworks.spcue.dao.postgres;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import com.google.common.collect.Lists;
import com.google.common.collect.Sets;
import com.imageworks.spcue.dao.AbstractJdbcDao;
import org.apache.commons.lang.StringUtils;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.ExecutionSummary;
import com.imageworks.spcue.FrameStateTotals;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.LayerEntity;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.ResourceUsage;
import com.imageworks.spcue.ThreadStats;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.grpc.job.LayerType;
import com.imageworks.spcue.util.CueUtil;
import com.imageworks.spcue.util.SqlUtil;
import org.springframework.stereotype.Repository;

@Repository
public class LayerDaoJdbc extends AbstractJdbcDao implements LayerDao {

    private static final String INSERT_OUTPUT_PATH =
        "INSERT INTO " +
            "layer_output " +
        "( " +
            "pk_layer_output,"+
            "pk_layer,"+
            "pk_job,"+
            "str_filespec " +
        ") VALUES (?,?,?,?)";

    @Override
    public void insertLayerOutput(LayerInterface layer, String filespec) {
        getJdbcTemplate().update(
                INSERT_OUTPUT_PATH, UUID.randomUUID().toString(),
                layer.getLayerId(), layer.getJobId(),
                filespec);
    }

    private static final String GET_OUTPUT =
        "SELECT " +
            "str_filespec " +
        "FROM " +
            "layer_output " +
        "WHERE " +
            "pk_layer = ?";

    private static final RowMapper<String> OUTPUT_MAPPER =
        new RowMapper<String>() {
        public String mapRow(ResultSet rs, int rowNum) throws SQLException {
            return rs.getString("str_filespec");
        }
    };

    @Override
    public List<String> getLayerOutputs(LayerInterface layer) {
        return getJdbcTemplate().query(GET_OUTPUT,
                OUTPUT_MAPPER, layer.getLayerId());
    }

    private static final String IS_LAYER_DISPATCHABLE =
        "SELECT " +
            "int_waiting_count " +
        "FROM " +
            "layer_stat " +
        "WHERE " +
            "pk_layer=?";

    @Override
    public boolean isLayerDispatchable(LayerInterface l ) {
        return getJdbcTemplate().queryForObject(IS_LAYER_DISPATCHABLE,
                Integer.class, l.getLayerId()) > 0;
    }

    private static final String IS_LAYER_COMPLETE =
        "SELECT " +
            "SUM ( " +
                "int_waiting_count + " +
                "int_running_count + " +
                "int_dead_count + " +
                "int_depend_count "+
            ") " +
        "FROM " +
            "layer_stat " +
        "WHERE " +
            "pk_layer=?";

    public boolean isLayerComplete(LayerInterface l) {
        if (isLaunching(l)) {
            return false;
        }
        return getJdbcTemplate().queryForObject(IS_LAYER_COMPLETE,
                Integer.class, l.getLayerId()) == 0;
    }

    private static final String IS_LAUNCHING =
        "SELECT " +
            "str_state " +
        "FROM " +
            "job " +
        "WHERE " +
            "pk_job=?";

    @Override
    public boolean isLaunching(LayerInterface l) {
        return getJdbcTemplate().queryForObject(
                IS_LAUNCHING, String.class, l.getJobId()).equals(
                        JobState.STARTUP.toString());
    }

    private static final String IS_THREADABLE =
        "SELECT " +
            "b_threadable " +
        "FROM " +
            "layer " +
        "WHERE " +
            "pk_layer = ?";

    @Override
    public boolean isThreadable(LayerInterface l) {
        return getJdbcTemplate().queryForObject(IS_THREADABLE, Boolean.class, l.getLayerId());
    }

    /**
     * Query for layers table.  Where clauses are appended later
     */
     public static final String GET_LAYER_DETAIL =
         "SELECT " +
             "layer.*, " +
             "job.pk_show, "+
             "job.pk_facility " +
          "FROM " +
              "layer," +
              "job," +
              "show " +
          "WHERE " +
              "layer.pk_job = job.pk_job " +
          "AND " +
              "job.pk_show = show.pk_show ";

     private static final String GET_LAYER =
         "SELECT " +
             "layer.pk_layer,"+
             "layer.pk_job,"+
             "job.pk_show,"+
             "job.pk_facility, " +
             "layer.str_name "+
          "FROM " +
              "layer," +
              "job," +
              "show " +
          "WHERE " +
              "layer.pk_job = job.pk_job " +
          "AND " +
              "job.pk_show = show.pk_show ";

    /**
    * Maps a ResultSet to a LayerDetail
    */
    public static final RowMapper<LayerDetail> LAYER_DETAIL_MAPPER = new RowMapper<LayerDetail>() {
        public LayerDetail mapRow(ResultSet rs, int rowNum) throws SQLException {
            LayerDetail layer = new LayerDetail();
            layer.chunkSize = rs.getInt("int_chunk_size");
            layer.command = rs.getString("str_cmd");
            layer.dispatchOrder = rs.getInt("int_dispatch_order");
            layer.id = rs.getString("pk_layer");
            layer.jobId = rs.getString("pk_job");
            layer.showId = rs.getString("pk_show");
            layer.facilityId =rs.getString("pk_facility");
            layer.name = rs.getString("str_name");
            layer.range = rs.getString("str_range");
            layer.minimumCores = rs.getInt("int_cores_min");
            layer.minimumMemory = rs.getLong("int_mem_min");
            layer.minimumGpu = rs.getLong("int_gpu_min");
            layer.type = LayerType.valueOf(rs.getString("str_type"));
            layer.tags = Sets.newHashSet(
                    rs.getString("str_tags").replaceAll(" ", "").split("\\|"));
            layer.services.addAll(
                    Lists.newArrayList(rs.getString("str_services").split(",")));
            return layer;
        }
    };

    /**
     * Maps a ResultSet to a LayerDetail
     */
     private static final RowMapper<LayerInterface> LAYER_MAPPER = new RowMapper<LayerInterface>() {
         public LayerEntity mapRow(ResultSet rs, int rowNum) throws SQLException {
             LayerEntity layer = new LayerEntity();
             layer.id = rs.getString("pk_layer");
             layer.jobId = rs.getString("pk_job");
             layer.showId = rs.getString("pk_show");
             layer.facilityId = rs.getString("pk_facility");
             layer.name = rs.getString("str_name");
             return layer;
         }
     };


     @Override
     public LayerDetail getLayerDetail(String id) {
         return getJdbcTemplate().queryForObject(GET_LAYER_DETAIL + " AND layer.pk_layer=?",
                 LAYER_DETAIL_MAPPER, id);
     }

     @Override
     public LayerDetail getLayerDetail(LayerInterface layer) {
         return getJdbcTemplate().queryForObject(GET_LAYER_DETAIL + " AND layer.pk_layer=?",
                 LAYER_DETAIL_MAPPER, layer.getLayerId());
     }

     @Override
     public LayerDetail findLayerDetail(JobInterface job, String name) {
         return getJdbcTemplate().queryForObject(
                 GET_LAYER_DETAIL + " AND layer.pk_job=? AND layer.str_name=?",
                 LAYER_DETAIL_MAPPER, job.getJobId(), name);
     }

     @Override
     public LayerInterface findLayer(JobInterface job, String name) {
         try {
             return getJdbcTemplate().queryForObject(
                     GET_LAYER + " AND layer.pk_job=? AND layer.str_name=?",
                     LAYER_MAPPER, job.getJobId(), name);
         } catch (org.springframework.dao.EmptyResultDataAccessException e) {
             throw new EmptyResultDataAccessException("The layer " +
                     name + " was not found in " + job.getName() + e, 0);
         }
     }

     @Override
     public List<LayerDetail> getLayerDetails(JobInterface job) {
         return getJdbcTemplate().query(
                 GET_LAYER_DETAIL + " AND layer.pk_job=?",
                 LAYER_DETAIL_MAPPER, job.getJobId());
     }

     @Override
     public List<LayerInterface> getLayers(JobInterface job) {
         return getJdbcTemplate().query(
                 GET_LAYER + " AND layer.pk_job=?",
                 LAYER_MAPPER, job.getJobId());
     }

     @Override
     public LayerInterface getLayer(String id) {
         return getJdbcTemplate().queryForObject(
                 GET_LAYER + " AND layer.pk_layer=?",
                 LAYER_MAPPER, id);
     }

     private static final String INSERT_LAYER =
     "INSERT INTO " +
         "layer " +
     "("+
         "pk_layer, " +
         "pk_job, "+
         "str_name, " +
         "str_cmd, " +
         "str_range, " +
         "int_chunk_size, " +
         "int_dispatch_order, " +
         "str_tags, " +
         "str_type," +
         "int_cores_min, "+
         "int_cores_max, "+
         "b_threadable, " +
         "int_mem_min, " +
         "int_gpu_min, " +
         "str_services " +
     ") " +
     "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)";

     @Override
     public void insertLayerDetail(LayerDetail l) {
        l.id =  SqlUtil.genKeyRandom();
        getJdbcTemplate().update(INSERT_LAYER,
                l.id, l.jobId, l.name, l.command,
                l.range, l.chunkSize, l.dispatchOrder,
                StringUtils.join(l.tags," | "), l.type.toString(),
                l.minimumCores, l.maximumCores, l.isThreadable,
                l.minimumMemory, l.minimumGpu, StringUtils.join(l.services,","));
    }

    @Override
    public void updateLayerMinMemory(LayerInterface layer, long val) {
        if (val < Dispatcher.MEM_RESERVED_MIN) {
            val = Dispatcher.MEM_RESERVED_MIN;
        }
        getJdbcTemplate().update("UPDATE layer SET int_mem_min=? WHERE pk_layer=?",
                val, layer.getLayerId());
    }

    @Override
    public void updateLayerMinGpu(LayerInterface layer, long gpu) {
        getJdbcTemplate().update("UPDATE layer SET int_gpu_min=? WHERE pk_layer=?",
                gpu, layer.getLayerId());
    }

    private static final String BALANCE_MEM =
        "UPDATE " +
            "layer " +
        "SET " +
            "int_mem_min = ? " +
        "WHERE " +
            "pk_layer = ? " +
        "AND " +
            "int_mem_min > ? " +
        "AND " +
            "b_optimize = true";

    @Override
    public boolean balanceLayerMinMemory(LayerInterface layer, long frameMaxRss) {

        /**
         * Lowers the memory value on the frame when the maxrss is lower than
         * the memory requirement.
         */
        long maxrss = getJdbcTemplate().queryForObject(
                "SELECT int_max_rss FROM layer_mem WHERE pk_layer=?",
                Long.class, layer.getLayerId());

        if (maxrss < frameMaxRss) {
            maxrss = frameMaxRss;
        }
        if (maxrss < Dispatcher.MEM_RESERVED_MIN) {
            maxrss = Dispatcher.MEM_RESERVED_MIN;
        } else {
            maxrss = maxrss + CueUtil.MB256;
        }

        boolean result = getJdbcTemplate().update(BALANCE_MEM,
            maxrss, layer.getLayerId(), maxrss) == 1;
        if (result) {
            logger.info(layer.getName() + " was balanced to " + maxrss);
        }
        return result;
    }

    @Override
    public void increaseLayerMinMemory(LayerInterface layer, long val) {
        getJdbcTemplate().update("UPDATE layer SET int_mem_min=? WHERE pk_layer=? AND int_mem_min < ?",
                val, layer.getLayerId(), val);
    }

    @Override
    public void increaseLayerMinGpu(LayerInterface layer, long gpu) {
        getJdbcTemplate().update("UPDATE layer SET int_gpu_min=? WHERE pk_layer=? AND int_gpu_min < ?",
                gpu, layer.getLayerId(), gpu);
    }

    @Override
    public void updateLayerMinCores(LayerInterface layer, int val) {
        if (val < Dispatcher.CORE_POINTS_RESERVED_MIN) {
            val = Dispatcher.CORE_POINTS_RESERVED_DEFAULT;
        }
        getJdbcTemplate().update("UPDATE layer SET int_cores_min=? WHERE pk_layer=?",
                val, layer.getLayerId());
    }

    @Override
    public void updateLayerMaxCores(LayerInterface layer, int val) {
        getJdbcTemplate().update("UPDATE layer SET int_cores_max=? WHERE pk_layer=?",
                val, layer.getLayerId());
    }

    private static final String UPDATE_LAYER_MAX_RSS =
        "UPDATE " +
            "layer_mem " +
        "SET " +
            "int_max_rss = ? " +
        "WHERE " +
            "pk_layer = ?";

    @Override
    public void updateLayerMaxRSS(LayerInterface layer, long val, boolean force) {
        StringBuilder sb = new StringBuilder(UPDATE_LAYER_MAX_RSS);
        Object[] options;
        if (!force) {
            options = new Object[] { val, layer.getLayerId(), val};
            sb.append (" AND int_max_rss < ?");
        }
        else {
            options = new Object[] { val, layer.getLayerId() };
        }
        getJdbcTemplate().update(sb.toString(), options);
    }

    @Override
    public void updateLayerTags(LayerInterface layer, Set<String> tags) {
        if (tags.size() == 0) {
            throw new IllegalArgumentException(
                    "Layers must have at least one tag.");
        }
        StringBuilder sb = new StringBuilder(128);
        for (String t: tags) {
            if (t == null) { continue; }
            if (t.length() < 1) { continue; }
            sb.append(t + " | ");
        }
        sb.delete(sb.length()-3, sb.length());
        if (sb.length() == 0) {
            throw new IllegalArgumentException(
                "Invalid layer tags, cannot contain null tags or " +
                    "tags of zero length.");
        }
        getJdbcTemplate().update(
                "UPDATE layer SET str_tags=? WHERE pk_layer=?",
                sb.toString(), layer.getLayerId());
    }

    @Override
    public void appendLayerTags(LayerInterface layer, String val) {
        String appendTag = " | " + val;
        String matchTag = "%" + val + "%";

        getJdbcTemplate().update("UPDATE layer SET str_tags = str_tags || ? " +
                "WHERE pk_layer=? AND str_tags NOT LIKE ?",
                appendTag, layer.getLayerId(), matchTag);
    }

    public FrameStateTotals getFrameStateTotals(LayerInterface layer) {
        return getJdbcTemplate().queryForObject(
                "SELECT * FROM layer_stat WHERE pk_layer=?",
                new RowMapper<FrameStateTotals>() {
                    public FrameStateTotals mapRow(ResultSet rs, int rowNum) throws SQLException {
                        FrameStateTotals t = new FrameStateTotals();
                        t.dead = rs.getInt("int_dead_count");
                        t.depend = rs.getInt("int_depend_count");
                        t.eaten = rs.getInt("int_eaten_count");
                        t.running = rs.getInt("int_running_count");
                        t.succeeded = rs.getInt("int_succeeded_count");
                        t.waiting = rs.getInt("int_waiting_count");
                        t.total = rs.getInt("int_total_count");
                        return t;
                    }
                },layer.getLayerId());
    }

    private static final String GET_EXECUTION_SUMMARY =
        "SELECT " +
            "layer_usage.int_core_time_success,"+
            "layer_usage.int_core_time_fail," +
            "layer_usage.int_clock_time_success," +
            "layer_mem.int_max_rss " +
        "FROM " +
            "layer," +
            "layer_usage, "+
            "layer_mem " +
        "WHERE " +
            "layer.pk_layer = layer_usage.pk_layer "+
        "AND " +
            "layer.pk_layer = layer_mem.pk_layer " +
        "AND " +
            "layer.pk_layer = ?";

    @Override
    public ExecutionSummary getExecutionSummary(LayerInterface layer) {
        return getJdbcTemplate().queryForObject(
                GET_EXECUTION_SUMMARY,
                new RowMapper<ExecutionSummary>() {
                    public ExecutionSummary mapRow(ResultSet rs, int rowNum) throws SQLException {
                        ExecutionSummary e = new ExecutionSummary();
                        e.coreTimeSuccess = rs.getLong("int_core_time_success");
                        e.coreTimeFail = rs.getLong("int_core_time_fail");
                        e.coreTime = e.coreTimeSuccess + e.coreTimeFail;
                        e.highMemoryKb = rs.getLong("int_max_rss");
                        return e;
                    }
                }, layer.getLayerId());
    }

    private static final String INSERT_LAYER_ENV =
        "INSERT INTO " +
            "layer_env " +
        "(" +
            "pk_layer_env, pk_layer, pk_job, str_key, str_value " +
        ") " +
        "VALUES (?,?,?,?,?)";

    @Override
    public void insertLayerEnvironment(LayerInterface layer, Map<String,String> env) {
        for (Map.Entry<String,String> e: env.entrySet()) {
            String pk = SqlUtil.genKeyRandom();
            getJdbcTemplate().update(INSERT_LAYER_ENV,
                    pk, layer.getLayerId(), layer.getJobId(), e.getKey(), e.getValue());
        }
    }

    @Override
    public void insertLayerEnvironment(LayerInterface layer, String key, String value) {
        String pk = SqlUtil.genKeyRandom();
        getJdbcTemplate().update(INSERT_LAYER_ENV,
                pk, layer.getLayerId(), layer.getJobId(), key, value);
    }

    @Override
    public Map<String,String> getLayerEnvironment(LayerInterface layer) {
        Map<String,String> result = new HashMap<String,String>();
        List<Map<String, Object>> _result = getJdbcTemplate().queryForList(
                "SELECT str_key, str_value FROM layer_env WHERE pk_layer=?", layer.getLayerId());

        for (Map<String,Object> o: _result) {
            result.put((String) o.get("str_key"), (String) o.get("str_value"));
        }
        return result;
    }

    private static final String FIND_PAST_MAX_RSS =
        "SELECT "+
            "layer_mem.int_max_rss " +
        "FROM " +
            "layer, " +
            "layer_mem, "+
            "layer_stat "+
       "WHERE " +
           "layer.pk_layer = layer_stat.pk_layer " +
       "AND " +
           "layer.pk_layer = layer_mem.pk_layer " +
       "AND " +
           "layer.pk_job = ? " +
       "AND " +
           "layer.str_name = ? " +
       "AND " +
           "layer_stat.int_succeeded_count >= ceil(layer_stat.int_total_count * .5) ";

    @Override
    public long findPastMaxRSS(JobInterface job, String name) {
        try {
            long maxRss = getJdbcTemplate().queryForObject(FIND_PAST_MAX_RSS,
                    Long.class, job.getJobId(), name);
            if (maxRss >= Dispatcher.MEM_RESERVED_MIN) {
                return maxRss;
            }
            else {
                return Dispatcher.MEM_RESERVED_MIN;
            }
        } catch (EmptyResultDataAccessException e) {
            // Actually want to return 0 here, which means
            // there is no past history.
            return 0;
        }
    }

    @Override
    public void updateTags(JobInterface job, String tags, LayerType type) {
        getJdbcTemplate().update(
                "UPDATE layer SET str_tags=? WHERE pk_job=? AND str_type=?",
                tags, job.getJobId(), type.toString());
    }

    @Override
    public void updateMinMemory(JobInterface job, long mem, LayerType type) {
        if (mem < Dispatcher.MEM_RESERVED_MIN) {
            mem = Dispatcher.MEM_RESERVED_MIN;
        }
        getJdbcTemplate().update(
                "UPDATE layer SET int_mem_min=? WHERE pk_job=? AND str_type=?",
                mem, job.getJobId(), type.toString());
    }

    @Override
    public void updateMinGpu(JobInterface job, long gpu, LayerType type) {
        getJdbcTemplate().update(
                "UPDATE layer SET int_gpu_min=? WHERE pk_job=? AND str_type=?",
                gpu, job.getJobId(), type.toString());
    }

    @Override
    public void updateMinCores(JobInterface job, int cores, LayerType type) {
        getJdbcTemplate().update(
                "UPDATE layer SET int_cores_min=? WHERE pk_job=? AND str_type=?",
                cores, job.getJobId(), type.toString());
    }

    @Override
    public void updateThreadable(LayerInterface layer, boolean threadable) {
        getJdbcTemplate().update(
                "UPDATE layer SET b_threadable=? WHERE pk_layer=?",
                threadable, layer.getLayerId());
    }

    @Override
    public void enableMemoryOptimizer(LayerInterface layer, boolean value) {
        getJdbcTemplate().update(
                "UPDATE layer SET b_optimize=? WHERE pk_layer=?",
                value, layer.getLayerId());
    }

    private static final String IS_OPTIMIZABLE =
        "SELECT " +
            "COUNT(1) "+
        "FROM " +
            "layer, " +
            "layer_stat, " +
            "layer_usage " +
        "WHERE " +
            "layer.pk_layer = layer_stat.pk_layer " +
        "AND " +
            "layer.pk_layer = layer_usage.pk_layer " +
        "AND " +
            "layer.pk_layer = ? " +
        "AND " +
            "layer.int_cores_min = 100 " +
        "AND " +
            "str_tags LIKE '%general%' " +
        "AND " +
            "str_tags NOT LIKE '%util%' " +
        "AND " +
            "layer_stat.int_succeeded_count >= ? " +
        "AND " +
            "(layer_usage.int_core_time_success / layer_stat.int_succeeded_count) <= ?";

    @Override
    public boolean isOptimizable(LayerInterface l, int succeeded, float avg) {
        if (succeeded < 1) {
            throw new IllegalArgumentException("Succeeded frames option " +
                    "must be greater than zero");
        }
        return getJdbcTemplate().queryForObject(IS_OPTIMIZABLE,
                Integer.class, l.getLayerId(), succeeded, avg) > 0;
    }

    private static final String THREAD_STATS =
        "SELECT " +
            "avg(interval_to_seconds(ts_stopped - ts_started)) AS avg, " +
            "int_cores " +
        "FROM " +
            "frame " +
        "WHERE " +
            "frame.pk_layer = ? " +
        "AND " +
            "frame.int_checkpoint_count = 0 " +
        "AND " +
            "int_cores > 0 " +
        "GROUP BY " +
            "int_cores " +
        "ORDER BY " +
            "int_cores DESC ";

    @Override
    public List<ThreadStats> getThreadStats(LayerInterface layer) {

        return getJdbcTemplate().query(THREAD_STATS,
                new RowMapper<ThreadStats>() {
            public ThreadStats mapRow(ResultSet rs, int rowNum) throws SQLException {
                ThreadStats s = new ThreadStats();
                s.setThreads(rs.getInt("int_cores") / 100);
                s.setAvgFrameTime(rs.getInt("avg"));
                return s;
            }
        }, layer.getLayerId());
    }

    @Override
    public void updateUsage(LayerInterface layer, ResourceUsage usage, int exitStatus) {

        if (exitStatus == 0) {

            getJdbcTemplate().update(
                    "UPDATE " +
                        "layer_usage " +
                    "SET " +
                        "int_core_time_success = int_core_time_success + ?," +
                        "int_clock_time_success = int_clock_time_success + ?,"+
                        "int_frame_success_count = int_frame_success_count + 1 " +
                    "WHERE " +
                        "pk_layer = ? ",
                        usage.getCoreTimeSeconds(),
                        usage.getClockTimeSeconds(),
                        layer.getLayerId());

            getJdbcTemplate().update(
                    "UPDATE " +
                        "layer_usage " +
                    "SET " +
                        "int_clock_time_high = ? " +
                    "WHERE " +
                        "pk_layer = ? " +
                    "AND " +
                        "int_clock_time_high < ?",
                    usage.getClockTimeSeconds(),
                    layer.getLayerId(),
                    usage.getClockTimeSeconds());

            getJdbcTemplate().update(
                    "UPDATE " +
                        "layer_usage " +
                    "SET " +
                        "int_clock_time_low = ? " +
                    "WHERE " +
                        "pk_layer = ? " +
                    "AND " +
                        "(? < int_clock_time_low OR int_clock_time_low = 0)",
                    usage.getClockTimeSeconds(),
                    layer.getLayerId(),
                    usage.getClockTimeSeconds());
        }
        else {
            getJdbcTemplate().update(
                    "UPDATE " +
                        "layer_usage " +
                    "SET " +
                        "int_core_time_fail = int_core_time_fail + ?," +
                        "int_clock_time_fail = int_clock_time_fail + ?,"+
                        "int_frame_fail_count = int_frame_fail_count + 1 " +
                    "WHERE " +
                        "pk_layer = ? ",
                        usage.getCoreTimeSeconds(),
                        usage.getClockTimeSeconds(),
                        layer.getLayerId());
        }
    }
}

