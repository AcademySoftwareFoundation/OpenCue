
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



package com.imageworks.spcue.dao.oracle;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.common.spring.remoting.IceServer;
import com.imageworks.spcue.CueIce.JobState;
import com.imageworks.spcue.CueClientIce.*;
import com.imageworks.spcue.dao.NestedWhiteboardDao;
import com.imageworks.spcue.util.Convert;
import com.imageworks.spcue.util.CueUtil;

public class NestedWhiteboardDaoJdbc extends JdbcDaoSupport implements NestedWhiteboardDao {

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

    private static IceServer iceServer;

    public NestedWhiteboardDaoJdbc(IceServer iceServer) {
        NestedWhiteboardDaoJdbc.iceServer = iceServer;
    }

    public static final String GET_NESTED_GROUPS =
        "SELECT " +
            "show.pk_show, " +
            "show.str_name AS str_show," +
            "facility.str_name AS facility_name,"+
            "dept.str_name AS dept_name,"+
            "folder.pk_folder," +
            "folder.pk_parent_folder," +
            "folder.str_name AS group_name," +
            "folder.int_job_priority as int_def_job_priority," +
            "folder.int_job_min_cores as int_def_job_min_cores," +
            "folder.int_job_max_cores as int_def_job_max_cores, " +
            "folder_resource.int_min_cores AS folder_min_cores," +
            "folder_resource.int_max_cores AS folder_max_cores," +
            "folder_level.int_level,"+
            "job.pk_job," +
            "job.str_name," +
            "job.str_shot," +
            "job.str_user," +
            "job.str_state," +
            "job.str_log_dir," +
            "job.int_uid," +
            "job_resource.int_priority," +
            "job.ts_started," +
            "job.ts_stopped," +
            "job.ts_updated,"+
            "job.b_paused," +
            "job.b_autoeat, " +
            "job.b_comment," +
            "job.str_os," +
            "job.int_frame_count, " +
            "job.int_layer_count, " +
            "job_stat.int_waiting_count, "+
            "job_stat.int_running_count, "+
            "job_stat.int_dead_count, " +
            "job_stat.int_eaten_count," +
            "job_stat.int_depend_count, "+
            "job_stat.int_succeeded_count, "+
            "job_usage.int_core_time_success, "+
            "job_usage.int_core_time_fail, " +
            "job_usage.int_frame_success_count, " +
            "job_usage.int_frame_fail_count, " +
            "job_usage.int_clock_time_high," +
            "job_usage.int_clock_time_success,"+
            "(job_resource.int_cores + job_resource.int_local_cores) AS int_cores,"+
            "job_resource.int_min_cores,"+
            "job_resource.int_max_cores,"+
            "job_mem.int_max_rss " +
        "FROM " +
            "show, " +
            "dept, " +
            "folder_level, " +
            "folder_resource, "+
            "folder " +
        "LEFT JOIN " +
            "job " +
        "ON " +
            " (folder.pk_folder = job.pk_folder AND job.str_state='Pending') " +
        "LEFT JOIN " +
            "facility "+
        "ON " +
            "(job.pk_facility = facility.pk_facility) "+
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
            "folder.pk_folder = folder_resource.pk_folder " +
        "AND " +
            "folder.pk_dept = dept.pk_dept ";

    class NestedJobWhiteboardMapper implements RowMapper<NestedGroup> {

        public Map<String, NestedGroup> groups = new HashMap<String,NestedGroup>(50);

