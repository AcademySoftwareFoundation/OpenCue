
/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */

package com.imageworks.spcue.dao.postgres;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.EnumSet;
import java.util.List;
import java.sql.Timestamp;
import java.util.Optional;

import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.FrameEntity;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.LightweightDependency;
import com.imageworks.spcue.ResourceUsage;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.criteria.FrameSearchInterface;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.FrameReservationException;
import com.imageworks.spcue.grpc.depend.DependType;
import com.imageworks.spcue.grpc.job.CheckpointState;
import com.imageworks.spcue.grpc.job.FrameExitStatus;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.job.FrameStateDisplayOverride;
import com.imageworks.spcue.grpc.job.FrameStateDisplayOverrideSeq;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.grpc.job.LayerType;
import com.imageworks.spcue.util.CueUtil;
import com.imageworks.spcue.util.FrameSet;
import com.imageworks.spcue.util.SqlUtil;

public class FrameDaoJdbc extends JdbcDaoSupport implements FrameDao {

    private static final String UPDATE_FRAME_STOPPED_NORSS = "UPDATE " + "frame " + "SET "
            + "str_state=?, " + "int_exit_status = ?, " + "ts_stopped = current_timestamp, "
            + "ts_updated = current_timestamp,  " + "int_version = int_version + 1, "
            + "int_total_past_core_time = int_total_past_core_time + "
            + "round(INTERVAL_TO_SECONDS(current_timestamp - ts_started) * int_cores / 100),"
            + "int_total_past_gpu_time = int_total_past_gpu_time + "
            + "round(INTERVAL_TO_SECONDS(current_timestamp - ts_started) * int_gpus) " + "WHERE "
            + "frame.pk_frame = ? " + "AND " + "frame.str_state = ? " + "AND "
            + "frame.int_version = ? ";

    @Override
    public boolean updateFrameStopped(FrameInterface frame, FrameState state, int exitStatus) {
        return getJdbcTemplate().update(UPDATE_FRAME_STOPPED_NORSS, state.toString(), exitStatus,
                frame.getFrameId(), FrameState.RUNNING.toString(), frame.getVersion()) == 1;
    }

    private static final String UPDATE_FRAME_STOPPED = "UPDATE " + "frame " + "SET "
            + "str_state=?, " + "int_exit_status = ?, "
            + "ts_stopped = current_timestamp + interval '1' second, "
            + "ts_updated = current_timestamp, " + "int_mem_max_used = ?, "
            + "int_version = int_version + 1, "
            + "int_total_past_core_time = int_total_past_core_time + "
            + "round(INTERVAL_TO_SECONDS(current_timestamp + interval '1' second - ts_started) * int_cores / 100), "
            + "int_total_past_gpu_time = int_total_past_gpu_time + "
            + "round(INTERVAL_TO_SECONDS(current_timestamp + interval '1' second - ts_started) * int_gpus) "
            + "WHERE " + "frame.pk_frame = ? " + "AND " + "frame.str_state = ? " + "AND "
            + "frame.int_version = ? ";

    @Override
    public boolean updateFrameStopped(FrameInterface frame, FrameState state, int exitStatus,
            long maxRss) {

        return getJdbcTemplate().update(UPDATE_FRAME_STOPPED, state.toString(), exitStatus, maxRss,
                frame.getFrameId(), FrameState.RUNNING.toString(), frame.getVersion()) == 1;
    }

    private static final String UPDATE_FRAME_REASON = "UPDATE " + "frame " + "SET "
            + "str_state = ?, " + "int_exit_status = ?, " + "ts_stopped = current_timestamp, "
            + "ts_updated = current_timestamp, " + "int_version = int_version + 1 " + "WHERE "
            + "frame.pk_frame = ? " + "AND " + "frame.pk_frame NOT IN "
            + "(SELECT proc.pk_frame FROM " + "proc WHERE proc.pk_frame=?)";

    private int updateFrame(FrameInterface frame, int exitStatus) {

        int result = getJdbcTemplate().update(UPDATE_FRAME_REASON, FrameState.WAITING.toString(),
                exitStatus, frame.getFrameId(), frame.getFrameId());

        return result;
    }

    @Override
    public boolean updateFrameHostDown(FrameInterface frame) {
        return updateFrame(frame, Dispatcher.EXIT_STATUS_DOWN_HOST) > 0;
    }

    @Override
    public boolean updateFrameCleared(FrameInterface frame) {
        return updateFrame(frame, Dispatcher.EXIT_STATUS_FRAME_CLEARED) > 0;
    }

    private static final String UPDATE_FRAME_MEMORY_ERROR =
            "UPDATE " + "frame " + "SET " + "int_exit_status = ?, "
                    + "int_version = int_version + 1 " + "WHERE " + "frame.pk_frame = ? ";

