
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
import java.util.ArrayList;
import java.util.EnumSet;
import java.util.List;

import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.Frame;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.Job;
import com.imageworks.spcue.Layer;
import com.imageworks.spcue.FrameEntity;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.LightweightDependency;
import com.imageworks.spcue.ResourceUsage;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.CueIce.CheckpointState;
import com.imageworks.spcue.CueIce.DependType;
import com.imageworks.spcue.CueIce.FrameState;
import com.imageworks.spcue.CueIce.FrameExitStatusSkipRetry;
import com.imageworks.spcue.CueIce.JobState;
import com.imageworks.spcue.CueIce.LayerType;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.criteria.FrameSearch;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.FrameReservationException;
import com.imageworks.spcue.util.CueUtil;
import com.imageworks.spcue.util.SqlUtil;
import com.imageworks.spcue.util.FrameSet;

public class FrameDaoJdbc extends JdbcDaoSupport  implements FrameDao {

    private static final String UPDATE_FRAME_STOPPED_NORSS =
        "UPDATE "+
            "frame "+
        "SET " +
            "str_state=?, "+
            "int_exit_status = ?, " +
            "ts_stopped = systimestamp, " +
            "ts_updated = systimestamp,  " +
            "int_version = int_version + 1, " +
            "int_total_past_core_time = int_total_past_core_time + " +
                "round(INTERVAL_TO_SECONDS(systimestamp - ts_started) * int_cores / 100) " +
        "WHERE " +
            "frame.pk_frame = ? " +
        "AND " +
            "frame.str_state = ? " +
        "AND " +
            "frame.int_version = ? ";

    @Override
    public boolean updateFrameStopped(Frame frame, FrameState state,
            int exitStatus) {
       return getJdbcTemplate().update(UPDATE_FRAME_STOPPED_NORSS,
                state.toString(), exitStatus, frame.getFrameId(),
                FrameState.Running.toString(), frame.getVersion()) == 1;
    }

    private static final String UPDATE_FRAME_STOPPED =
        "UPDATE "+
            "frame "+
        "SET " +
            "str_state=?, "+
            "int_exit_status = ?, " +
            "ts_stopped = systimestamp + interval '1' second, " +
            "ts_updated = systimestamp, " +
            "int_mem_max_used = ?, " +
            "int_version = int_version + 1, " +
            "int_total_past_core_time = int_total_past_core_time + " +
                "round(INTERVAL_TO_SECONDS(systimestamp + interval '1' second - ts_started) * int_cores / 100) " +
        "WHERE " +
            "frame.pk_frame = ? " +
        "AND " +
            "frame.str_state = ? " +
         "AND " +
            "frame.int_version = ? ";

    @Override
    public boolean updateFrameStopped(Frame frame, FrameState state,
            int exitStatus, long maxRss) {


       return getJdbcTemplate().update(UPDATE_FRAME_STOPPED,
                state.toString(), exitStatus, maxRss,
                frame.getFrameId(), FrameState.Running.toString(),
                frame.getVersion()) == 1;
    }

    private static final String UPDATE_FRAME_CLEARED =
        "UPDATE "+
            "frame "+
        "SET " +
            "str_state = ?, "+
            "int_exit_status = ?, " +
            "ts_stopped = systimestamp, " +
            "ts_updated = systimestamp, " +
            "int_version = int_version + 1 " +
        "WHERE " +
            "frame.pk_frame = ? " +
        "AND " +
            "frame.pk_frame NOT IN " +
                "(SELECT proc.pk_frame FROM " +
                    "proc WHERE proc.pk_frame=?)";

    @Override
    public boolean updateFrameCleared(Frame frame) {

        int result =  getJdbcTemplate().update(
               UPDATE_FRAME_CLEARED,
               FrameState.Waiting.toString(),
               Dispatcher.EXIT_STATUS_FRAME_CLEARED,
               frame.getFrameId(),
               frame.getFrameId());

        return result > 0;
    }

    private static final String UPDATE_FRAME_STARTED =
        "UPDATE "+
            "frame "+
        "SET " +
            "str_state = ?,"+
            "str_host=?, " +
            "int_cores=?, "+
            "int_mem_reserved = ?, " +
            "int_gpu_reserved = ?, " +
            "ts_updated = systimestamp,"+
            "ts_started = systimestamp,"+
            "ts_stopped = null, "+
            "int_version = int_version + 1 "+
        "WHERE " +
            "pk_frame = ? " +
        "AND " +
            "str_state = ? " +
        "AND " +
            "int_version = ?";

