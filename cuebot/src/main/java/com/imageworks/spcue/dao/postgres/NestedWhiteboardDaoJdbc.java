
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
import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import com.imageworks.spcue.dao.AbstractJdbcDao;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.dao.NestedWhiteboardDao;
import com.imageworks.spcue.grpc.host.NestedHost;
import com.imageworks.spcue.grpc.host.NestedHostSeq;
import com.imageworks.spcue.grpc.host.NestedProc;
import com.imageworks.spcue.grpc.job.GroupStats;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.grpc.job.JobStats;
import com.imageworks.spcue.grpc.job.NestedGroup;
import com.imageworks.spcue.grpc.job.NestedGroupSeq;
import com.imageworks.spcue.grpc.job.NestedJob;
import com.imageworks.spcue.util.Convert;
import com.imageworks.spcue.util.CueUtil;
import org.springframework.stereotype.Repository;

@Repository
public class NestedWhiteboardDaoJdbc extends AbstractJdbcDao implements NestedWhiteboardDao {

    private class CachedJobWhiteboardMapper {
        public final long time;
        public NestedJobWhiteboardMapper mapper;

        public CachedJobWhiteboardMapper(NestedJobWhiteboardMapper result) {
            this.mapper = result;
            this.time = System.currentTimeMillis();
        }
    }

    private static final int CACHE_TIMEOUT = 5000;
    private final ConcurrentHashMap<String,CachedJobWhiteboardMapper> jobCache =
        new ConcurrentHashMap<String,CachedJobWhiteboardMapper>(20);

    public static final String GET_NESTED_GROUPS =
        "SELECT " +
            "show.pk_show, " +
            "show.str_name AS str_show, " +
            "facility.str_name AS facility_name, " +
            "folder.pk_folder, " +
            "folder.pk_parent_folder, " +
            "folder.str_name AS group_name, " +
            "folder.int_job_priority as int_def_job_priority, " +
            "folder.int_job_min_cores as int_def_job_min_cores, " +
            "folder.int_job_max_cores as int_def_job_max_cores, " +
            "folder_resource.int_min_cores AS folder_min_cores, " +
            "folder_resource.int_max_cores AS folder_max_cores, " +
            "folder_level.int_level, " +
            "job.pk_job, " +
            "job.str_name, " +
            "job.str_shot, " +
            "job.str_user, " +
            "job.str_state, " +
            "job.str_log_dir, " +
            "job.int_uid, " +
            "job_resource.int_priority, " +
            "job.ts_started, " +
            "job.ts_stopped, " +
            "job.ts_updated, " +
            "job.b_paused, " +
            "job.b_autoeat, " +
            "job.b_comment, " +
            "job.str_os, " +
            "job.int_frame_count, " +
            "job.int_layer_count, " +
            "job_stat.int_waiting_count, " +
            "job_stat.int_running_count, " +
            "job_stat.int_dead_count, " +
            "job_stat.int_eaten_count," +
            "job_stat.int_depend_count, " +
            "job_stat.int_succeeded_count, " +
            "job_usage.int_core_time_success, " +
            "job_usage.int_core_time_fail, " +
            "job_usage.int_frame_success_count, " +
            "job_usage.int_frame_fail_count, " +
            "job_usage.int_clock_time_high, " +
            "job_usage.int_clock_time_success, " +
            "(job_resource.int_cores + job_resource.int_local_cores) AS int_cores, " +
            "job_resource.int_min_cores, " +
            "job_resource.int_max_cores, " +
            "job_mem.int_max_rss " +
        "FROM " +
            "show, " +
            "folder_level, " +
            "folder_resource, " +
            "folder " +
        "LEFT JOIN " +
            "job " +
        "ON " +
            " (folder.pk_folder = job.pk_folder AND job.str_state='PENDING') " +
        "LEFT JOIN " +
            "facility " +
        "ON " +
            "(job.pk_facility = facility.pk_facility) " +
        "LEFT JOIN " +
            "job_stat " +
        "ON " +
            "(job.pk_job = job_stat.pk_job) " +
        "LEFT JOIN " +
            "job_resource " +
        "ON " +
            "(job.pk_job = job_resource.pk_job) " +
        "LEFT JOIN " +
            "job_usage " +
        "ON " +
            "(job.pk_job = job_usage.pk_job) " +
        "LEFT JOIN " +
            "job_mem " +
        "ON " +
            "(job.pk_job = job_mem.pk_job) " +
        "WHERE " +
            "show.pk_show = folder.pk_show " +
        "AND " +
            "folder.pk_folder = folder_level.pk_folder " +
        "AND " +
            "folder.pk_folder = folder_resource.pk_folder ";