    @Override
    public boolean updateFrameMemoryError(FrameInterface frame) {
        int result = getJdbcTemplate().update(UPDATE_FRAME_MEMORY_ERROR,
                Dispatcher.EXIT_STATUS_MEMORY_FAILURE, frame.getFrameId());

        return result > 0;
    }

    private static final String UPDATE_FRAME_STARTED = "UPDATE " + "frame " + "SET "
            + "str_state = ?, " + "str_host = ?, " + "int_cores = ?, " + "int_mem_reserved = ?, "
            + "int_gpus = ?, " + "int_gpu_mem_reserved = ?, " + "ts_updated = current_timestamp, "
            + "ts_started = current_timestamp, " + "ts_stopped = null, "
            + "int_version = int_version + 1 " + "WHERE " + "pk_frame = ? " + "AND "
            + "str_state = ? " + "AND " + "int_version = ? " + "AND " + "frame.pk_layer IN ("
            + "SELECT " + "layer.pk_layer " + "FROM " + "layer "
            + "LEFT JOIN layer_limit ON layer_limit.pk_layer = layer.pk_layer "
            + "LEFT JOIN limit_record ON limit_record.pk_limit_record = layer_limit.pk_limit_record "
            + "LEFT JOIN (" + "SELECT " + "limit_record.pk_limit_record, "
            + "SUM(layer_stat.int_running_count) AS int_sum_running " + "FROM " + "layer_limit "
            + "LEFT JOIN limit_record ON layer_limit.pk_limit_record = limit_record.pk_limit_record "
            + "LEFT JOIN layer_stat ON layer_stat.pk_layer = layer_limit.pk_layer "
            + "GROUP BY limit_record.pk_limit_record) AS sum_running "
            + "ON limit_record.pk_limit_record = sum_running.pk_limit_record " + "WHERE "
            + "sum_running.int_sum_running < limit_record.int_max_value "
            + "OR sum_running.int_sum_running IS NULL " + ")";

    private static final String UPDATE_FRAME_RETRIES =
            "UPDATE " + "frame " + "SET " + "int_retries = int_retries + 1 " + "WHERE "
                    + "pk_frame = ? " + "AND " + "int_exit_status NOT IN (?,?,?,?,?,?,?) ";

    @Override
    public void updateFrameStarted(VirtualProc proc, FrameInterface frame) {

        lockFrameForUpdate(frame, FrameState.WAITING);

        try {
            int result = getJdbcTemplate().update(UPDATE_FRAME_STARTED,
                    FrameState.RUNNING.toString(), proc.hostName, proc.coresReserved,
                    proc.memoryReserved, proc.gpusReserved, proc.gpuMemoryReserved,
                    frame.getFrameId(), FrameState.WAITING.toString(), frame.getVersion());
            if (result == 0) {
                String error_msg = "the frame " + frame + " was updated by another thread.";
                throw new FrameReservationException(error_msg);
            }
        } catch (DataAccessException e) {
            /*
             * This usually happens when the folder's max cores limit has exceeded
             */
            throw new FrameReservationException(e.getCause());
        }

        /*
         * Frames that were killed via nimby or hardware errors not attributed to the software do
         * not increment the retry counter. Like failed launch, orphaned frame, failed kill or down
         * host.
         */
        try {
            getJdbcTemplate().update(UPDATE_FRAME_RETRIES, frame.getFrameId(), -1,
                    FrameExitStatus.SKIP_RETRY_VALUE, FrameExitStatus.FAILED_LAUNCH_VALUE,
                    Dispatcher.EXIT_STATUS_FRAME_CLEARED, Dispatcher.EXIT_STATUS_FRAME_ORPHAN,
                    Dispatcher.EXIT_STATUS_FAILED_KILL, Dispatcher.EXIT_STATUS_DOWN_HOST);
        } catch (DataAccessException e) {
            throw new FrameReservationException(e.getCause());
        }
    }

    private static final String UPDATE_FRAME_FIXED =
            "UPDATE " + "frame " + "SET " + "str_state = ?," + "str_host=?, " + "int_cores=?, "
                    + "int_mem_reserved = ?, " + "int_gpus = ?, " + "int_gpu_mem_reserved = ?, "
                    + "ts_updated = current_timestamp, " + "ts_started = current_timestamp, "
                    + "ts_stopped = null, " + "int_version = int_version + 1 " + "WHERE "
                    + "pk_frame = ? " + "AND " + "str_state = 'RUNNING'";

    @Override
    public boolean updateFrameFixed(VirtualProc proc, FrameInterface frame) {
        return getJdbcTemplate().update(UPDATE_FRAME_FIXED, FrameState.RUNNING.toString(),
                proc.hostName, proc.coresReserved, proc.memoryReserved, proc.gpusReserved,
                proc.gpuMemoryReserved, frame.getFrameId()) == 1;
    }