    private static final String UPDATE_FRAME_RETRIES =
        "UPDATE " +
            "frame " +
        "SET " +
            "int_retries = int_retries + 1 " +
        "WHERE " +
            "pk_frame = ? " +
        "AND " +
            "int_exit_status NOT IN (?,?,?) ";

    @Override
    public void updateFrameStarted(VirtualProc proc, Frame frame) {

        lockFrameForUpdate(frame, FrameState.Waiting);

        int result = getJdbcTemplate().update(UPDATE_FRAME_STARTED,
                FrameState.Running.toString(), proc.hostName, proc.coresReserved,
                proc.memoryReserved, proc.gpuReserved, frame.getFrameId(),
                FrameState.Waiting.toString(), frame.getVersion());

        if (result == 0) {
            String error_msg = "the frame " +
                frame + " was updated by another thread.";
            throw new FrameReservationException(error_msg);
        }

        /*
         * Frames that were killed via nimby or hardware errors not attributed to
         * the software do not increment the retry counter.
         */
        getJdbcTemplate().update(UPDATE_FRAME_RETRIES,
                frame.getFrameId(), -1, FrameExitStatusSkipRetry.value,
                Dispatcher.EXIT_STATUS_FRAME_CLEARED);
    }

    private static final String UPDATE_FRAME_FIXED =
        "UPDATE "+
            "frame "+
        "SET " +
            "str_state = ?,"+
            "str_host=?, " +
            "int_cores=?, "+
            "int_mem_reserved = ?, " +
            "int_gpu_reserved = ?, " +
            "ts_updated = systimestamp,"+
            "ts_started = systimestamp,"+
            "ts_stopped = null, "+
            "int_version = int_version + 1 " +
        "WHERE " +
            "pk_frame = ? " +
        "AND " +
            "str_state = 'Running'";

    @Override
    public boolean updateFrameFixed(VirtualProc proc, Frame frame) {
        return getJdbcTemplate().update(UPDATE_FRAME_FIXED,
                FrameState.Running.toString(), proc.hostName, proc.coresReserved,
                proc.memoryReserved, proc.gpuReserved, frame.getFrameId()) == 1;
    }

    @Override
    public DispatchFrame getDispatchFrame(String uuid) {
        return getJdbcTemplate().queryForObject(
                GET_DISPATCH_FRAME, DISPATCH_FRAME_MAPPER, uuid);
    }

    static final RowMapper<DispatchFrame> DISPATCH_FRAME_MAPPER = new RowMapper<DispatchFrame>() {
        public DispatchFrame mapRow(ResultSet rs, int rowNum) throws SQLException {
            DispatchFrame frame = new DispatchFrame();
            frame.id = rs.getString("pk_frame");
            frame.name = rs.getString("frame_name");
            frame.layerId = rs.getString("pk_layer");
            frame.jobId = rs.getString("pk_job");
            frame.showId = rs.getString("pk_show");
            frame.facilityId = rs.getString("pk_facility");
            frame.retries = rs.getInt("int_retries");
            frame.state = FrameState.valueOf(rs.getString("frame_state"));
            frame.command = rs.getString("str_cmd");
            frame.jobName = rs.getString("job_name");
            frame.layerName = rs.getString("layer_name");
            frame.chunkSize = rs.getInt("int_chunk_size");
            frame.range = rs.getString("str_range");
            frame.logDir = rs.getString("str_log_dir");
            frame.shot = rs.getString("str_shot");
            frame.show = rs.getString("show_name");
            frame.owner = rs.getString("str_user");
            frame.uid = rs.getInt("int_uid");
            frame.state = FrameState.valueOf(rs.getString("frame_state"));
            frame.minCores = rs.getInt("int_cores_min");
            frame.maxCores = rs.getInt("int_cores_max");
            frame.threadable = rs.getBoolean("b_threadable");
            frame.minMemory = rs.getLong("int_mem_min");
            frame.minGpu = rs.getLong("int_gpu_min");
            frame.version = rs.getInt("int_version");
            frame.services = rs.getString("str_services");
            return frame;
        }
    };