    class NestedJobWhiteboardMapper implements RowMapper<NestedGroup> {

        public Map<String, NestedGroup> groups = new HashMap<String,NestedGroup>(50);
        public Map<String, List<String>> childrenMap = new HashMap<String, List<String>>();
        public String rootGroupID;

        @Override
        public NestedGroup mapRow(ResultSet rs, int rowNum) throws SQLException {
            String groupId = rs.getString("pk_folder");
            NestedGroup group;
            if (!groups.containsKey(groupId)) {
                group = NestedGroup.newBuilder()
                        .setId(rs.getString("pk_folder"))
                        .setName(rs.getString("group_name"))
                        .setDefaultJobPriority(rs.getInt("int_def_job_priority"))
                        .setDefaultJobMinCores(Convert.coreUnitsToCores(rs.getInt("int_def_job_min_cores")))
                        .setDefaultJobMaxCores(Convert.coreUnitsToCores(rs.getInt("int_def_job_max_cores")))
                        .setMaxCores(Convert.coreUnitsToCores(rs.getInt("folder_max_cores")))
                        .setMinCores(Convert.coreUnitsToCores(rs.getInt("folder_min_cores")))
                        .setLevel(rs.getInt("int_level"))
                        .build();

                String parentGroupId = rs.getString("pk_parent_folder");
                if (parentGroupId != null) {
                    List<String> children = childrenMap.get(parentGroupId);
                    if (children == null) {
                        children = new ArrayList<>();
                        childrenMap.put(parentGroupId, children);
                    }
                    children.add(groupId);
                }
                else {
                    rootGroupID = rs.getString("pk_folder");
                }
                groups.put(groupId, group);
            }
            else {
                group = groups.get(groupId);
            }
            if (rs.getString("pk_job") != null) {
                GroupStats oldStats = group.getStats();
                JobStats jobStats = WhiteboardDaoJdbc.mapJobStats(rs);
                GroupStats groupStats = GroupStats.newBuilder()
                        .setDeadFrames(oldStats.getDeadFrames() + jobStats.getDeadFrames())
                        .setRunningFrames(oldStats.getRunningFrames() + jobStats.getRunningFrames())
                        .setWaitingFrames(oldStats.getWaitingFrames() + jobStats.getWaitingFrames())
                        .setDependFrames(oldStats.getDependFrames() + jobStats.getDependFrames())
                        .setReservedCores(oldStats.getReservedCores() + jobStats.getReservedCores())
                        .setPendingJobs(oldStats.getPendingJobs() + 1).build();

                group = group.toBuilder()
                        .setStats(groupStats)
                        .addJobs(rs.getString("pk_job"))
                        .build();
                groups.put(groupId, group);
            }
            return group;
        }
    }

    private NestedJobWhiteboardMapper updateConnections(NestedJobWhiteboardMapper mapper) {
        for (Map.Entry<String, List<String>> entry : mapper.childrenMap.entrySet()) {
            NestedGroup group = mapper.groups.get(entry.getKey());
            NestedGroupSeq.Builder childrenBuilder = NestedGroupSeq.newBuilder();
            for (String childId : entry.getValue()) {
                NestedGroup child = mapper.groups.get(childId);
                child = child.toBuilder().setParent(group).build();
                childrenBuilder.addNestedGroups(child);
                mapper.groups.put(childId, child);
            }
            group = group.toBuilder()
                    .setGroups(childrenBuilder.build())
                    .build();
            mapper.groups.put(entry.getKey(), group);
        }
        return mapper;
    }

    public NestedGroup getJobWhiteboard(ShowInterface show) {

        CachedJobWhiteboardMapper cachedMapper = jobCache.get(show.getShowId());
        if (cachedMapper != null) {
            if (System.currentTimeMillis() - cachedMapper.time < CACHE_TIMEOUT) {
                return cachedMapper.mapper.groups.get(cachedMapper.mapper.rootGroupID);
            }
        }

        NestedJobWhiteboardMapper mapper = new NestedJobWhiteboardMapper();
        getJdbcTemplate().query(
                GET_NESTED_GROUPS + " AND show.pk_show=? ORDER BY folder_level.int_level ASC",
                mapper, show.getShowId());

        mapper = updateConnections(mapper);
        jobCache.put(show.getShowId(), new CachedJobWhiteboardMapper(mapper));
        return mapper.groups.get(mapper.rootGroupID);
    }