    @Override
    public DispatchFrame getDispatchFrame(String uuid) {
        return getJdbcTemplate().queryForObject(GET_DISPATCH_FRAME, DISPATCH_FRAME_MAPPER, uuid);
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
            int uid = rs.getInt("int_uid");
            frame.uid = rs.wasNull() ? Optional.empty() : Optional.of(uid);
            frame.state = FrameState.valueOf(rs.getString("frame_state"));
            frame.minCores = rs.getInt("int_cores_min");
            frame.maxCores = rs.getInt("int_cores_max");
            frame.threadable = rs.getBoolean("b_threadable");
            frame.setMinMemory(rs.getLong("int_mem_min"));
            frame.minGpus = rs.getInt("int_gpus_min");
            frame.maxGpus = rs.getInt("int_gpus_max");
            frame.minGpuMemory = rs.getLong("int_gpu_mem_min");
            frame.version = rs.getInt("int_version");
            frame.services = rs.getString("str_services");
            frame.os = rs.getString("str_os");
            frame.lokiURL = rs.getString("str_loki_url");
            return frame;
        }
    };

    private static final String GET_DISPATCH_FRAME = "SELECT " + "show.str_name AS show_name, "
            + "job.str_name AS job_name, " + "job.pk_job," + "job.pk_show," + "job.pk_facility,"
            + "job.str_name," + "job.str_shot," + "job.str_user," + "job.int_uid,"
            + "job.str_log_dir," + "COALESCE(str_os, '') AS str_os, "
            + "COALESCE(str_loki_url, '') AS str_loki_url, " + "frame.str_name AS frame_name, "
            + "frame.str_state AS frame_state, " + "frame.pk_frame, " + "frame.pk_layer, "
            + "frame.int_retries, " + "frame.int_version, " + "layer.str_name AS layer_name, "
            + "layer.str_type AS layer_type, " + "layer.str_cmd, " + "layer.int_cores_min,"
            + "layer.int_cores_max," + "layer.b_threadable," + "layer.int_mem_min, "
            + "layer.int_gpus_min," + "layer.int_gpus_max," + "layer.int_gpu_mem_min, "
            + "layer.str_range, " + "layer.int_chunk_size, " + "layer.str_services " + "FROM "
            + "layer, " + "job, " + "show, "
            + "frame LEFT JOIN proc ON (proc.pk_frame = frame.pk_frame) " + "WHERE "
            + "job.pk_show = show.pk_show " + "AND " + "frame.pk_job = job.pk_job " + "AND "
            + "frame.pk_layer = layer.pk_layer " + "AND " + "frame.pk_frame = ?";

    private static final String GET_FRAME_DETAIL =
            "SELECT " + "frame.*, " + "job.pk_facility," + "job.pk_show " + "FROM " + "frame,"
                    + "layer," + "job," + "show " + "WHERE " + "frame.pk_job = job.pk_job " + "AND "
                    + "frame.pk_layer = layer.pk_layer " + "AND " + "job.pk_show = show.pk_show ";

    private static final String GET_MINIMAL_FRAME = "SELECT " + "frame.pk_frame,"
            + "frame.str_name, " + "frame.pk_job, " + "frame.pk_layer, " + "frame.str_state, "
            + "frame.int_version, " + "job.pk_show, " + "job.pk_facility " + "FROM " + "frame,"
            + "layer," + "job," + "show " + "WHERE " + "frame.pk_job = job.pk_job " + "AND "
            + "frame.pk_layer = layer.pk_layer " + "AND " + "job.pk_show = show.pk_show ";

    private static final RowMapper<FrameInterface> FRAME_MAPPER = new RowMapper<FrameInterface>() {
        public FrameEntity mapRow(ResultSet rs, int rowNum) throws SQLException {
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
            frame.maxRss = rs.getLong("int_mem_max_used");
            frame.name = rs.getString("str_name");
            frame.number = rs.getInt("int_number");
            frame.dispatchOrder = rs.getInt("int_dispatch_order");
            frame.retryCount = rs.getInt("int_retries");
            frame.dateStarted = rs.getTimestamp("ts_started");
            frame.dateStopped = rs.getTimestamp("ts_stopped");
            frame.dateUpdated = rs.getTimestamp("ts_updated");
            frame.dateLLU = rs.getTimestamp("ts_llu");
            frame.version = rs.getInt("int_version");

            if (rs.getString("str_host") != null) {
                frame.lastResource = String.format("%s/%d/%d", rs.getString("str_host"),
                        rs.getInt("int_cores"), rs.getInt("int_gpus"));
            } else {
                frame.lastResource = "";
            }
            frame.state = FrameState.valueOf(rs.getString("str_state"));

            return frame;
        }
    };

    public static final String FIND_ORPHANED_FRAMES = "SELECT " + "frame.pk_frame, "
            + "frame.pk_layer, " + "frame.str_name, " + "frame.int_version, " + "job.pk_job, "
            + "job.pk_show, " + "job.pk_facility " + "FROM " + "frame, " + "job " + "WHERE "
            + "job.pk_job = frame.pk_job " + "AND " + "frame.str_state = 'RUNNING' " + "AND "
            + "job.str_state = 'PENDING' " + "AND "
            + "(SELECT COUNT(1) FROM proc WHERE proc.pk_frame = frame.pk_frame) = 0 " + "AND "
            + "current_timestamp - frame.ts_updated > interval '300' second";

    @Override
    public List<FrameInterface> getOrphanedFrames() {
        return getJdbcTemplate().query(FIND_ORPHANED_FRAMES, FRAME_MAPPER);
    }

    private static final String IS_ORPHAN = "SELECT " + "COUNT(1) " + "FROM " + "frame " + "WHERE "
            + "frame.pk_frame = ? " + "AND " + "frame.str_state = 'RUNNING' " + "AND "
            + "(SELECT COUNT(1) FROM proc WHERE proc.pk_frame = frame.pk_frame) = 0 " + "AND "
            + "current_timestamp - frame.ts_updated > interval '300' second";

    @Override
    public boolean isOrphan(FrameInterface frame) {
        return getJdbcTemplate().queryForObject(IS_ORPHAN, Integer.class, frame.getFrameId()) == 1;
    }

    private static final String INSERT_FRAME = "INSERT INTO " + "frame " + "(" + "pk_frame, "
            + "pk_layer, " + "pk_job, " + "str_name, " + "str_state, " + "int_number, "
            + "int_dispatch_order, " + "int_layer_order, " + "ts_updated, " + "ts_llu " + ") "
            + "VALUES (?,?,?,?,?,?,?,?,current_timestamp,current_timestamp)";

    @Override
    public void insertFrames(LayerDetail layer, List<Integer> frames) {

        int count = 0;
        for (int frame : frames) {
            getJdbcTemplate().update(INSERT_FRAME, SqlUtil.genKeyRandom(), layer.getLayerId(),
                    layer.getJobId(), CueUtil.buildFrameName(layer, frame),
                    FrameState.SETUP.toString(), frame, count, layer.dispatchOrder);
            count++;
        }
    }

    @Override
    public List<FrameInterface> getDependentFrames(LightweightDependency depend) {

        /*
         * Compound depends are handled in the DependManager.
         */

        String key = null;
        StringBuilder sb = new StringBuilder(4096);
        sb.append(GET_MINIMAL_FRAME);
        sb.append(" AND frame.int_depend_count > 0 ");

        if (EnumSet.of(DependType.JOB_ON_JOB, DependType.JOB_ON_LAYER, DependType.JOB_ON_FRAME)
                .contains(depend.type)) {
            sb.append("AND job.pk_job = ?");
            key = depend.dependErJobId;
        } else if (EnumSet
                .of(DependType.LAYER_ON_FRAME, DependType.LAYER_ON_LAYER, DependType.LAYER_ON_JOB)
                .contains(depend.type)) {
            sb.append("AND layer.pk_layer = ?");
            key = depend.dependErLayerId;
        } else if (EnumSet
                .of(DependType.FRAME_ON_JOB, DependType.FRAME_ON_LAYER, DependType.FRAME_ON_FRAME)
                .contains(depend.type)) {
            sb.append("AND frame.pk_frame = ?");
            key = depend.dependErFrameId;
        } else {
            return new ArrayList<FrameInterface>(1);
        }

        return getJdbcTemplate().query(sb.toString(), FRAME_MAPPER, new Object[] {key});
    }

    @Override
    public FrameInterface findFrame(LayerInterface layer, int number) {
        return getJdbcTemplate().queryForObject(
                GET_MINIMAL_FRAME + " AND frame.pk_layer=? AND int_number=?", FRAME_MAPPER,
                layer.getLayerId(), number);
    }

    @Override
    public FrameDetail getFrameDetail(FrameInterface frame) {
        return getJdbcTemplate().queryForObject(GET_FRAME_DETAIL + " AND pk_frame=?",
                FRAME_DETAIL_MAPPER, frame.getFrameId());
    }

    @Override
    public FrameDetail getFrameDetail(String id) {
        return getJdbcTemplate().queryForObject(GET_FRAME_DETAIL + " AND pk_frame=?",
                FRAME_DETAIL_MAPPER, id);
    }

    @Override
    public FrameDetail findFrameDetail(JobInterface job, String name) {
        // Uses C_FRAME_STR_NAME_UNQ
        return getJdbcTemplate().queryForObject(
                GET_FRAME_DETAIL + " AND frame.str_name=? AND frame.pk_job=?", FRAME_DETAIL_MAPPER,
                name, job.getJobId());
    }

    @Override
    public List<FrameDetail> findFrameDetails(FrameSearchInterface r) {
        return getJdbcTemplate().query(r.getFilteredQuery(GET_FRAME_DETAIL), FRAME_DETAIL_MAPPER,
                r.getValuesArray());
    }

    @Override
    public List<FrameInterface> findFrames(FrameSearchInterface r) {
        return getJdbcTemplate().query(r.getFilteredQuery(GET_MINIMAL_FRAME), FRAME_MAPPER,
                r.getValuesArray());
    }

    private static final String FIND_LONGEST_FRAME = "SELECT " + "pk_frame " + "FROM " + "frame, "
            + "layer " + "WHERE " + "frame.pk_layer = layer.pk_layer " + "AND "
            + "frame.pk_job = ? " + "AND " + "str_state=? " + "AND " + "layer.str_type=? "
            + "ORDER BY " + "ts_stopped - ts_started DESC " + "LIMIT 1";

    @Override
    public FrameDetail findLongestFrame(JobInterface job) {
        String pk_frame = getJdbcTemplate().queryForObject(FIND_LONGEST_FRAME, String.class,
                job.getJobId(), FrameState.SUCCEEDED.toString(), LayerType.RENDER.toString());
        return getFrameDetail(pk_frame);
    }

    private static final String FIND_SHORTEST_FRAME = "SELECT " + "pk_frame " + "FROM " + "frame, "
            + "layer " + "WHERE " + "frame.pk_layer = layer.pk_layer " + "AND "
            + "frame.pk_job = ? " + "AND " + "frame.str_state = ? " + "AND " + "layer.str_type = ? "
            + "ORDER BY " + "ts_stopped - ts_started ASC " + "LIMIT 1";

    @Override
    public FrameDetail findShortestFrame(JobInterface job) {
        String pk_frame = getJdbcTemplate().queryForObject(FIND_SHORTEST_FRAME, String.class,
                job.getJobId(), FrameState.SUCCEEDED.toString(), LayerType.RENDER.toString());
        return getFrameDetail(pk_frame);
    }

    @Override
    public FrameInterface getFrame(String id) {
        return getJdbcTemplate().queryForObject(GET_MINIMAL_FRAME + " AND frame.pk_frame=?",
                FRAME_MAPPER, id);
    }

    @Override
    public FrameInterface findFrame(JobInterface job, String name) {
        // Uses C_FRAME_STR_NAME_UNQ
        return getJdbcTemplate().queryForObject(
                GET_MINIMAL_FRAME + " AND frame.str_name=? AND frame.pk_job=?", FRAME_MAPPER, name,
                job.getJobId());
    }

    @Override
    public void checkRetries(FrameInterface frame) {
        int max_retries = getJdbcTemplate().queryForObject(
                "SELECT int_max_retries FROM job WHERE pk_job=?", Integer.class, frame.getJobId());

        if (getJdbcTemplate().queryForObject("SELECT int_retries FROM frame WHERE pk_frame=?",
                Integer.class, frame.getFrameId()) >= max_retries) {
            getJdbcTemplate().update("UPDATE frame SET str_state=? WHERE pk_frame=?",
                    FrameState.DEAD.toString(), frame.getFrameId());
        }
    }

    private static final String UPDATE_FRAME_STATE =
            "UPDATE " + "frame " + "SET " + "str_state = ?, " + "ts_updated = current_timestamp, "
                    + "int_version = int_version + 1 " + "WHERE " + "pk_frame = ? " + "AND "
                    + "int_version = ? ";

    @Override
    public boolean updateFrameState(FrameInterface frame, FrameState state) {
        if (getJdbcTemplate().update(UPDATE_FRAME_STATE, state.toString(), frame.getFrameId(),
                frame.getVersion()) == 1) {
            logger.info("The frame " + frame + " state changed to " + state.toString());
            return true;
        }
        logger.info("Failed to change the frame " + frame + " state to " + state.toString());
        return false;
    }

    private static final String MARK_AS_WAITING = "UPDATE " + "frame " + "SET " + "str_state=?, "
            + "ts_updated = current_timestamp, " + "ts_llu = current_timestamp, "
            + "int_depend_count = 0, " + "int_version = int_version + 1 " + "WHERE "
            + "pk_frame = ? " + "AND " + "int_version = ? " + "AND " + "str_state = ? ";

    @Override
    public void markFrameAsWaiting(FrameInterface frame) {
        getJdbcTemplate().update(MARK_AS_WAITING, FrameState.WAITING.toString(), frame.getFrameId(),
                frame.getVersion(), FrameState.DEPEND.toString());
    }

    private static final String MARK_AS_DEPEND = "UPDATE " + "frame " + "SET " + "str_state=?, "
            + "int_depend_count = ?, " + "ts_updated = current_timestamp, "
            + "int_version = int_version + 1 " + "WHERE " + "pk_frame = ? " + "AND "
            + "int_version = ? " + "AND " + "str_state = ? ";

    private static final String GET_FRAME_DEPEND_COUNT =
            "SELECT " + "COUNT(1) " + "FROM " + "depend " + "WHERE " + "( "
                    + "(pk_job_depend_er = ? AND str_type LIKE 'JOB#_ON%' ESCAPE '#') " + "OR "
                    + "pk_layer_depend_er = ? " + "OR " + "pk_frame_depend_er = ? " + ") " + "AND "
                    + "depend.b_active = true " + "AND " + "depend.b_composite = false ";

    public void markFrameAsDepend(FrameInterface frame) {
        // We need to full depend count in this case to reset the
        // frames's depend count accurately.
        int depend_count = getJdbcTemplate().queryForObject(GET_FRAME_DEPEND_COUNT, Integer.class,
                frame.getJobId(), frame.getLayerId(), frame.getFrameId());

        if (depend_count > 0) {
            getJdbcTemplate().update(MARK_AS_DEPEND, FrameState.DEPEND.toString(), depend_count,
                    frame.getFrameId(), frame.getVersion(), FrameState.WAITING.toString());
        }
    }

    private static final String FIND_HIGHEST_MEM_FRAME =
            "SELECT " + "pk_frame " + "FROM " + "frame " + "WHERE " + "pk_job = ? " + "AND "
                    + "str_state = ? " + "ORDER BY " + "int_mem_max_used DESC " + "LIMIT 1";

    @Override
    public FrameDetail findHighestMemoryFrame(JobInterface job) {
        String pk_frame = getJdbcTemplate().queryForObject(FIND_HIGHEST_MEM_FRAME, String.class,
                job.getJobId(), FrameState.SUCCEEDED.toString());
        return getFrameDetail(pk_frame);
    }

    private static final String FIND_LOWEST_MEM_FRAME =
            "SELECT " + "pk_frame " + "FROM " + "frame " + "WHERE " + "pk_job = ? " + "AND "
                    + "str_state = ? " + "ORDER BY " + "int_mem_max_used ASC " + "LIMIT 1";

    @Override
    public FrameDetail findLowestMemoryFrame(JobInterface job) {
        String pk_frame = getJdbcTemplate().queryForObject(FIND_LOWEST_MEM_FRAME, String.class,
                job.getJobId(), FrameState.SUCCEEDED.toString());
        return getFrameDetail(pk_frame);
    }

    @Override
    public void reorderFramesFirst(LayerInterface layer, FrameSet frameSet) {
        int start;
        int size = frameSet.size();
        int min = getJdbcTemplate().queryForObject(
                "SELECT MIN(int_dispatch_order) FROM frame WHERE pk_layer=?", Integer.class,
                layer.getLayerId());

        start = min - size;
        for (int frameIdx = 0; frameIdx < size; frameIdx++) {
            getJdbcTemplate().update(
                    "UPDATE frame SET int_dispatch_order=? WHERE str_name=? AND pk_job=?", start,
                    CueUtil.buildFrameName(layer, frameSet.get(frameIdx)), layer.getJobId());

            logger.info("reordering " + CueUtil.buildFrameName(layer, frameSet.get(frameIdx))
                    + " to " + start);
            start++;
        }
    }

    @Override
    public void reorderFramesLast(LayerInterface layer, FrameSet frameSet) {
        int start;
        int size = frameSet.size();
        List<Object[]> frames = new ArrayList<>(size);
        int max = getJdbcTemplate().queryForObject(
                "SELECT MAX(int_dispatch_order) FROM frame WHERE pk_layer=?", Integer.class,
                layer.getLayerId());

        start = max + 1;
        for (int i = 0; i <= size; i++) {
            frames.add(
                    new Object[] {start + i, CueUtil.buildFrameName(layer, i), layer.getJobId()});
        }

        if (frames.size() > 0) {
            getJdbcTemplate().batchUpdate(
                    "UPDATE frame SET int_dispatch_order=? WHERE str_name=? AND pk_job=?", frames);
        }
    }

    @Override
    public void reorderLayerReverse(LayerInterface layer, FrameSet frameSet) {

        int size = frameSet.size();
        List<Object[]> frames = new ArrayList<>(size);

        for (int i = 0; i < size; i++) {
            if (i >= size - i - 1) {
                break;
            }
            try {
                int a = getJdbcTemplate().queryForObject(
                        "SELECT int_dispatch_order FROM frame WHERE str_name=? AND pk_job=? AND pk_layer=?",
                        Integer.class, CueUtil.buildFrameName(layer, frameSet.get(i)),
                        layer.getJobId(), layer.getLayerId());

                int b = getJdbcTemplate().queryForObject(
                        "SELECT int_dispatch_order FROM frame WHERE str_name=? AND pk_job=? AND pk_layer=?",
                        Integer.class, CueUtil.buildFrameName(layer, frameSet.get(size - i - 1)),
                        layer.getJobId(), layer.getLayerId());

                frames.add(new Object[] {a, layer.getLayerId(),
                        CueUtil.buildFrameName(layer, frameSet.get(size - i - 1))});
                frames.add(new Object[] {b, layer.getLayerId(),
                        CueUtil.buildFrameName(layer, frameSet.get(i))});

            } catch (Exception e) {
                logger.info("frame not found while attempting to reverse layer, skipping");
            }
        }

        if (frames.size() > 0) {
            getJdbcTemplate().batchUpdate(
                    "UPDATE frame SET int_dispatch_order=? WHERE pk_layer=? and str_name=?",
                    frames);
        }
    }

    @Override
    public void staggerLayer(LayerInterface layer, String frameRange, int stagger) {

        /*
         * If the layer is only 1 frame we don't stagger it.
         */
        if (getJdbcTemplate().queryForObject(
                "SELECT int_total_count FROM layer_stat WHERE pk_layer=?", Integer.class,
                layer.getLayerId()) == 1) {
            return;
        }

        logger.info("staggering: " + layer.getName() + " range: " + frameRange + " on " + stagger);

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
         * Find the dispatch order of the first frame we're working with and base our other staggers
         * of this value.
         */
        int first = getJdbcTemplate().queryForObject(
                "SELECT int_dispatch_order FROM frame WHERE str_name=? AND pk_job=? AND pk_layer=?",
                Integer.class, CueUtil.buildFrameName(layer, range.get(0)), layer.getJobId(),
                layer.getLayerId());

        int size = range.size();
        for (int i = 0; i < size; i++) {
            int frame = range.get(i);
            int newDispatchOrder = frameSet.index(frame) + first;

            getJdbcTemplate().update(
                    "UPDATE frame SET int_dispatch_order=? WHERE pk_layer=? and str_name=?",
                    newDispatchOrder, layer.getLayerId(), CueUtil.buildFrameName(layer, frame));
        }
    }

    @Override
    public boolean isFrameComplete(FrameInterface f) {

        String state = getJdbcTemplate().queryForObject(
                "SELECT str_state FROM frame WHERE pk_frame=?", String.class, f.getFrameId());

        if (state.equals(FrameState.SUCCEEDED.toString())
                || state.equals(FrameState.EATEN.toString())) {
            return true;
        }

        return false;
    }

    private static final RowMapper<ResourceUsage> RESOURCE_USAGE_MAPPER =
            new RowMapper<ResourceUsage>() {
                public ResourceUsage mapRow(ResultSet rs, int rowNum) throws SQLException {
                    return new ResourceUsage(rs.getLong("int_clock_time"), rs.getInt("int_cores"),
                            rs.getInt("int_gpus"));
                }

            };

    @Override
    public ResourceUsage getResourceUsage(FrameInterface f) {
        /*
         * Using current_timestamp = ts_started here because ts_stopped is not set. Stopping the
         * frame allows it to be dispatched again, which could blow away the ts_stopped time.
         */
        return getJdbcTemplate().queryForObject(
                "SELECT " + "COALESCE(interval_to_seconds(current_timestamp - ts_started), 1) "
                        + "AS int_clock_time, " + "COALESCE(int_cores, 100) AS int_cores,"
                        + "int_gpus " + "FROM " + "frame " + "WHERE " + "pk_frame = ?",
                RESOURCE_USAGE_MAPPER, f.getFrameId());
    }

    private static final String UPDATE_FRAME_MEMORY_USAGE_AND_LLU_TIME = "UPDATE " + "frame "
            + "SET " + "ts_updated = current_timestamp," + "int_mem_max_used = ?,"
            + "int_mem_used = ?," + "ts_llu = ? " + "WHERE " + "pk_frame = ? ";

    @Override
    public void updateFrameMemoryUsageAndLluTime(FrameInterface f, long maxRss, long rss,
            long lluTime) {
        getJdbcTemplate().update(UPDATE_FRAME_MEMORY_USAGE_AND_LLU_TIME, maxRss, rss,
                new Timestamp(lluTime * 1000l), f.getFrameId());
    }

    /**
     * Attempt a SELECT FOR UPDATE NOWAIT on the frame record. If the frame is being modified by
     * another transaction or if the version has been incremented a FrameReservationException is
     * thrown.
     *
     * @param frame
     * @param state
     */
    @Override
    public void lockFrameForUpdate(FrameInterface frame, FrameState state) {
        try {
            getJdbcTemplate().queryForObject(
                    "SELECT pk_frame FROM frame WHERE pk_frame=? AND "
                            + "str_state=? AND int_version =? FOR UPDATE NOWAIT",
                    String.class, frame.getFrameId(), state.toString(), frame.getVersion());
        } catch (Exception e) {
            String error_msg = "the frame " + frame + " was updated by another thread.";
            throw new FrameReservationException(error_msg, e);
        }
    }

    @Override
    public boolean updateFrameCheckpointState(FrameInterface frame, CheckpointState state) {

        logger.info("Setting checkpoint state to: " + state.toString());

        boolean result = false;

        if (state.equals(CheckpointState.COMPLETE)) {
            /*
             * Only update the checkpoint state to complete if the state is either Copying or
             * Enabled.
             */
            result = getJdbcTemplate().update(
                    "UPDATE frame SET str_checkpoint_state=?, "
                            + "int_checkpoint_count=int_checkpoint_count + 1 WHERE "
                            + "pk_frame=? AND str_checkpoint_state IN (?, ?)",
                    CheckpointState.COMPLETE.toString(), frame.getFrameId(),
                    CheckpointState.COPYING.toString(), CheckpointState.ENABLED.toString()) == 1;
        } else {
            result = getJdbcTemplate().update(
                    "UPDATE frame SET str_checkpoint_state=? WHERE pk_frame=?", state.toString(),
                    frame.getFrameId()) == 1;
        }

        /*
         * If the checkpoint state is complete or disabled then set the frame state back to waiting,
         * if and only if the frame state is currently in the checkpoint state.
         */
        if ((state.equals(CheckpointState.DISABLED))
                || state.equals(CheckpointState.COMPLETE) && result) {
            getJdbcTemplate().update(
                    "UPDATE frame SET str_state=? WHERE pk_frame=? AND str_state=?",
                    FrameState.WAITING.toString(), frame.getFrameId(),
                    FrameState.CHECKPOINT.toString());
        }

        return result;
    }

    @Override
    public List<FrameInterface> getStaleCheckpoints(int cutoffTimeSec) {
        return getJdbcTemplate().query(
                GET_MINIMAL_FRAME + " AND job.str_state=? " + " AND frame.str_state=? "
                        + " AND current_timestamp - frame.ts_stopped > interval '" + cutoffTimeSec
                        + "' second",
                FRAME_MAPPER, JobState.PENDING.toString(), FrameState.CHECKPOINT.toString());
    }

    private static final String CREATE_FRAME_STATE_OVERRIDE =
            "INSERT INTO frame_state_display_overrides (" + "pk_frame_override," + "pk_frame,"
                    + "str_frame_state," + "str_override_text," + "str_rgb" + ") "
                    + "VALUES (?,?,?,?,?)";

    @Override
    public void setFrameStateDisplayOverride(String frameId, FrameStateDisplayOverride override) {
        getJdbcTemplate().update(CREATE_FRAME_STATE_OVERRIDE, SqlUtil.genKeyRandom(), frameId,
                override.getState().toString(), override.getText(),
                Integer.toString(override.getColor().getRed()) + ","
                        + Integer.toString(override.getColor().getGreen()) + ","
                        + Integer.toString(override.getColor().getBlue()));
    }

    private static final String GET_FRAME_STATE_OVERRIDE =
            "SELECT * from frame_state_display_overrides WHERE pk_frame = ?";

    private static final RowMapper<FrameStateDisplayOverride> OVERRIDE_MAPPER =
            new RowMapper<FrameStateDisplayOverride>() {
                public FrameStateDisplayOverride mapRow(ResultSet rs, int rowNum)
                        throws SQLException {
                    String[] rgb = rs.getString("str_rgb").split(",");
                    return FrameStateDisplayOverride.newBuilder()
                            .setState(FrameState.valueOf(rs.getString("str_frame_state")))
                            .setText(rs.getString("str_override_text"))
                            .setColor(FrameStateDisplayOverride.RGB.newBuilder()
                                    .setRed(Integer.parseInt(rgb[0]))
                                    .setGreen(Integer.parseInt(rgb[1]))
                                    .setBlue(Integer.parseInt(rgb[2])).build())
                            .build();
                }
            };

    @Override
    public FrameStateDisplayOverrideSeq getFrameStateDisplayOverrides(String frameId) {
        List<FrameStateDisplayOverride> overrides =
                getJdbcTemplate().query(GET_FRAME_STATE_OVERRIDE, OVERRIDE_MAPPER, frameId);
        return FrameStateDisplayOverrideSeq.newBuilder().addAllOverrides(overrides).build();
    }

    private static final String UPDATE_FRAME_STATE_OVERRIDE =
            "UPDATE " + "frame_state_display_overrides " + "SET " + "str_override_text = ?,"
                    + "str_rgb = ? " + "WHERE " + "pk_frame = ? " + "AND " + "str_frame_state = ?";

    @Override
    public void updateFrameStateDisplayOverride(String frameId,
            FrameStateDisplayOverride override) {
        getJdbcTemplate().update(UPDATE_FRAME_STATE_OVERRIDE, override.getText(),
                Integer.toString(override.getColor().getRed()) + ","
                        + Integer.toString(override.getColor().getGreen()) + ","
                        + Integer.toString(override.getColor().getBlue()),
                frameId, override.getState().toString());
    }
}