    private static final String GET_DISPATCH_FRAME =
        "SELECT " +
            "show.str_name AS show_name, "+
            "job.str_name AS job_name, " +
            "job.pk_job,"+
            "job.pk_show,"+
            "job.pk_facility,"+
            "job.str_name,"+
            "job.str_shot,"+
            "job.str_user,"+
            "job.int_uid,"+
            "job.str_log_dir,"+
            "frame.str_name AS frame_name, "+
            "frame.str_state AS frame_state, "+
            "frame.pk_frame, "+
            "frame.pk_layer, "+
            "frame.int_retries, "+
            "frame.int_version, " +
            "layer.str_name AS layer_name, " +
            "layer.str_type AS layer_type, "+
            "layer.str_cmd, "+
            "layer.int_cores_min,"+
            "layer.int_cores_max,"+
            "layer.b_threadable,"+
            "layer.int_mem_min, "+
            "layer.int_gpu_min, "+
            "layer.str_range, "+
            "layer.int_chunk_size, " +
            "layer.str_services " +
        "FROM " +
            "layer, " +
            "job, "+
            "show, " +
            "frame LEFT JOIN proc ON (proc.pk_frame = frame.pk_frame) " +
        "WHERE " +
            "job.pk_show = show.pk_show "+
        "AND " +
            "frame.pk_job = job.pk_job " +
        "AND " +
            "frame.pk_layer = layer.pk_layer " +
        "AND " +
            "frame.pk_frame = ?";

    private static final String GET_FRAME_DETAIL =
        "SELECT " +
            "frame.*, " +
            "job.pk_facility," +
            "job.pk_show " +
        "FROM " +
            "frame," +
            "layer," +
            "job," +
            "show " +
        "WHERE "+
            "frame.pk_job = job.pk_job " +
        "AND " +
            "frame.pk_layer = layer.pk_layer " +
         "AND "+
             "job.pk_show = show.pk_show ";

    private static final String GET_MINIMAL_FRAME =
        "SELECT " +
            "frame.pk_frame," +
            "frame.str_name, " +
            "frame.pk_job, " +
            "frame.pk_layer, "+
            "frame.str_state, " +
            "frame.int_version, "+
            "job.pk_show, " +
            "job.pk_facility "+
        "FROM " +
            "frame," +
            "layer," +
            "job," +
            "show " +
        "WHERE "+
            "frame.pk_job = job.pk_job " +
        "AND " +
            "frame.pk_layer = layer.pk_layer " +
        "AND " +
            "job.pk_show = show.pk_show ";

    private static final RowMapper<Frame> FRAME_MAPPER =
        new RowMapper<Frame>() {
        public FrameEntity mapRow(ResultSet rs,
                int rowNum) throws SQLException {
            FrameEntity frame = new FrameEntity();
            frame.id = rs.getString("pk_frame");
            frame.name = rs.getString("str_name");
            frame.jobId = rs.getString("pk_job");
            frame.layerId = rs.getString("pk_layer");
            frame.showId = rs.getString("pk_show");
            frame.facilityId = rs.getString("pk_facility");
            frame.version = rs.getInt("int_version");
            return frame;
        }
    };

    private static final RowMapper<FrameDetail> FRAME_DETAIL_MAPPER = new RowMapper<FrameDetail>() {
        public FrameDetail mapRow(ResultSet rs, int rowNum) throws SQLException {
            FrameDetail frame = new FrameDetail();
            frame.id = rs.getString("pk_frame");
            frame.dependCount = rs.getInt("int_depend_count");
            frame.exitStatus = rs.getInt("int_exit_status");
            frame.jobId = rs.getString("pk_job");
            frame.layerId = rs.getString("pk_layer");
            frame.showId = rs.getString("pk_show");
            frame.maxRss = rs.getInt("int_mem_max_used");
            frame.name = rs.getString("str_name");
            frame.number = rs.getInt("int_number");
            frame.dispatchOrder = rs.getInt("int_dispatch_order");
            frame.retryCount = rs.getInt("int_retries");
            frame.dateStarted = rs.getTimestamp("ts_started");
            frame.dateStopped = rs.getTimestamp("ts_stopped");
            frame.dateUpdated = rs.getTimestamp("ts_updated");
            frame.version = rs.getInt("int_version");

            if (rs.getString("str_host") != null) {
                frame.lastResource = String.format("%s/%d",rs.getString("str_host"),rs.getInt("int_cores"));
            }
            else {
                frame.lastResource = "";
            }
            frame.state = FrameState.valueOf(rs.getString("str_state"));

            return frame;
        }
    };