    private static final NestedJob mapResultSetToJob(ResultSet rs) throws SQLException {

        NestedJob.Builder jobBuilder = NestedJob.newBuilder()
                .setId(rs.getString("pk_job"))
                .setLogDir(rs.getString("str_log_dir"))
                .setMaxCores(Convert.coreUnitsToCores(rs.getInt("int_max_cores")))
                .setMinCores(Convert.coreUnitsToCores(rs.getInt("int_min_cores")))
                .setName(rs.getString("str_name"))
                .setPriority(rs.getInt("int_priority"))
                .setShot(rs.getString("str_shot"))
                .setShow(rs.getString("str_show"))
                .setOs(rs.getString("str_os"))
                .setFacility(rs.getString("facility_name"))
                .setGroup(rs.getString("group_name"))
                .setState(JobState.valueOf(rs.getString("str_state")))
                .setUid(rs.getInt("int_uid"))
                .setUser(rs.getString("str_user"))
                .setIsPaused(rs.getBoolean("b_paused"))
                .setHasComment(rs.getBoolean("b_comment"))
                .setAutoEat(rs.getBoolean("b_autoeat"))
                .setStartTime((int) (rs.getTimestamp("ts_started").getTime() / 1000))
                .setStats(WhiteboardDaoJdbc.mapJobStats(rs));
        Timestamp ts = rs.getTimestamp("ts_stopped");
        if (ts != null) {
            jobBuilder.setStopTime((int) (ts.getTime() / 1000));
        }
        else {
            jobBuilder.setStopTime(0);
        }
        return jobBuilder.build();
    }

    private static final String GET_HOSTS =
        "SELECT " +
            "alloc.str_name AS alloc_name, " +
            "host.pk_host, " +
            "host.str_name AS host_name, " +
            "host_stat.str_state AS host_state, " +
            "host.b_nimby, " +
            "host_stat.ts_booted, " +
            "host_stat.ts_ping, " +
            "host.int_cores, " +
            "host.int_cores_idle, " +
            "host.int_gpu, " +
            "host.int_gpu_idle, " +
            "host.int_mem, " +
            "host.int_mem_idle, " +
            "host.str_lock_state, " +
            "host.str_tags, " +
            "host.b_comment, " +
            "host.int_thread_mode, " +
            "host_stat.str_os, " +
            "host_stat.int_mem_total, " +
            "host_stat.int_mem_free, " +
            "host_stat.int_swap_total, " +
            "host_stat.int_swap_free, " +
            "host_stat.int_mcp_total, " +
            "host_stat.int_mcp_free, " +
            "host_stat.int_gpu_total, " +
            "host_stat.int_gpu_free, " +
            "host_stat.int_load, " +
            "proc.pk_proc, " +
            "proc.int_cores_reserved AS proc_cores, " +
            "proc.int_mem_reserved AS proc_memory, " +
            "proc.int_mem_used AS used_memory, " +
            "proc.int_mem_max_used AS max_memory, " +
            "proc.int_gpu_reserved AS proc_gpu, " +
            "proc.ts_ping, " +
            "proc.ts_booked, " +
            "proc.ts_dispatched, " +
            "proc.b_unbooked, " +
            "redirect.str_name AS str_redirect, " +
            "job.str_name AS job_name, " +
            "job.str_log_dir, " +
            "show.str_name AS show_name, " +
            "frame.str_name AS frame_name " +
        "FROM " +
            "alloc, " +
            "host_stat, " +
            "host " +
                "LEFT JOIN " +
                    "proc " +
                 "ON " +
                     "(proc.pk_host = host.pk_host) " +
                 "LEFT JOIN " +
                    "frame " +
                "ON " +
                    "(proc.pk_frame = frame.pk_frame) " +
                "LEFT JOIN " +
                    "job " +
                "ON " +
                    "(proc.pk_job  = job.pk_job) " +
                "LEFT JOIN " +
                    "show " +
                "ON " +
                    "(proc.pk_show = show.pk_show) " +
                "LEFT JOIN " +
                    "redirect " +
                "ON " +
                    "(proc.pk_proc = redirect.pk_proc) " +
        "WHERE " +
            "host.pk_alloc = alloc.pk_alloc " +
        "AND " +
            "host.pk_host = host_stat.pk_host ";

