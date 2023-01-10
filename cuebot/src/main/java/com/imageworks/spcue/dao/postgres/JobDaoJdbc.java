
/*
 * Copyright Contributors to the OpenCue Project
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
import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.BuildableJob;
import com.imageworks.spcue.DepartmentInterface;
import com.imageworks.spcue.DispatchJob;
import com.imageworks.spcue.EntityModificationError;
import com.imageworks.spcue.ExecutionSummary;
import com.imageworks.spcue.FacilityInterface;
import com.imageworks.spcue.FrameStateTotals;
import com.imageworks.spcue.GroupDetail;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.Inherit;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.ResourceUsage;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.TaskEntity;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.util.CueUtil;
import com.imageworks.spcue.util.JobLogUtil;
import com.imageworks.spcue.util.SqlUtil;

public class JobDaoJdbc extends JdbcDaoSupport implements JobDao {
    private static final Pattern LAST_JOB_STRIP_PATTERN = Pattern.compile("_v*([_0-9]*$)");

    /*
     * Maps a row to a DispatchJob object
     */
    public static final RowMapper<DispatchJob> DISPATCH_JOB_MAPPER = new RowMapper<DispatchJob>() {
        public DispatchJob mapRow(ResultSet rs, int rowNum) throws SQLException {
            DispatchJob job = new DispatchJob();
            job.id = rs.getString("pk_job");
            job.showId = rs.getString("pk_show");
            job.facilityId = rs.getString("pk_facility");
            job.name = rs.getString("str_name");
            job.state = JobState.valueOf(rs.getString("str_state"));
            job.maxRetries = rs.getInt("int_max_retries");
            job.paused = rs.getBoolean("b_paused");
            job.autoEat = rs.getBoolean("b_autoeat");
            job.autoBook = rs.getBoolean("b_auto_book");
            job.autoUnbook = rs.getBoolean("b_auto_unbook");
            return job;
        }
    };

    /*
     * Maps a row to minimal job.
     */
    public static final RowMapper<JobInterface> JOB_MAPPER = new RowMapper<JobInterface>() {
        public JobInterface mapRow(final ResultSet rs, int rowNum) throws SQLException {
            return new JobInterface() {
                final String jobid = rs.getString("pk_job");
                final String showid = rs.getString("pk_show");
                final String name = rs.getString("str_name");
                final String facility = rs.getString("pk_facility");
                public String getJobId() { return jobid; }
                public String getShowId() { return showid; }
                public String getId() { return jobid; }
                public String getName() { return name; }
                public String getFacilityId() { return facility; }
            };
        }
    };

    /*
     * Maps a row to a JobDetail object
     */
    private static final RowMapper<JobDetail> JOB_DETAIL_MAPPER =
        new RowMapper<JobDetail>() {
            public JobDetail mapRow(ResultSet rs, int rowNum) throws SQLException {
                JobDetail job = new JobDetail();
                job.id = rs.getString("pk_job");
                job.showId = rs.getString("pk_show");
                job.facilityId = rs.getString("pk_facility");
                job.deptId = rs.getString("pk_dept");
                job.groupId = rs.getString("pk_folder");
                job.logDir = rs.getString("str_log_dir");
                job.maxCoreUnits = rs.getInt("int_max_cores");
                job.minCoreUnits = rs.getInt("int_min_cores");
                job.maxGpuUnits = rs.getInt("int_max_gpus");
                job.minGpuUnits = rs.getInt("int_min_gpus");
                job.name = rs.getString("str_name");
                job.priority = rs.getInt("int_priority");
                job.shot = rs.getString("str_shot");
                job.state = JobState.valueOf(rs.getString("str_state"));
                int uid = rs.getInt("int_uid");
                job.uid = rs.wasNull() ? Optional.empty() : Optional.of(uid);
                job.user = rs.getString("str_user");
                job.email = rs.getString("str_email");
                job.totalFrames = rs.getInt("int_frame_count");
                job.totalLayers = rs.getInt("int_layer_count");
                Timestamp startTime = rs.getTimestamp("ts_started");
                job.startTime = startTime != null ? (int) (startTime.getTime() / 1000) : 0;
                Timestamp stopTime = rs.getTimestamp("ts_stopped");
                job.stopTime = stopTime != null ? (int) (stopTime.getTime() / 1000) : 0;
                job.isPaused = rs.getBoolean("b_paused");
                job.maxRetries = rs.getInt("int_max_retries");
                job.showName = rs.getString("show_name");
                job.facilityName = rs.getString("facility_name");
                job.deptName = rs.getString("dept_name");
                return job;
            }
        };

    private static final String GET_DISPATCH_JOB =
        "SELECT " +
            "job.pk_job, " +
            "job.pk_facility, " +
            "job.pk_show, " +
            "job.str_name, "+
            "job.str_show, " +
            "job.str_state, "+
            "job.b_paused, "+
            "job.int_max_retries, " +
            "job.b_autoeat, " +
            "job.b_auto_book,"+
            "job.b_auto_unbook " +
        "FROM " +
            "job "+
        "WHERE " +
            "pk_job = ?";

    @Override
    public DispatchJob getDispatchJob(String uuid) {
        return getJdbcTemplate().queryForObject(
            GET_DISPATCH_JOB, DISPATCH_JOB_MAPPER, uuid);
    }

    private static final String IS_JOB_COMPLETE =
        "SELECT " +
            "SUM (" +
                "int_waiting_count + " +
                "int_running_count + " +
                "int_dead_count + " +
                "int_depend_count + " +
                "int_checkpoint_count " +
            ") " +
        "FROM " +
            "job_stat " +
         "WHERE " +
             "pk_job=?";

    @Override
    public boolean isJobComplete(JobInterface job) {
        if (isLaunching(job)) {
            return false;
        }
        return getJdbcTemplate().queryForObject(IS_JOB_COMPLETE,
                Integer.class, job.getJobId()) == 0;
    }

    public static final String GET_JOB=
        "SELECT " +
            "job.pk_job, "+
            "job.pk_show, "+
            "job.pk_dept,"+
            "job.pk_facility,"+
            "job.str_name " +
        "FROM " +
            "job ";

    private static final String GET_JOB_DETAIL =
         "SELECT " +
             "job.pk_job,"+
             "job.pk_show,"+
             "job.pk_facility,"+
             "job.pk_dept,"+
             "job.pk_folder,"+
             "job.str_log_dir,"+
             "job.str_name,"+
             "job.str_shot,"+
             "job.str_state,"+
             "job.int_uid,"+
             "job.str_user,"+
             "job.str_email,"+
             "job.int_frame_count,"+
             "job.int_layer_count,"+
             "job.ts_started,"+
             "job.ts_stopped,"+
             "job.b_paused,"+
             "job.int_max_retries,"+
             "job_resource.int_max_cores,"+
             "job_resource.int_min_cores,"+
             "job_resource.int_max_gpus,"+
             "job_resource.int_min_gpus,"+
             "job_resource.int_priority,"+
             "show.str_name AS show_name, " +
             "dept.str_name AS dept_name, "+
             "facility.str_name AS facility_name "+
         "FROM " +
             "job, " +
             "job_resource, "+
             "show, " +
             "dept, "+
             "facility "+
         "WHERE " +
             "job.pk_job = job_resource.pk_job " +
         "AND " +
             "job.pk_show = show.pk_show " +
         "AND " +
             "job.pk_dept = dept.pk_dept " +
         "AND " +
             "job.pk_facility = facility.pk_facility ";

    private static final String GET_JOB_BY_ID =
        GET_JOB_DETAIL + "AND job.pk_job=?";

    private static final String FIND_JOB_BY_NAME =
        GET_JOB_DETAIL + "AND job.str_visible_name=? ";

    @Override
    public JobDetail getJobDetail(String id) {
        return getJdbcTemplate().queryForObject(
                GET_JOB_BY_ID, JOB_DETAIL_MAPPER, id);
    }

    @Override
    public JobDetail findLastJob(String name) {
        Matcher matcher = LAST_JOB_STRIP_PATTERN.matcher(name);
        name = matcher.replaceAll("%");

        return getJdbcTemplate().queryForObject(
                GET_JOB_DETAIL + " AND job.str_state = 'FINISHED' AND job.str_name LIKE ? " +
                    "ORDER BY job.ts_stopped LIMIT 1", JOB_DETAIL_MAPPER, name);
    }

    @Override
    public JobInterface getJob(String id) {
        return getJdbcTemplate().queryForObject(
                GET_JOB + " WHERE pk_job=?", JOB_MAPPER, id);
    }


    public static final String GET_JOBS_BY_TASK =
        "SELECT " +
            "job.pk_job, " +
            "job.pk_show, " +
            "job.pk_dept, " +
            "job.pk_facility, " +
            "job.str_name " +
        "FROM " +
            "job," +
            "folder " +
        "WHERE " +
            "job.pk_folder = folder.pk_folder " +
        "AND " +
            "folder.b_exclude_managed = false " +
        "AND " +
            "job.str_state = ? " +
        "AND " +
            "job.pk_dept = ? " +
        "AND " +
            "job.str_shot = ? " +
        "ORDER BY "+
            "ts_started ASC ";

    @Override
    public List<JobInterface> getJobs(TaskEntity t) {
        return getJdbcTemplate().query(GET_JOBS_BY_TASK,
                JOB_MAPPER, JobState.PENDING.toString(), t.deptId, t.shot);
    }

    @Override
    public JobDetail findJobDetail(String name) {
        return getJdbcTemplate().queryForObject(
                FIND_JOB_BY_NAME, JOB_DETAIL_MAPPER, name);
    }

    @Override
    public JobInterface findJob(String name) {
        return getJdbcTemplate().queryForObject(
                GET_JOB + " WHERE job.str_visible_name=?", JOB_MAPPER, name);
    }

    @Override
    public List<JobDetail> findJobs(ShowInterface show) {
        return getJdbcTemplate().query(
                GET_JOB_DETAIL + " AND job.pk_show=?", JOB_DETAIL_MAPPER, show.getShowId());
    }

    @Override
    public List<JobDetail> findJobs(GroupInterface group) {
        return getJdbcTemplate().query(
                GET_JOB_DETAIL + " AND job.pk_folder=?", JOB_DETAIL_MAPPER, group.getId());
    }

    @Override
    public void deleteJob(JobInterface j) {
        /* See trigger before_delete_job */
        getJdbcTemplate().update("DELETE FROM job WHERE pk_job=?", j.getId());
    }

    @Override
    public void updatePriority(JobInterface j, int v) {
        getJdbcTemplate().update("UPDATE job_resource SET int_priority=? WHERE pk_job=?",
                v, j.getJobId());
    }

    @Override
    public void updatePriority(GroupInterface g, int v) {
        getJdbcTemplate().update("UPDATE job_resource SET int_priority=? WHERE " +
                "pk_job IN (SELECT pk_job FROM job WHERE job.pk_folder=?)",
                v, g.getGroupId());
    }

    @Override
    public void updateMinCores(GroupInterface g, int v) {
        getJdbcTemplate().update("UPDATE job_resource SET int_min_cores=? WHERE " +
                "pk_job IN (SELECT pk_job FROM job WHERE pk_folder=?)",
                v, g.getGroupId());
    }

    @Override
    public void updateMaxCores(GroupInterface g, int v) {
        getJdbcTemplate().update("UPDATE job_resource SET int_max_cores=? WHERE " +
                "pk_job IN (SELECT pk_job FROM job WHERE pk_folder=?)",
                v, g.getGroupId());
    }

    @Override
    public void updateMinCores(JobInterface j, int v) {
        getJdbcTemplate().update("UPDATE job_resource SET int_min_cores=? WHERE pk_job=?",
                v, j.getJobId());
    }

    @Override
    public void updateMaxCores(JobInterface j, int v) {
        getJdbcTemplate().update("UPDATE job_resource SET int_max_cores=? WHERE pk_job=?",
                v, j.getJobId());
    }

    @Override
    public void updateMinGpus(GroupInterface g, int v) {
        getJdbcTemplate().update("UPDATE job_resource SET int_min_gpus=? WHERE " +
                "pk_job IN (SELECT pk_job FROM job WHERE pk_folder=?)",
                v, g.getGroupId());
    }

    @Override
    public void updateMaxGpus(GroupInterface g, int v) {
        getJdbcTemplate().update("UPDATE job_resource SET int_max_gpus=? WHERE " +
                "pk_job IN (SELECT pk_job FROM job WHERE pk_folder=?)",
                v, g.getGroupId());
    }

    @Override
    public void updateMinGpus(JobInterface j, int v) {
        getJdbcTemplate().update("UPDATE job_resource SET int_min_gpus=? WHERE pk_job=?",
                v, j.getJobId());
    }

    @Override
    public void updateMaxGpus(JobInterface j, int v) {
        getJdbcTemplate().update("UPDATE job_resource SET int_max_gpus=? WHERE pk_job=?",
                v, j.getJobId());
    }

    @Override
    public void updatePaused(JobInterface j, boolean b) {
        getJdbcTemplate().update("UPDATE job SET b_paused=? WHERE pk_job=?",
                b, j.getJobId());
    }

    @Override
    public void updateAutoEat(JobInterface j, boolean b) {
        int maxRetries = 1;
        if (b) {
            maxRetries = 0;
        }
        getJdbcTemplate().update("UPDATE job SET b_autoeat=?, int_max_retries=? WHERE pk_job=?",
                b, maxRetries, j.getJobId());
    }

    @Override
    public void updateState(JobInterface job, JobState state) {
        getJdbcTemplate().update("UPDATE job SET str_state=? WHERE pk_job=?",
                state.toString(), job.getJobId());
    }

    @Override
    public void updateLogPath(JobInterface job, String path) {
        getJdbcTemplate().update("UPDATE job SET str_log_dir=? WHERE pk_job=?",
                path, job.getJobId());
    }

    @Override
    public void updateMaxRSS(JobInterface job, long value) {
        getJdbcTemplate().update(
                "UPDATE job_mem SET int_max_rss=? WHERE pk_job=? AND int_max_rss < ?",
                value, job.getJobId(), value);
    }

    private static final String UPDATE_JOB_FINISHED =
        "UPDATE " +
            "job " +
        "SET " +
            "str_state = ?, "+
            "str_visible_name = NULL, " +
            "ts_stopped = current_timestamp "+
        "WHERE " +
            "str_state = 'PENDING'" +
        "AND " +
            "pk_job = ?";

    @Override
    public boolean updateJobFinished(JobInterface job) {
        // Only return true if this thread was the one who actually
        // set the job state to finished.
        if(getJdbcTemplate().update(UPDATE_JOB_FINISHED,
                JobState.FINISHED.toString(), job.getJobId()) == 1) {
            return true;
        }
        return false;
    }

    private static final String INSERT_JOB =
        "INSERT INTO " +
        "job " +
        "(" +
            "pk_job," +
            "pk_show," +
            "pk_folder,"+
            "pk_facility,"+
            "pk_dept,"+
            "str_name," +
            "str_visible_name,"+
            "str_show,"+
            "str_shot," +
            "str_user," +
            "str_email,"+
            "str_state," +
            "str_log_dir," +
            "str_os, "+
            "int_uid," +
            "b_paused," +
            "b_autoeat,"+
            "int_max_retries " +
        ") " +
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)";

    @Override
    public void insertJob(JobDetail j, JobLogUtil jobLogUtil) {
        j.id = SqlUtil.genKeyRandom();
        j.logDir = jobLogUtil.getJobLogPath(j);
        if (j.minCoreUnits < 100) { j.minCoreUnits = 100; }

        getJdbcTemplate().update(INSERT_JOB,
                j.id, j.showId, j.groupId, j.facilityId, j.deptId,
                j.name, j.name, j.showName, j.shot, j.user, j.email, j.state.toString(),
                j.logDir, j.os, j.uid.orElse(null), j.isPaused, j.isAutoEat, j.maxRetries);
    }

    private static final String JOB_EXISTS =
        "SELECT " +
            "1 " +
        "FROM " +
            "job " +
        "WHERE " +
            "str_name = ? " +
        "AND " +
            "str_state='PENDING' " +
        "LIMIT 1";

    @Override
    public boolean exists(String name) {
        try {
            return (getJdbcTemplate().queryForObject(JOB_EXISTS,
                    Integer.class, name) >= 1);
        } catch (Exception e) {
            return false;
        }
    }

    private static final String IS_LAUNCHING =
        "SELECT " +
            "str_state " +
        "FROM " +
            "job " +
        "WHERE " +
            "pk_job=?";

    @Override
    public boolean isLaunching(JobInterface j) {
        return getJdbcTemplate().queryForObject(
                IS_LAUNCHING, String.class, j.getJobId()).equals(
                    JobState.STARTUP.toString());
    }

    @Override
    public void activateJob(JobInterface job, JobState jobState) {

        Long[] jobTotals = { 0L, 0L };  // Depend, Waiting

        /*
         * Sets all frames in the setup state to Waiting. Frames with a depend
         * count > 0 are automatically updated to Depend via the
         * update_frame_wait_to_dep trigger.
         */
        getJdbcTemplate().update("UPDATE frame SET str_state=? WHERE pk_job=? AND str_state=?",
                FrameState.WAITING.toString(), job.getId(), FrameState.SETUP.toString());

        List<Map<String,Object>> layers = getJdbcTemplate().queryForList(
                "SELECT pk_layer, str_state, count(1) AS c FROM frame " +
                "WHERE pk_job=? GROUP BY pk_layer, str_state", job.getId());

        for (Map<String,Object> row: layers) {
            String layer = (String) row.get("pk_layer");
            FrameState state = FrameState.valueOf((String) row.get("str_state"));
            Long count = (Long) row.get("c");

            if (count == 0 || state == null) { continue; }

            switch (state) {
                case DEPEND:
                    jobTotals[0] =  jobTotals[0] + count;
                    getJdbcTemplate().update(
                            "UPDATE layer_stat SET int_depend_count=?,int_total_count=int_total_count + ? WHERE pk_layer=?",
                            count, count, layer);
                    break;
                case WAITING:
                    jobTotals[1] =  jobTotals[1] + count;
                    getJdbcTemplate().update(
                            "UPDATE layer_stat SET int_waiting_count=?,int_total_count=int_total_count + ? WHERE pk_layer=?",
                            count, count, layer);
                    break;
            }
        }

        getJdbcTemplate().update(
                "UPDATE job_stat SET int_depend_count=?,int_waiting_count=? WHERE pk_job=?",
                jobTotals[0], jobTotals[1], job.getJobId());

        getJdbcTemplate().update(
                "UPDATE job SET int_frame_count=?, int_layer_count=? WHERE pk_job=?",
                jobTotals[0] + jobTotals[1], layers.size(), job.getJobId());

        getJdbcTemplate().update(
                "UPDATE show SET int_frame_insert_count=int_frame_insert_count+?, int_job_insert_count=int_job_insert_count+1 WHERE pk_show=?",
                jobTotals[0] + jobTotals[1], job.getShowId());

        updateState(job, jobState);
    }

    private static final String HAS_PENDING_FRAMES =
        "SELECT " +
            "int_waiting_count " +
        "FROM " +
            "job,"+
            "job_stat " +
        "WHERE " +
            "job.pk_job = job_stat.pk_job " +
        "AND " +
            "job.str_state = 'PENDING' " +
        "AND " +
            "job.b_paused = false " +
        "AND " +
            "job.b_auto_book = true " +
        "AND " +
            "job.pk_job = ?";

    @Override
    public boolean hasPendingFrames(JobInterface job) {
        try {
            return getJdbcTemplate().queryForObject(HAS_PENDING_FRAMES,
                    Integer.class, job.getJobId()) > 0;
        } catch (DataAccessException e) {
            return false;
        }
    }

    private static final String IS_JOB_OVER_MIN_CORES =
        "SELECT " +
            "COUNT(1) " +
        "FROM " +
            "job_resource " +
        "WHERE " +
            "job_resource.pk_job = ? " +
        "AND " +
            "job_resource.int_cores > job_resource.int_min_cores";

    @Override
    public boolean isOverMinCores(JobInterface job) {
        return getJdbcTemplate().queryForObject(IS_JOB_OVER_MIN_CORES,
                Integer.class, job.getJobId()) > 0;
    }

    private static final String IS_JOB_OVER_MAX_CORES =
        "SELECT " +
            "COUNT(1) " +
        "FROM " +
            "job_resource " +
        "WHERE " +
            "job_resource.pk_job = ? " +
        "AND " +
            "job_resource.int_cores + ? > job_resource.int_max_cores";

    @Override
    public boolean isOverMaxCores(JobInterface job) {
        return getJdbcTemplate().queryForObject(IS_JOB_OVER_MAX_CORES,
                Integer.class, job.getJobId(), 0) > 0;
    }

    @Override
    public boolean isOverMaxCores(JobInterface job, int coreUnits) {
        return getJdbcTemplate().queryForObject(IS_JOB_OVER_MAX_CORES,
                Integer.class, job.getJobId(), coreUnits) > 0;
    }


    private static final String IS_JOB_AT_MAX_CORES =
        "SELECT " +
            "COUNT(1) " +
        "FROM " +
            "job_resource " +
        "WHERE " +
            "job_resource.pk_job = ? " +
        "AND " +
            "job_resource.int_cores >= job_resource.int_max_cores ";

    @Override
    public boolean isAtMaxCores(JobInterface job) {
        return getJdbcTemplate().queryForObject(IS_JOB_AT_MAX_CORES,
                Integer.class, job.getJobId()) > 0;
    }

    private static final String IS_JOB_OVER_MAX_GPUS =
        "SELECT " +
            "COUNT(1) " +
        "FROM " +
            "job_resource " +
        "WHERE " +
            "job_resource.pk_job = ? " +
        "AND " +
            "job_resource.int_gpus + ? > job_resource.int_max_gpus";

    @Override
    public boolean isOverMaxGpus(JobInterface job) {
        return getJdbcTemplate().queryForObject(IS_JOB_OVER_MAX_GPUS,
                Integer.class, job.getJobId(), 0) > 0;
    }

    @Override
    public boolean isOverMaxGpus(JobInterface job, int gpu) {
        return getJdbcTemplate().queryForObject(IS_JOB_OVER_MAX_GPUS,
                Integer.class, job.getJobId(), gpu) > 0;
    }

    private static final String IS_JOB_AT_MAX_GPUS =
        "SELECT " +
            "COUNT(1) " +
        "FROM " +
            "job_resource " +
        "WHERE " +
            "job_resource.pk_job = ? " +
        "AND " +
            "job_resource.int_gpus >= job_resource.int_max_gpus ";

    @Override
    public boolean isAtMaxGpus(JobInterface job) {
        return getJdbcTemplate().queryForObject(IS_JOB_AT_MAX_GPUS,
                Integer.class, job.getJobId()) > 0;
    }

    @Override
    public void updateMaxFrameRetries(JobInterface j, int max_retries) {
        if (max_retries < 0) {
            throw new IllegalArgumentException("max retries must be greater than 0");
        }

        int max_max_retries = getJdbcTemplate().queryForObject(
                "SELECT int_value FROM config WHERE str_key=?",
                Integer.class, "MAX_FRAME_RETRIES");

        if (max_retries > max_max_retries) {
            throw new IllegalArgumentException("max retries must be less than "
                    + max_max_retries);
        }

        getJdbcTemplate().update(
                "UPDATE job SET int_max_retries=? WHERE pk_job=?",
                max_retries, j.getJobId());
    }

    private static final String GET_FRAME_STATE_TOTALS =
        "SELECT " +
            "job.int_frame_count," +
            "job_stat.* " +
        "FROM " +
            "job," +
            "job_stat " +
        "WHERE " +
            "job.pk_job = job_stat.pk_job " +
        "AND " +
            "job.pk_job=?";

    public FrameStateTotals getFrameStateTotals(JobInterface job) {
        return getJdbcTemplate().queryForObject(
                GET_FRAME_STATE_TOTALS,
                new RowMapper<FrameStateTotals>() {
                    public FrameStateTotals mapRow(ResultSet rs, int rowNum) throws SQLException {
                        FrameStateTotals t = new FrameStateTotals();
                        t.dead = rs.getInt("int_dead_count");
                        t.depend = rs.getInt("int_depend_count");
                        t.eaten = rs.getInt("int_eaten_count");
                        t.running = rs.getInt("int_running_count");
                        t.succeeded = rs.getInt("int_succeeded_count");
                        t.waiting = rs.getInt("int_waiting_count");
                        t.total = rs.getInt("int_frame_count");
                        return t;
                    }
                },job.getJobId());
    }

    private static final String GET_EXECUTION_SUMMARY =
        "SELECT " +
            "job_usage.int_core_time_success,"+
            "job_usage.int_core_time_fail,"+
            "job_usage.int_gpu_time_success,"+
            "job_usage.int_gpu_time_fail,"+
            "job_mem.int_max_rss " +
        "FROM " +
            "job," +
            "job_usage, "+
            "job_mem " +
        "WHERE " +
            "job.pk_job = job_usage.pk_job "+
        "AND " +
            "job.pk_job = job_mem.pk_job " +
        "AND " +
            "job.pk_job = ?";

    public ExecutionSummary getExecutionSummary(JobInterface job) {
        return getJdbcTemplate().queryForObject(
                GET_EXECUTION_SUMMARY,
                new RowMapper<ExecutionSummary>() {
                    public ExecutionSummary mapRow(ResultSet rs, int rowNum) throws SQLException {
                        ExecutionSummary e = new ExecutionSummary();
                        e.coreTimeSuccess = rs.getLong("int_core_time_success");
                        e.coreTimeFail = rs.getLong("int_core_time_fail");
                        e.coreTime = e.coreTimeSuccess + e.coreTimeFail;
                        e.gpuTimeSuccess = rs.getLong("int_gpu_time_success");
                        e.gpuTimeFail = rs.getLong("int_gpu_time_fail");
                        e.gpuTime = e.gpuTimeSuccess + e.gpuTimeFail;
                        e.highMemoryKb = rs.getLong("int_max_rss");

                        return e;
                    }
                }, job.getJobId());
    }

    private static final String INSERT_JOB_ENV =
        "INSERT INTO " +
            "job_env " +
        "(" +
            "pk_job_env, pk_job, str_key, str_value " +
        ") " +
        "VALUES (?,?,?,?)";

    @Override
    public void insertEnvironment(JobInterface job, Map<String,String> env) {
        for (Map.Entry<String,String> e: env.entrySet()) {
            String pk = SqlUtil.genKeyRandom();
            getJdbcTemplate().update(INSERT_JOB_ENV,
                    pk, job.getJobId(), e.getKey(), e.getValue());
        }
    }

    @Override
    public void insertEnvironment(JobInterface job, String key, String value) {
        String pk = SqlUtil.genKeyRandom();
        getJdbcTemplate().update(INSERT_JOB_ENV,
                pk, job.getJobId(), key, value);
    }

    @Override
    public Map<String,String> getEnvironment(JobInterface job) {
        Map<String,String> result = new HashMap<String,String>();

        List<Map<String, Object>> _result = getJdbcTemplate().queryForList(
                "SELECT str_key, str_value FROM job_env WHERE pk_job=?", job.getJobId());

        for (Map<String,Object> o: _result) {
            result.put((String) o.get("str_key"), (String) o.get("str_value"));
        }

        return result;
    }

    @Override
    public void updateParent(JobInterface job, GroupDetail dest) {
        updateParent(job, dest, new Inherit[] { Inherit.All });
    }

    @Override
    public void updateParent(JobInterface job, GroupDetail dest, Inherit[] inherits) {

        if (!job.getShowId().equals(dest.getShowId())) {
            throw new EntityModificationError("error moving job, " +
                "cannot move jobs between shows");
        }

        StringBuilder query = new StringBuilder(1024);
        query.append("UPDATE job_resource SET ");
        List<Object> values= new ArrayList<Object>();

        Set<Inherit> inheritSet = new HashSet<Inherit>(inherits.length);
        inheritSet.addAll(Arrays.asList(inherits));

        for (Inherit i: inheritSet) {
            switch(i) {
                case Priority:
                    if (dest.jobPriority != CueUtil.FEATURE_DISABLED) {
                        query.append("int_priority=?,");
                        values.add(dest.jobPriority);
                    }
                    break;

                case MinCores:
                    if (dest.jobMinCores != CueUtil.FEATURE_DISABLED) {
                        query.append("int_min_cores=?,");
                        values.add(dest.jobMinCores);
                    }
                    break;

                case MaxCores:
                    if (dest.jobMaxCores != CueUtil.FEATURE_DISABLED) {
                        query.append("int_max_cores=?,");
                        values.add(dest.jobMaxCores);
                    }
                    break;

                case MinGpus:
                    if (dest.jobMinGpus != CueUtil.FEATURE_DISABLED) {
                        query.append("int_min_gpus=?,");
                        values.add(dest.jobMinGpus);
                    }
                    break;

                case MaxGpus:
                    if (dest.jobMaxGpus != CueUtil.FEATURE_DISABLED) {
                        query.append("int_max_gpus=?,");
                        values.add(dest.jobMaxGpus);
                    }
                    break;

                case All:
                    if (dest.jobPriority != CueUtil.FEATURE_DISABLED) {
                        query.append("int_priority=?,");
                        values.add(dest.jobPriority);
                    }

                    if (dest.jobMinCores != CueUtil.FEATURE_DISABLED) {
                        query.append("int_min_cores=?,");
                        values.add(dest.jobMinCores);
                    }

                    if (dest.jobMaxCores != CueUtil.FEATURE_DISABLED) {
                        query.append("int_max_cores=?,");
                        values.add(dest.jobMaxCores);
                    }

                    if (dest.jobMinGpus != CueUtil.FEATURE_DISABLED) {
                        query.append("int_min_gpus=?,");
                        values.add(dest.jobMinGpus);
                    }

                    if (dest.jobMaxGpus != CueUtil.FEATURE_DISABLED) {
                        query.append("int_max_gpus=?,");
                        values.add(dest.jobMaxGpus);
                    }
                    break;
            }
        }

        getJdbcTemplate().update(
                "UPDATE job SET pk_folder=?, pk_dept=? WHERE pk_job=?",
                dest.getGroupId(), dest.getDepartmentId(), job.getJobId());

        getJdbcTemplate().update(
                "UPDATE job_history SET pk_dept=? WHERE pk_job=?",
                dest.getDepartmentId(), job.getJobId());

        if (values.size() > 0) {
            query.deleteCharAt(query.length()-1);
            query.append(" WHERE pk_job=?");
            values.add(job.getJobId());
            getJdbcTemplate().update(query.toString(), values.toArray());
        }
    }

    private static final String HAS_PENDING_JOBS =
        "SELECT " +
            "job.pk_job " +
        "FROM " +
            "job, " +
            "job_stat, " +
            "job_resource " +
        "WHERE " +
            "job.pk_job = job_stat.pk_job " +
        "AND " +
            "job.pk_job = job_resource.pk_job " +
        "AND " +
            "job.str_state = 'PENDING' " +
        "AND " +
            "job.b_paused = false " +
        "AND " +
            "job.b_auto_book = true " +
        "AND " +
            "job_stat.int_waiting_count != 0 " +
        "AND " +
            "job_resource.int_cores < job_resource.int_max_cores " +
        "AND " +
            "job_resource.int_gpus < job_resource.int_max_gpus " +
        "AND " +
            "job.pk_facility = ? " +
        "LIMIT 1";

    @Override
    public boolean cueHasPendingJobs(FacilityInterface f) {
        return getJdbcTemplate().queryForList(
                HAS_PENDING_JOBS, f.getFacilityId()).size() > 0;
    }

    @Override
    public void enableAutoBooking(JobInterface job, boolean value) {
        getJdbcTemplate().update(
                "UPDATE job SET b_auto_book=? WHERE pk_job=?", value, job.getJobId());
    }

    @Override
    public void enableAutoUnBooking(JobInterface job, boolean value) {
        getJdbcTemplate().update(
                "UPDATE job SET b_auto_unbook=? WHERE pk_job=?", value, job.getJobId());
    }

    public static final String MAP_POST_JOB =
        "INSERT INTO " +
            "job_post " +
        "(pk_job_post, pk_job, pk_post_job) " +
        "VALUES (?,?,?)";

    @Override
    public void mapPostJob(BuildableJob job) {
        getJdbcTemplate().update(MAP_POST_JOB,
                SqlUtil.genKeyRandom(), job.detail.id, job.getPostJob().detail.id);
    }

    public static final String ACTIVATE_POST_JOB =
        "UPDATE " +
            "job " +
        "SET " +
            "str_state=? " +
        "WHERE " +
            "pk_job IN (SELECT pk_post_job FROM job_post WHERE pk_job = ?)";

    @Override
    public void activatePostJob(JobInterface job) {
        getJdbcTemplate().update(ACTIVATE_POST_JOB,
                JobState.PENDING.toString(), job.getJobId());
        getJdbcTemplate().update("DELETE FROM job_post WHERE pk_job=?",job.getJobId());
    }

    @Override
    public void updateDepartment(GroupInterface group, DepartmentInterface dept) {
        getJdbcTemplate().update("UPDATE job SET pk_dept=? WHERE pk_folder=?",
                dept.getDepartmentId(), group.getGroupId());
    }

    @Override
    public void updateDepartment(JobInterface job, DepartmentInterface dept) {
        getJdbcTemplate().update("UPDATE job SET pk_dept=? WHERE pk_job=?",
                dept.getDepartmentId(), job.getJobId());
    }


    public void updateUsage(JobInterface job, ResourceUsage usage, int exitStatus) {

        if (exitStatus == 0) {

            getJdbcTemplate().update(
                    "UPDATE " +
                        "job_usage " +
                    "SET " +
                        "int_core_time_success = int_core_time_success + ?," +
                        "int_gpu_time_success = int_gpu_time_success + ?," +
                        "int_clock_time_success = int_clock_time_success + ?,"+
                        "int_frame_success_count = int_frame_success_count + 1 " +
                    "WHERE " +
                        "pk_job = ? ",
                        usage.getCoreTimeSeconds(),
                        usage.getGpuTimeSeconds(),
                        usage.getClockTimeSeconds(),
                        job.getJobId());

            getJdbcTemplate().update(
                    "UPDATE " +
                        "job_usage " +
                    "SET " +
                        "int_clock_time_high = ? " +
                    "WHERE " +
                        "pk_job = ? " +
                    "AND " +
                        "int_clock_time_high < ?",
                    usage.getClockTimeSeconds(),
                    job.getJobId(),
                    usage.getClockTimeSeconds());
        }
        else {

            getJdbcTemplate().update(
                    "UPDATE " +
                        "job_usage " +
                    "SET " +
                        "int_core_time_fail = int_core_time_fail + ?," +
                        "int_clock_time_fail = int_clock_time_fail + ?,"+
                        "int_frame_fail_count = int_frame_fail_count + 1 " +
                    "WHERE " +
                        "pk_job = ? ",
                        usage.getCoreTimeSeconds(),
                        usage.getClockTimeSeconds(),
                        job.getJobId());
        }
    }

    public void updateEmail(JobInterface job, String email) {
        getJdbcTemplate().update(
                "UPDATE job SET str_email=? WHERE pk_job=?",
                email, job.getJobId());
    }
}