    public static final String FIND_ORPHANED_FRAMES =
        "SELECT " +
            "frame.pk_frame, " +
            "frame.pk_layer, " +
            "frame.str_name, " +
            "frame.int_version, " +
            "job.pk_job, " +
            "job.pk_show, " +
            "job.pk_facility " +
        "FROM " +
            "frame, " +
            "job " +
        "WHERE " +
            "job.pk_job = frame.pk_job " +
        "AND " +
            "frame.str_state='Running' " +
        "AND " +
            "job.str_state = 'Pending' " +
        "AND " +
            "(SELECT COUNT(1) FROM proc WHERE proc.pk_frame = frame.pk_frame) = 0 " +
        "AND " +
            "systimestamp - frame.ts_updated > interval '300' second";

    @Override
    public List<Frame> getOrphanedFrames() {
        return getJdbcTemplate().query(FIND_ORPHANED_FRAMES,
                FRAME_MAPPER);
    }

    private static final String IS_ORPHAN =
        "SELECT " +
            "COUNT(1) " +
        "FROM " +
            "frame " +
        "WHERE " +
            "frame.pk_frame = ? " +
        "AND " +
            "frame.str_state = 'Running' " +
        "AND " +
            "(SELECT COUNT(1) FROM proc WHERE proc.pk_frame = frame.pk_frame) = 0 " +
        "AND " +
            "systimestamp - frame.ts_updated > interval '300' second";

    @Override
    public boolean isOrphan(Frame frame) {
        return getJdbcTemplate().queryForObject(IS_ORPHAN, Integer.class,
                frame.getFrameId()) == 1;
    }

    private static final String INSERT_FRAME =
        "INSERT INTO " +
        "frame " +
        "("+
            "pk_frame, " +
            "pk_layer, " +
            "pk_job, " +
            "str_name, " +
            "str_state, " +
            "int_number, " +
            "int_dispatch_order, " +
            "int_layer_order, "+
            "ts_updated "+
        ") " +
        "VALUES (?,?,?,?,?,?,?,?,systimestamp)";

    @Override
    public void insertFrames(LayerDetail layer, List<Integer> frames) {

        int count = 0;
        for (int frame: frames) {
            getJdbcTemplate().update(INSERT_FRAME,
                    SqlUtil.genKeyRandom(),
                    layer.getLayerId(),
                    layer.getJobId(),
                    CueUtil.buildFrameName(layer, frame),
                    FrameState.Setup.toString(),
                    frame,
                    count,
                    layer.dispatchOrder);
            count++;
        }
    }

    @Override
    public List<Frame> getDependentFrames(LightweightDependency depend) {

        /*
         * Compound depends are handled in the DependManager.
         */

        String key = null;
        StringBuilder sb = new StringBuilder(4096);
        sb.append(GET_MINIMAL_FRAME);
        sb.append(" AND frame.int_depend_count > 0 ");

        if (EnumSet.of(
                DependType.JobOnJob,
                DependType.JobOnLayer,
                DependType.JobOnFrame).contains(depend.type)) {
            sb.append("AND job.pk_job = ?");
            key = depend.dependErJobId;
        }
        else if (EnumSet.of(
                DependType.LayerOnFrame,
                DependType.LayerOnLayer,
                DependType.LayerOnJob).contains(depend.type)) {
            sb.append("AND layer.pk_layer = ?");
            key = depend.dependErLayerId;
        }
        else if (EnumSet.of(
                DependType.FrameOnJob,
                DependType.FrameOnLayer,
                DependType.FrameOnFrame).contains(depend.type)) {
            sb.append("AND frame.pk_frame = ?");
            key = depend.dependErFrameId;
        }
        else {
            return new ArrayList<Frame>(1);
        }

        return getJdbcTemplate().query(
                sb.toString(), FRAME_MAPPER,
                new Object[] { key });
    }

    @Override
    public Frame findFrame(Layer layer, int number) {
        return getJdbcTemplate().queryForObject(
                GET_MINIMAL_FRAME + " AND frame.pk_layer=? AND int_number=?",
                FRAME_MAPPER, layer.getLayerId(), number);
    }

    @Override
    public FrameDetail getFrameDetail(Frame frame) {
        return getJdbcTemplate().queryForObject(
                GET_FRAME_DETAIL + " AND pk_frame=?",
                FRAME_DETAIL_MAPPER, frame.getFrameId());
    }

    @Override
    public FrameDetail getFrameDetail(String id) {
        return getJdbcTemplate().queryForObject(
                GET_FRAME_DETAIL + " AND pk_frame=?",
                FRAME_DETAIL_MAPPER, id);
    }