        @Override
        public NestedGroup mapRow(ResultSet rs, int rowNum) throws SQLException {

            String group_id = rs.getString("pk_folder");
            NestedGroup group;
            if (!groups.containsKey(group_id)) {
                group = new NestedGroup();
                group.jobs = new ArrayList<NestedJob>();
                group.groups = new ArrayList<NestedGroup>();
                group.data = new GroupData();
                group.stats = new GroupStats(0,0,0,0,0,0f);
                group.data.name = rs.getString("group_name");
                group.data.defaultJobPriority = rs.getInt("int_def_job_priority");
                group.data.defaultJobMinCores =
                    Convert.coreUnitsToCores(rs.getInt("int_def_job_min_cores"));
                group.data.defaultJobMaxCores =
                    Convert.coreUnitsToCores(rs.getInt("int_def_job_max_cores"));
                group.data.maxCores = Convert.coreUnitsToCores(rs.getInt("folder_max_cores"));
                group.data.minCores = Convert.coreUnitsToCores(rs.getInt("folder_min_cores"));
                group.data.level = rs.getInt("int_level");
                group.data.department = rs.getString("dept_name");
                group.proxy = GroupInterfacePrxHelper.uncheckedCast(iceServer.getAdapter()
                        .createProxy(new Ice.Identity(rs.getString("pk_folder"),"manageGroup")));

                if (rs.getString("pk_parent_folder") != null) {
                    NestedGroup parent = groups.get(rs.getString("pk_parent_folder"));
                    group.parent = parent;
                    parent.groups.add(group);
                }
                else {
                    groups.put("root", group);
                }
                groups.put(group_id, group);
            }
            else {
                group = groups.get(group_id);
            }

            if (rs.getString("pk_job") != null) {
                NestedJob job = mapResultSetToJob(rs);
                job.parent = group;
                /*
                 * Instead of tallying up the group stats on the DB in a view,
                 * the query is a lot less costly if they are tallied up here.
                 */
                group.stats.deadFrames = group.stats.deadFrames + job.stats.deadFrames;
                group.stats.runningFrames =  group.stats.runningFrames + job.stats.runningFrames;
                group.stats.waitingFrames = group.stats.waitingFrames + job.stats.waitingFrames;
                group.stats.dependFrames = group.stats.dependFrames + job.stats.dependFrames;
                group.stats.reservedCores =  group.stats.reservedCores + job.stats.reservedCores;
                group.stats.pendingJobs++;
                group.jobs.add(job);
            }
            return null;
        }
    }

    public NestedGroup getJobWhiteboard(com.imageworks.spcue.Show show) {

        CachedJobWhiteboardMapper cachedMapper = jobCache.get(show.getShowId());
        if (cachedMapper != null) {
            if (System.currentTimeMillis() - cachedMapper.time < CACHE_TIMEOUT) {
                return cachedMapper.mapper.groups.get("root");
            }
        }

        NestedJobWhiteboardMapper mapper = new NestedJobWhiteboardMapper();
        getJdbcTemplate().query(
                GET_NESTED_GROUPS + " AND show.pk_show=? ORDER BY folder_level.int_level ASC",
                mapper, show.getShowId());

        jobCache.put(show.getShowId(), new CachedJobWhiteboardMapper(mapper));
        return mapper.groups.get("root");
    }


    private static final NestedJob mapResultSetToJob(ResultSet rs) throws SQLException {

        NestedJob job = new NestedJob();
        job.data = new JobData();
        job.data.logDir = rs.getString("str_log_dir");
        job.data.maxCores = Convert.coreUnitsToCores(rs.getInt("int_max_cores"));
        job.data.minCores = Convert.coreUnitsToCores(rs.getInt("int_min_cores"));
        job.data.name = rs.getString("str_name");
        job.data.priority = rs.getInt("int_priority");
        job.data.shot = rs.getString("str_shot");
        job.data.show = rs.getString("str_show");
        job.data.os = rs.getString("str_os");
        job.data.facility = rs.getString("facility_name");
        job.data.group = rs.getString("group_name");
        job.data.state = JobState.valueOf(rs.getString("str_state"));
        job.data.uid = rs.getInt("int_uid");
        job.data.user = rs.getString("str_user");
        job.data.isPaused = rs.getBoolean("b_paused");
        job.data.hasComment = rs.getBoolean("b_comment");
        job.data.autoEat = rs.getBoolean("b_autoeat");

        job.data.startTime = (int) (rs.getTimestamp("ts_started").getTime() / 1000);
        Timestamp ts = rs.getTimestamp("ts_stopped");
        if (ts != null) {
            job.data.stopTime = (int) (ts.getTime() / 1000);
        }
        else {
            job.data.stopTime = 0;
        }

        job.stats = WhiteboardDaoJdbc.mapJobStats(rs);
        job.proxy = JobInterfacePrxHelper.uncheckedCast(iceServer.getAdapter()
                .createProxy(new Ice.Identity(rs.getString("pk_job"),"manageJob")));

        return job;
    }

