
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
import java.util.Calendar;
import java.util.List;

import com.imageworks.spcue.dao.AbstractJdbcDao;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.dao.BookingDao;
import com.imageworks.spcue.dispatcher.ResourceReservationFailureException;
import com.imageworks.spcue.grpc.renderpartition.RenderPartitionType;
import com.imageworks.spcue.util.SqlUtil;
import org.springframework.stereotype.Repository;

import javax.annotation.PostConstruct;
import javax.sql.DataSource;

@Repository
public class BookingDaoJdbc extends
        AbstractJdbcDao implements BookingDao {

    private static final String INSERT_LOCAL_JOB_ASSIGNMENT =
        "INSERT INTO " +
            "host_local " +
        "(" +
            "pk_host_local,"+
            "pk_job,"+
            "pk_layer,"+
            "pk_frame,"+
            "str_type,"+
            "pk_host,"+
            "int_mem_max,"+
            "int_mem_idle,"+
            "int_cores_max,"+
            "int_cores_idle,"+
            "int_gpu_idle,"+
            "int_gpu_max,"+
            "int_threads "+
        ") " +
        "VALUES " +
            "(?,?,?,?,?,?,?,?,?,?,?,?,?)";

    @Override
    public void insertLocalHostAssignment(HostInterface h, JobInterface job, LocalHostAssignment l) {
        l.id = SqlUtil.genKeyRandom();
        l.name = String.format("%s->%s", h.getName(), job.getName());
        l.setHostId(h.getHostId());
        l.setJobId(job.getJobId());
        l.setType(RenderPartitionType.JOB_PARTITION);
        l.setIdleCoreUnits(l.getMaxCoreUnits());
        l.setIdleMemory(l.getMaxMemory());
        l.setIdleGpu(l.getMaxGpu());

        getJdbcTemplate().update(
                INSERT_LOCAL_JOB_ASSIGNMENT,
                l.id,
                job.getJobId(),
                l.getLayerId(),
                l.getFrameId(),
                l.getType().toString(),
                h.getHostId(),
                l.getMaxMemory(),
                l.getMaxMemory(),
                l.getMaxCoreUnits(),
                l.getMaxCoreUnits(),
                l.getMaxGpu(),
                l.getMaxGpu(),
                l.getThreads());
    }

    @Override
    public void insertLocalHostAssignment(HostInterface h, LayerInterface layer, LocalHostAssignment l) {
        l.id = SqlUtil.genKeyRandom();
        l.name = String.format("%s->%s", h.getName(), layer.getName());
        l.setHostId(h.getHostId());
        l.setJobId(layer.getJobId());
        l.setLayerId(layer.getLayerId());
        l.setType(RenderPartitionType.LAYER_PARTITION);
        l.setIdleCoreUnits(l.getMaxCoreUnits());
        l.setIdleMemory(l.getMaxMemory());
        l.setIdleGpu(l.getMaxGpu());

        getJdbcTemplate().update(
                INSERT_LOCAL_JOB_ASSIGNMENT,
                l.id,
                l.getJobId(),
                l.getLayerId(),
                l.getFrameId(),
                l.getType().toString(),
                h.getHostId(),
                l.getMaxMemory(),
                l.getMaxMemory(),
                l.getMaxCoreUnits(),
                l.getMaxCoreUnits(),
                l.getMaxGpu(),
                l.getMaxGpu(),
                l.getThreads());
    }

    @Override
    public void insertLocalHostAssignment(HostInterface h, FrameInterface frame, LocalHostAssignment l) {
        l.id = SqlUtil.genKeyRandom();
        l.name = String.format("%s->%s", h.getName(), frame.getName());
        l.setHostId(h.getHostId());
        l.setJobId(frame.getJobId());
        l.setLayerId(frame.getLayerId());
        l.setFrameId(frame.getFrameId());
        l.setType(RenderPartitionType.FRAME_PARTITION);
        l.setIdleCoreUnits(l.getMaxCoreUnits());
        l.setIdleMemory(l.getMaxMemory());
        l.setIdleGpu(l.getMaxGpu());

        getJdbcTemplate().update(
                INSERT_LOCAL_JOB_ASSIGNMENT,
                l.id,
                l.getJobId(),
                l.getLayerId(),
                l.getFrameId(),
                l.getType().toString(),
                h.getHostId(),
                l.getMaxMemory(),
                l.getMaxMemory(),
                l.getMaxCoreUnits(),
                l.getMaxCoreUnits(),
                l.getMaxGpu(),
                l.getMaxGpu(),
                l.getThreads());
    }
    public static final RowMapper<LocalHostAssignment> LJA_MAPPER =
        new RowMapper<LocalHostAssignment>() {
        public LocalHostAssignment mapRow(final ResultSet rs, int rowNum) throws SQLException {
            LocalHostAssignment l = new LocalHostAssignment();
            l.id = rs.getString("pk_host_local");
            l.setMaxCoreUnits(rs.getInt("int_cores_max"));
            l.setMaxMemory(rs.getLong("int_mem_max"));
            l.setMaxGpu(rs.getLong("int_gpu_max"));
            l.setThreads(rs.getInt("int_threads"));
            l.setIdleCoreUnits(rs.getInt("int_cores_idle"));
            l.setIdleMemory(rs.getLong("int_mem_idle"));
            l.setIdleGpu(rs.getLong("int_gpu_idle"));
            l.setJobId(rs.getString("pk_job"));
            l.setLayerId(rs.getString("pk_layer"));
            l.setFrameId(rs.getString("pk_frame"));
            l.setHostId(rs.getString("pk_host"));
            l.setType(RenderPartitionType.valueOf(rs.getString("str_type")));
            return l;
        }
    };

    private static final String QUERY_FOR_LJA =
        "SELECT " +
            "pk_host_local,"+
            "pk_job,"+
            "pk_layer," +
            "pk_frame,"+
            "pk_host,"+
            "int_mem_idle,"+
            "int_mem_max,"+
            "int_cores_idle,"+
            "int_cores_max,"+
            "int_gpu_idle,"+
            "int_gpu_max,"+
            "int_threads, "+
            "str_type " +
        "FROM " +
            "host_local ";

    @Override
    public List<LocalHostAssignment> getLocalJobAssignment(HostInterface host) {
        return getJdbcTemplate().query(
                QUERY_FOR_LJA +
                "WHERE " +
                    "host_local.pk_host = ? ",
                LJA_MAPPER, host.getHostId());
    }

    @Override
    public LocalHostAssignment getLocalJobAssignment(String id) {
        return getJdbcTemplate().queryForObject(
                QUERY_FOR_LJA + " WHERE pk_host_local = ?",
                LJA_MAPPER, id);
    }

    @Override
    public LocalHostAssignment getLocalJobAssignment(String hostId, String jobId) {
        return getJdbcTemplate().queryForObject(
                QUERY_FOR_LJA + " WHERE pk_host = ? and pk_job = ?",
                LJA_MAPPER, hostId, jobId);
    }

    @Override
    public boolean deleteLocalJobAssignment(LocalHostAssignment l) {
        return getJdbcTemplate().update(
                "DELETE FROM host_local WHERE pk_host_local = ?",
                l.getId()) > 0;
    }

    private static final String HAS_LOCAL_JOB =
        "SELECT " +
            "COUNT(1) " +
        "FROM " +
            "host_local " +
        "WHERE " +
            "host_local.pk_host = ? ";

    @Override
    public boolean hasLocalJob(HostInterface host) {
        return getJdbcTemplate().queryForObject(HAS_LOCAL_JOB,
                Integer.class, host.getHostId()) > 0;
    }

    private static final String HAS_ACTIVE_LOCAL_JOB =
        "SELECT " +
            "COUNT(1) " +
        "FROM " +
            "host_local, " +
            "proc " +
        "WHERE " +
            "host_local.pk_host = proc.pk_host " +
        "AND " +
            "proc.b_local = true " +
        "AND " +
            "host_local.pk_host = ? ";

    @Override
    public boolean hasActiveLocalJob(HostInterface host) {
        return getJdbcTemplate().queryForObject(HAS_ACTIVE_LOCAL_JOB,
                Integer.class, host.getHostId()) > 0;
    }

    private static final String IS_BLACKOUT_TIME =
        "SELECT " +
            "int_blackout_start,"+
            "int_blackout_duration " +
        "FROM " +
            "host,"+
            "deed "+
        "WHERE " +
            "host.pk_host = deed.pk_host " +
        "AND " +
            "deed.b_blackout = true " +
        "AND " +
            "host.pk_host = ? ";

    public static final RowMapper<Boolean> BLACKOUT_MAPPER =
        new RowMapper<Boolean>() {
        public Boolean mapRow(final ResultSet rs, int rowNum) throws SQLException {

            int startTimeSeconds = rs.getInt("int_backout_start");
            int stopTimeSeconds = rs.getInt("int_blackout_stop");
            if (stopTimeSeconds <= startTimeSeconds) {
                stopTimeSeconds = stopTimeSeconds + 86400;
            }

            Calendar startTime = Calendar.getInstance();
            startTime.set(Calendar.HOUR_OF_DAY, 0);
            startTime.set(Calendar.MINUTE, 0);
            startTime.set(Calendar.SECOND, 0);
            startTime.add(Calendar.SECOND, startTimeSeconds);

            Calendar stopTime = Calendar.getInstance();
            stopTime.set(Calendar.HOUR_OF_DAY, 0);
            stopTime.set(Calendar.MINUTE, 0);
            stopTime.set(Calendar.SECOND, 0);
            stopTime.add(Calendar.SECOND, stopTimeSeconds);

            Calendar now = Calendar.getInstance();
            if (now.compareTo(startTime) >= 0 && now.compareTo(stopTime) <= 0) {
                return true;
            }

            return false;
        }
    };

    @Override
    public boolean isBlackoutTime(HostInterface h) {
        try {
            return getJdbcTemplate().queryForObject(IS_BLACKOUT_TIME,
                    BLACKOUT_MAPPER, h.getHostId());
        } catch (Exception e) {
            return false;
        }
    }

    @Override
    public int getCoreUsageDifference(LocalHostAssignment l, int coreUnits) {
        return getJdbcTemplate().queryForObject(
                "SELECT ? - int_cores_max  FROM host_local WHERE pk_host_local=?",
                Integer.class, coreUnits, l.getId());
    }

    private static final String UPDATE_MAX_CORES =
        "UPDATE " +
            "host_local " +
        "SET " +
            "int_cores_idle = int_cores_idle + (? - int_cores_max), " +
            "int_cores_max = ? "+
        "WHERE " +
            "pk_host_local = ? ";

    @Override
    public boolean updateMaxCores(LocalHostAssignment l, int coreUnits) {
        return getJdbcTemplate().update(UPDATE_MAX_CORES,
                coreUnits, coreUnits, l.getId()) > 0;
    }

    private static final String UPDATE_MAX_MEMORY =
        "UPDATE " +
            "host_local " +
        "SET " +
            "int_mem_idle = int_mem_idle + (? - int_mem_max), " +
            "int_mem_max = ? "+
        "WHERE " +
            "pk_host_local = ? ";

    @Override
    public boolean updateMaxMemory(LocalHostAssignment l, long maxMemory) {
        return getJdbcTemplate().update(
                UPDATE_MAX_MEMORY, maxMemory, maxMemory, l.getId()) > 0;
    }

    private static final String UPDATE_MAX_GPU =
        "UPDATE " +
            "host_local " +
        "SET " +
            "int_gpu_idle = int_gpu_idle + (? - int_gpu_max), " +
            "int_gpu_max = ? "+
        "WHERE " +
            "pk_host_local = ? ";

    @Override
    public boolean updateMaxGpu(LocalHostAssignment l, long maxGpu) {
        return getJdbcTemplate().update(
                UPDATE_MAX_GPU, maxGpu, maxGpu, l.getId()) > 0;
    }

    @Override
    public boolean deactivate(LocalHostAssignment l) {
        return getJdbcTemplate().update(
                "UPDATE host_local SET b_active = false WHERE " +
                "pk_host_local = ? AND b_active = true",
                l.getId()) > 0;
    }

    /**
     *
     * @param h HostInterface
     * @param cores int
     * @return boolean
     */
    @Override
    public boolean allocateCoresFromHost(HostInterface h, int cores) {

        try {
            return getJdbcTemplate().update(
                    "UPDATE host SET int_cores_idle = int_cores_idle - ? " +
                    "WHERE pk_host = ?",
                    cores, h.getHostId()) > 0;
        } catch (DataAccessException e) {
            throw new ResourceReservationFailureException("Failed to allocate " +
                    cores + " from host, " + e);
        }

    }

    /**
     *
     * @param h HostInterface
     * @param cores int
     * @return boolean
     */
    @Override
    public boolean deallocateCoresFromHost(HostInterface h, int cores) {
        try {
            return getJdbcTemplate().update(
                    "UPDATE host SET int_cores_idle = int_cores_idle + ? WHERE pk_host = ?",
                    cores, h.getHostId()) > 0;
        } catch (DataAccessException e) {
            throw new ResourceReservationFailureException("Failed to de-allocate " +
                    cores + " from host, " + e);
        }
    }

    @Override
    public boolean hasResourceDeficit(HostInterface host) {
        return getJdbcTemplate().queryForObject(
                "SELECT COUNT(1) FROM host_local WHERE " +
                "(int_cores_max < int_cores_max - int_cores_idle OR " +
                "int_gpu_max < int_gpu_max - int_gpu_idle OR " +
                "int_mem_max < int_mem_max - int_mem_idle) AND " +
                "host_local.pk_host= ?",
                Integer.class, host.getHostId()) > 0;
    }
}