    @Override
    public FrameDetail findFrameDetail(Job job, String name) {
        //Uses C_FRAME_STR_NAME_UNQ
        return getJdbcTemplate().queryForObject(
                GET_FRAME_DETAIL + " AND frame.str_name=? AND frame.pk_job=?",
                FRAME_DETAIL_MAPPER, name, job.getJobId());
    }

    @Override
    public List<FrameDetail> findFrameDetails(FrameSearch r) {
        return getJdbcTemplate().query(r.getQuery(GET_FRAME_DETAIL),
                FRAME_DETAIL_MAPPER, r.getValuesArray());
    }

    @Override
    public List<Frame> findFrames(FrameSearch r) {
        return getJdbcTemplate().query(r.getQuery(GET_MINIMAL_FRAME),
                FRAME_MAPPER, r.getValuesArray());
    }

    private static final String FIND_LONGEST_FRAME =
        "SELECT " +
            "pk_frame " +
        "FROM (" +
        "SELECT " +
            "pk_frame,"+
            "ts_stopped - ts_started AS duration " +
        "FROM " +
            "frame, " +
            "layer " +
        "WHERE " +
            "frame.pk_layer = layer.pk_layer " +
        "AND " +
            "frame.pk_job = ? "+
        "AND " +
            "str_state=? "+
        "AND " +
            "layer.str_type=? " +
        "ORDER BY "+
            "duration DESC "+
        ") WHERE ROWNUM = 1";

    @Override
    public FrameDetail findLongestFrame(Job job) {
        String pk_frame = getJdbcTemplate().queryForObject(
                FIND_LONGEST_FRAME, String.class, job.getJobId(),
                FrameState.Succeeded.toString(), LayerType.Render.toString());
        return getFrameDetail(pk_frame);
    }

    private static final String FIND_SHORTEST_FRAME =
        "SELECT " +
            "pk_frame " +
        "FROM (" +
        "SELECT " +
            "pk_frame,"+
            "ts_stopped - ts_started AS duration " +
        "FROM " +
            "frame, " +
            "layer " +
        "WHERE " +
            "frame.pk_layer = layer.pk_layer " +
        "AND " +
            "frame.pk_job = ? "+
        "AND " +
            "frame.str_state=? "+
        "AND " +
            "layer.str_type=? " +
        "ORDER BY "+
            "duration ASC "+
        ") WHERE ROWNUM = 1";

    @Override
    public FrameDetail findShortestFrame(Job job) {
        String pk_frame = getJdbcTemplate().queryForObject(
                FIND_SHORTEST_FRAME, String.class, job.getJobId(),
                FrameState.Succeeded.toString(),LayerType.Render.toString());
        return getFrameDetail(pk_frame);
    }

    @Override
    public Frame getFrame(String id) {
        return getJdbcTemplate().queryForObject(
                GET_MINIMAL_FRAME + " AND frame.pk_frame=?",
                FRAME_MAPPER, id);
    }

    @Override
    public Frame findFrame(Job job, String name) {
        //Uses C_FRAME_STR_NAME_UNQ
        return getJdbcTemplate().queryForObject(
                GET_MINIMAL_FRAME + " AND frame.str_name=? AND frame.pk_job=?",
                FRAME_MAPPER, name, job.getJobId());
    }

    @Override
    public void checkRetries(Frame frame) {
        int max_retries = getJdbcTemplate().queryForObject(
                "SELECT int_max_retries FROM job WHERE pk_job=?", Integer.class,
                frame.getJobId());

        if (getJdbcTemplate().queryForObject(
                "SELECT int_retries FROM frame WHERE pk_frame=?", Integer.class,
                frame.getFrameId()) >= max_retries) {
            getJdbcTemplate().update(
                    "UPDATE frame SET str_state=? WHERE pk_frame=?",
                    FrameState.Dead.toString(), frame.getFrameId());
        }
    }

    public static final String GET_FRAME_ID =
        "SELECT " +
            "frame.pk_frame "+
        "FROM " +
            "frame,"+
            "layer,"+
            "job "+
        "WHERE " +
            "frame.pk_layer = layer.pk_layer " +
        "AND " +
            "frame.pk_job = job.pk_job ";


    private static final String UPDATE_FRAME_STATE =
        "UPDATE " +
            "frame "+
        "SET " +
            "str_state=?, " +
            "ts_updated = systimestamp, " +
            "int_version = int_version + 1 " +
        "WHERE " +
            "pk_frame = ? " +
        "AND " +
            "int_version = ? ";