    private static final String GET_HOSTS =
        "SELECT " +
            "alloc.str_name AS alloc_name," +
            "host.pk_host, "+
            "host.str_name AS host_name," +
            "host_stat.str_state AS host_state,"+
            "host.b_nimby,"+
            "host_stat.ts_booted,"+
            "host_stat.ts_ping,"+
            "host.int_cores,"+
            "host.int_cores_idle,"+
            "host.int_mem,"+
            "host.int_mem_idle,"+
            "host.str_lock_state,"+
            "host.str_tags,"+
            "host.b_comment,"+
            "host.int_thread_mode,"+
            "host_stat.int_mem_total,"+
            "host_stat.int_mem_free,"+
            "host_stat.int_swap_total,"+
            "host_stat.int_swap_free,"+
            "host_stat.int_mcp_total,"+
            "host_stat.int_mcp_free,"+
            "host_stat.int_gpu_total,"+
            "host_stat.int_gpu_free,"+
            "host_stat.int_load,"+
            "proc.pk_proc,"+
            "proc.int_cores_reserved AS proc_cores,"+
            "proc.int_mem_reserved AS proc_memory, "+
            "proc.int_mem_used AS used_memory,"+
            "proc.int_mem_max_used AS max_memory,"+
            "proc.int_gpu_reserved AS proc_gpu, "+
            "proc.ts_ping,"+
            "proc.ts_booked,"+
            "proc.ts_dispatched,"+
            "proc.b_unbooked,"+
            "redirect.str_name AS str_redirect,"+
            "job.str_name AS job_name,"+
            "job.str_log_dir, "+
            "show.str_name AS show_name,"+
            "frame.str_name AS frame_name "+
        "FROM " +
            "alloc," +
            "host_stat,"+
            "host "+
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
                "ON "+
                    "(proc.pk_job  = job.pk_job) " +
                "LEFT JOIN "+
                    "show "+
                "ON " +
                    "(proc.pk_show = show.pk_show) "+
                "LEFT JOIN "+
                    "redirect "+
                "ON " +
                    "(proc.pk_proc = redirect.pk_proc) "+
        "WHERE " +
            "host.pk_alloc = alloc.pk_alloc " +
        "AND "+
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
        private List<NestedHost> hostWhiteboard;

        /**
         * The time in which the cache expires.
         */
        private long expireTime = 0l;

        public void cache(List<NestedHost> hostWhiteboard) {
            this.hostWhiteboard = hostWhiteboard;
            expireTime = System.currentTimeMillis() + CACHE_EXPIRE_TIME_MS;
        }

        public List<NestedHost> get() {
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

    public List<NestedHost> getHostWhiteboard() {

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
                                host = new NestedHost();
                                host.proxy = HostInterfacePrxHelper.uncheckedCast(iceServer.getAdapter()
                                        .createProxy(new Ice.Identity(hid,"manageHost")));
                                host.procs = new ArrayList<NestedProc>();
                                host.data = WhiteboardDaoJdbc.mapHostData(rs);
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
                                    proc = new NestedProc();
                                    proc.data = new ProcData();
                                    proc.data.name  = CueUtil.buildProcName(host.data.name,
                                            rs.getInt("proc_cores"));
                                    proc.data.reservedCores = Convert.coreUnitsToCores(
                                            rs.getInt("proc_cores"));
                                    proc.data.reservedMemory = rs.getLong("proc_memory");
                                    proc.data.usedMemory = rs.getLong("used_memory");
                                    proc.data.frameName = rs.getString("frame_name");
                                    proc.data.jobName = rs.getString("job_name");
                                    proc.data.showName = rs.getString("show_name");
                                    proc.data.pingTime = (int) (rs.getTimestamp("ts_ping").getTime() / 1000);
                                    proc.data.bookedTime = (int) (rs.getTimestamp("ts_booked").getTime() / 1000);
                                    proc.data.dispatchTime = (int) (rs.getTimestamp("ts_dispatched").getTime() / 1000);
                                    proc.data.unbooked = rs.getBoolean("b_unbooked");
                                    proc.data.logPath = String.format("%s/%s.%s.rqlog",
                                            rs.getString("str_log_dir"),rs.getString("job_name"),
                                            rs.getString("frame_name"));
                                    proc.data.redirectTarget = rs.getString("str_redirect");
                                    proc.parent = host;
                                    proc.proxy = ProcInterfacePrxHelper.uncheckedCast(iceServer.getAdapter()
                                            .createProxy(new Ice.Identity(pid,"manageProc")));
                                    host.procs.add(proc);

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