    /**
     * Caches a the host whiteboard.  This class is not
     * thread safe so you have to synchronize calls to
     * the "cache" method on your own.
     */
    class CachedHostWhiteboard {

        /**
         * Number of seconds till the cache expires
         */
        private static final int CACHE_EXPIRE_TIME_MS = 10000;

        /**
         * The host whiteboard we're caching
         */
        private NestedHostSeq hostWhiteboard;

        /**
         * The time in which the cache expires.
         */
        private long expireTime = 0l;

        public void cache(List<NestedHost> hostWhiteboard) {
            this.hostWhiteboard = NestedHostSeq.newBuilder().addAllNestedHosts(hostWhiteboard).build();
            expireTime = System.currentTimeMillis() + CACHE_EXPIRE_TIME_MS;
        }

        public NestedHostSeq get() {
            return hostWhiteboard;
        }

        public boolean isExpired() {
            return System.currentTimeMillis() > expireTime;
        }
    }

    /**
     * The CachedHostWhiteboard holds onto the result of the last
     * host whiteboard query for about 10 seconds, returning the
     * same result to all subsequent requests.
     */
    private final CachedHostWhiteboard cachedHostWhiteboard =
        new CachedHostWhiteboard();

    public NestedHostSeq getHostWhiteboard() {

        if (!cachedHostWhiteboard.isExpired()) {
            return cachedHostWhiteboard.get();
        }

        /*
         * Ensures only 1 thread is doing the query, other threads will wait
         * and then return the result of the thead that actually did
         * the query.
         */
        synchronized (cachedHostWhiteboard) {

            if (!cachedHostWhiteboard.isExpired()) {
                return cachedHostWhiteboard.get();
            }

            final List<NestedHost> result = new ArrayList<NestedHost>(3000);
            final Map<String, NestedHost> hosts = new HashMap<String,NestedHost>(3000);
            final Map<String, NestedProc> procs = new HashMap<String,NestedProc>(8000);

            getJdbcTemplate().query(
                    GET_HOSTS,
                    new RowMapper<NestedHost>() {

                        public NestedHost mapRow(ResultSet rs, int row) throws SQLException {
                            NestedHost host;
                            String hid = rs.getString("pk_host");
                            if (!hosts.containsKey(hid)) {
                                host = WhiteboardDaoJdbc.mapNestedHostBuilder(rs).build();
                                hosts.put(hid, host);
                                result.add(host);
                            }
                            else {
                                host = hosts.get(hid);
                            }

                            String pid = rs.getString("pk_proc");
                            if (pid != null) {
                                NestedProc proc;
                                if (!procs.containsKey(pid)) {
                                    proc = NestedProc.newBuilder()
                                            .setId(pid)
                                            .setName(CueUtil.buildProcName(host.getName(),
                                                    rs.getInt("proc_cores")))
                                            .setReservedCores(Convert.coreUnitsToCores(
                                                    rs.getInt("proc_cores")))
                                            .setReservedMemory(rs.getLong("proc_memory"))
                                            .setUsedMemory(rs.getLong("used_memory"))
                                            .setFrameName(rs.getString("frame_name"))
                                            .setJobName(rs.getString("job_name"))
                                            .setShowName(rs.getString("show_name"))
                                            .setPingTime((int) (rs.getTimestamp("ts_ping").getTime() / 1000))
                                            .setBookedTime((int) (rs.getTimestamp("ts_booked").getTime() / 1000))
                                            .setDispatchTime((int) (rs.getTimestamp("ts_dispatched").getTime() / 1000))
                                            .setUnbooked(rs.getBoolean("b_unbooked"))
                                            .setLogPath(String.format("%s/%s.%s.rqlog",
                                                    rs.getString("str_log_dir"),rs.getString("job_name"),
                                                    rs.getString("frame_name")))
                                            .setRedirectTarget(rs.getString("str_redirect"))
                                            .setParent(host)
                                            .build();

                                    host = host.toBuilder().setProcs(
                                            host.getProcs().toBuilder().addNestedProcs(proc).build())
                                            .build();
                                    procs.put(pid, proc);
                                }
                                else {
                                    proc = procs.get(pid);
                                }
                            }
                            return null;
                        }
                    });

            cachedHostWhiteboard.cache(result);
        }
        return cachedHostWhiteboard.get();
    }
}