    @Override
    public boolean updateFrameState(Frame frame, FrameState state) {
        if (getJdbcTemplate().update(UPDATE_FRAME_STATE,
                state.toString(),
                frame.getFrameId(),
                frame.getVersion()) == 1) {
            logger.info("The frame " + frame + " state changed to " +
                    state.toString());
            return true;
        }
        logger.info("Failed to change the frame " + frame + " state to " +
                state.toString());
        return false;
    }

    private static final String MARK_AS_WAITING =
        "UPDATE " +
            "frame "+
        "SET " +
            "str_state=?, " +
            "ts_updated = systimestamp, " +
            "int_depend_count = 0, " +
            "int_version = int_version + 1 " +
        "WHERE " +
            "pk_frame = ? " +
        "AND " +
            "int_version = ? " +
        "AND " +
            "str_state = ? ";

    @Override
    public void markFrameAsWaiting(Frame frame) {
        getJdbcTemplate().update(
                MARK_AS_WAITING,
                FrameState.Waiting.toString(),
                frame.getFrameId(),
                frame.getVersion(),
                FrameState.Depend.toString());
    }

    private static final String MARK_AS_DEPEND =
        "UPDATE " +
            "frame "+
        "SET " +
            "str_state=?, " +
            "int_depend_count = ?, "+
            "ts_updated = systimestamp, " +
            "int_version = int_version + 1 " +
        "WHERE " +
            "pk_frame = ? " +
        "AND " +
            "int_version = ? " +
        "AND " +
            "str_state = ? ";

    private static final String GET_FRAME_DEPEND_COUNT =
        "SELECT " +
            "COUNT(1) " +
        "FROM " +
            "depend " +
        "WHERE " +
            " ( " +
               "(pk_job_depend_er = ? AND str_type LIKE 'JobOn%') " +
            "OR " +
                "pk_layer_depend_er=? " +
            "OR " +
                "pk_frame_depend_er=? " +
            " ) " +
        "AND " +
            "depend.b_active = 1 " +
        "AND " +
            "depend.b_composite = 0 ";

    public void markFrameAsDepend(Frame frame) {
        // We need to full depend count in this case to reset the
        // frames's depend count accurately.
        int depend_count = getJdbcTemplate().queryForObject(
                GET_FRAME_DEPEND_COUNT, Integer.class,
                frame.getJobId(),frame.getLayerId(),frame.getFrameId());

        if (depend_count > 0) {
            getJdbcTemplate().update(
                    MARK_AS_DEPEND,
                    FrameState.Depend.toString(),
                    depend_count,
                    frame.getFrameId(),
                    frame.getVersion(),
                    FrameState.Waiting.toString());
        }
    }

    private static final String FIND_HIGHEST_MEM_FRAME =
        "SELECT " +
            "pk_frame " +
        "FROM (" +
        "SELECT " +
            "pk_frame " +
        "FROM " +
            "frame " +
        "WHERE " +
            "pk_job = ? "+
        "AND " +
            "str_state=? "+
        "ORDER BY "+
            "int_mem_max_used DESC "+
        ") WHERE ROWNUM = 1";

    @Override
    public FrameDetail findHighestMemoryFrame(Job job) {
        String pk_frame = getJdbcTemplate().queryForObject(
                FIND_HIGHEST_MEM_FRAME, String.class, job.getJobId(),
                FrameState.Succeeded.toString());
        return getFrameDetail(pk_frame);
    }

    private static final String FIND_LOWEST_MEM_FRAME =
        "SELECT " +
            "pk_frame " +
        "FROM (" +
        "SELECT " +
            "pk_frame " +
        "FROM " +
            "frame " +
        "WHERE " +
            "pk_job = ? "+
        "AND " +
            "str_state=? "+
        "ORDER BY "+
            "int_mem_max_used ASC "+
        ") WHERE ROWNUM = 1";

    @Override
    public FrameDetail findLowestMemoryFrame(Job job) {
        String pk_frame = getJdbcTemplate().queryForObject(
                FIND_LOWEST_MEM_FRAME, String.class, job.getJobId(),
                FrameState.Succeeded.toString());
        return getFrameDetail(pk_frame);
    }

    @Override
    public void reorderFramesFirst(Layer layer, FrameSet frameSet) {
        int start;
        int size = frameSet.size();
        int min = getJdbcTemplate().queryForObject(
                "SELECT MIN(int_dispatch_order) FROM frame WHERE pk_layer=?", Integer.class,
                layer.getLayerId());

        start = min - size;
        for (int frameIdx=0; frameIdx < size; frameIdx++) {
            getJdbcTemplate().update(
                    "UPDATE frame SET int_dispatch_order=? WHERE str_name=? AND pk_job=?",
                    start, CueUtil.buildFrameName(layer, frameSet.get(frameIdx)), layer.getJobId());

            logger.info("reordering " + CueUtil.buildFrameName(layer, frameSet.get(frameIdx)) + " to " +
                    start);
            start++;
        }
    }

    @Override
    public void reorderFramesLast(Layer layer, FrameSet frameSet) {
        int start;
        int size = frameSet.size();
        List<Object[]> frames = new ArrayList<Object[]>(size);
        int max = getJdbcTemplate().queryForObject(
                "SELECT MAX(int_dispatch_order) FROM frame WHERE pk_layer=?", Integer.class,
                layer.getLayerId());

        start = max + 1;
        for (int i=0; i <= size; i++) {
            frames.add(new Object[] { start + i, CueUtil.buildFrameName(layer, i), layer.getJobId() });
        }

        if (frames.size() > 0) {
            getJdbcTemplate().batchUpdate(
                    "UPDATE frame SET int_dispatch_order=? WHERE str_name=? AND pk_job=?", frames);
        }
    }

    @Override
    public void reorderLayerReverse(Layer layer, FrameSet frameSet) {

        int size = frameSet.size();
        List<Object[]> frames = new ArrayList<Object[]>(size);

        for (int i=0; i< size; i++) {
            if (i >= size - i -1) { break; }
            try {
                int a = getJdbcTemplate().queryForObject(
                        "SELECT int_dispatch_order FROM frame WHERE str_name=? AND pk_job=? AND pk_layer=?", Integer.class,
                        CueUtil.buildFrameName(layer,frameSet.get(i)), layer.getJobId(), layer.getLayerId());

                int b = getJdbcTemplate().queryForObject(
                        "SELECT int_dispatch_order FROM frame WHERE str_name=? AND pk_job=? AND pk_layer=?", Integer.class,
                        CueUtil.buildFrameName(layer,frameSet.get(size-i-1)), layer.getJobId(), layer.getLayerId());

                frames.add(new Object[] { a, layer.getLayerId(), CueUtil.buildFrameName(layer,frameSet.get(size-i-1)) });
                frames.add(new Object[] { b, layer.getLayerId(), CueUtil.buildFrameName(layer,frameSet.get(i)) });

            } catch (Exception e) {
                logger.info("frame not found while attempting to reverse layer, skipping");
            }
        }

        if (frames.size() > 0) {
            getJdbcTemplate().batchUpdate(
                    "UPDATE frame SET int_dispatch_order=? WHERE pk_layer=? and str_name=?", frames);
        }
    }

    @Override
    public void staggerLayer(Layer layer, String frameRange, int stagger) {

        /*
         * If the layer is only 1 frame we don't stagger it.
         */
        if (getJdbcTemplate().queryForObject(
                "SELECT int_total_count FROM layer_stat WHERE pk_layer=?", Integer.class,
                layer.getLayerId()) == 1) {
            return;
        }

        logger.info("staggering: " + layer.getName() + " range: " + frameRange
                + " on " + stagger);

        FrameSet frameSet = null;
        FrameSet range = null;

        try {
            frameSet = new FrameSet(frameRange + ":" + stagger);
            range = new FrameSet(frameRange);
        } catch (Exception e) {
            logger.warn("failed to stagger layer: " + layer.getName() + ", " + e);
            return;
        }

        /*
         * Find the dispatch order of the first frame we're working with and base
         * our other staggers of this value.
         */
        int first = getJdbcTemplate().queryForObject(
                "SELECT int_dispatch_order FROM frame WHERE str_name=? AND pk_job=? AND pk_layer=?", Integer.class,
                CueUtil.buildFrameName(layer, range.get(0)), layer.getJobId(), layer.getLayerId());

        int size = range.size();
        for (int i=0; i < size; i++) {
            int frame = range.get(i);
            int newDispatchOrder = frameSet.index(frame) + first;

            getJdbcTemplate().update(
                    "UPDATE frame SET int_dispatch_order=? WHERE pk_layer=? and str_name=?",
                    newDispatchOrder, layer.getLayerId(), CueUtil.buildFrameName(layer, frame));
        }
    }

    @Override
    public boolean isFrameComplete(Frame f) {

        String state = getJdbcTemplate().queryForObject(
                "SELECT str_state FROM frame WHERE pk_frame=?",
                String.class, f.getFrameId());

        if (state.equals(FrameState.Succeeded.toString()) ||
                state.equals(FrameState.Eaten.toString())) {
            return true;
        }

        return false;
    }

    private static final
        RowMapper<ResourceUsage> RESOURCE_USAGE_MAPPER =
        new RowMapper<ResourceUsage>() {
        public ResourceUsage mapRow(ResultSet rs,
                int rowNum) throws SQLException {
            return new ResourceUsage(
                    rs.getLong("int_clock_time"),
                    rs.getInt("int_cores"));
        }

    };

    @Override
    public ResourceUsage getResourceUsage(Frame f) {
        /*
         * Using systimestamp = ts_started here because ts_stopped is not set.
         * Stopping the frame allows it to be dispatched again, which could
         * blow away the ts_stopped time.
         */
        return getJdbcTemplate().queryForObject(
                "SELECT " +
                    "NVL(interval_to_seconds(systimestamp - ts_started),1) " +
                        "AS int_clock_time, " +
                    "NVL(int_cores,100) AS int_cores " +
                "FROM " +
                    "frame " +
                "WHERE " +
                    "pk_frame = ?", RESOURCE_USAGE_MAPPER, f.getFrameId());
    }

    private static final String UPDATE_FRAME_MEMORY_USAGE =
        "UPDATE " +
            "frame " +
        "SET " +
            "ts_updated = systimestamp," +
            "int_mem_max_used = ?," +
            "int_mem_used = ? " +
        "WHERE " +
            "pk_frame = ? ";

    @Override
    public void updateFrameMemoryUsage(Frame f, long maxRss, long rss) {
        getJdbcTemplate().update(UPDATE_FRAME_MEMORY_USAGE,
                maxRss, rss, f.getFrameId());
    }

    /**
     * Attempt a SELECT FOR UPDATE NOWAIT on the frame record.  If
     * the frame is being modified by another transaction or if
     * the version has been incremented a FrameReservationException
     * is thrown.
     *
     * @param frame
     * @param state
     */
    @Override
    public void lockFrameForUpdate(Frame frame, FrameState state) {
        try {
            getJdbcTemplate().queryForObject(
                    "SELECT pk_frame FROM frame WHERE pk_frame=? AND " +
                    "str_state=? AND int_version =? FOR UPDATE NOWAIT",
                    String.class, frame.getFrameId(),
                    state.toString(), frame.getVersion());
        } catch (Exception e) {
            String error_msg = "the frame " +
                frame + " was updated by another thread.";
            throw new FrameReservationException(error_msg, e);
        }
    }

    @Override
    public boolean updateFrameCheckpointState(Frame frame, CheckpointState state) {

        logger.info("Setting checkpoint state to: " + state.toString());

        boolean result = false;

        if (state.equals(CheckpointState.Complete)) {
            /*
             * Only update the checkpoint state to complete if the state
             * is either Copying or Enabled.
             */
            result = getJdbcTemplate().update(
                    "UPDATE frame SET str_checkpoint_state=?, " +
                    "int_checkpoint_count=int_checkpoint_count + 1 WHERE " +
                    "pk_frame=? AND str_checkpoint_state IN (?, ?)",
                    CheckpointState.Complete.toString(),
                    frame.getFrameId(),
                    CheckpointState.Copying.toString(),
                    CheckpointState.Enabled.toString()) == 1;
        }
        else {
            result = getJdbcTemplate().update(
                    "UPDATE frame SET str_checkpoint_state=? WHERE pk_frame=?",
                    state.toString(), frame.getFrameId()) == 1;
        }

        /*
         * If the checkpoint state is complete or disabled then set the frame
         * state back to waiting, if and only if the frame state is currently
         * in the checkpoint state.
         */
        if ((state.equals(CheckpointState.Disabled)) ||
            state.equals(CheckpointState.Complete) && result) {
            getJdbcTemplate().update(
                    "UPDATE frame SET str_state=? WHERE pk_frame=? AND str_state=?",
                    FrameState.Waiting.toString(), frame.getFrameId(),
                    FrameState.Checkpoint.toString());
        }

        return result;
    }

    @Override
    public List<Frame> getStaleCheckpoints(int cutoffTimeSec) {
        return getJdbcTemplate().query(
                GET_MINIMAL_FRAME +
                " AND job.str_state=? " +
                " AND frame.str_state=? " +
                " AND systimestamp - frame.ts_stopped > interval '" + cutoffTimeSec + "' second",
                FRAME_MAPPER,
                JobState.Pending.toString(),
                FrameState.Checkpoint.toString());
    }
}

