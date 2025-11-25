
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

import java.sql.Connection;
import java.sql.PreparedStatement;
import static com.imageworks.spcue.dao.postgres.DispatchQuery.*;
import java.sql.ResultSet;
import java.sql.SQLException;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;
import org.springframework.jdbc.core.PreparedStatementCreator;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.PrometheusMetricsCollector;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.SortableShow;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.DispatcherDao;
import com.imageworks.spcue.grpc.host.ThreadMode;

/**
 * Dispatcher DAO
 *
 * @category DAO
 */
public class DispatcherDaoJdbc extends JdbcDaoSupport implements DispatcherDao {
    private static final Logger logger = LogManager.getLogger(DispatcherDaoJdbc.class);
    private PrometheusMetricsCollector prometheusMetrics;

    public void setPrometheusMetrics(PrometheusMetricsCollector prometheusMetrics) {
        this.prometheusMetrics = prometheusMetrics;
    }

    public static final RowMapper<String> PKJOB_MAPPER = new RowMapper<String>() {
        public String mapRow(ResultSet rs, int rowNum) throws SQLException {
            return rs.getString("pk_job");
        }
    };

    private static final RowMapper<SortableShow> SHOW_MAPPER = new RowMapper<SortableShow>() {
        public SortableShow mapRow(ResultSet rs, int rowNum) throws SQLException {
            return new SortableShow(rs.getString("pk_show"), rs.getFloat("float_tier"));
        }
    };

    private int threadMode(int mode) {
        if (mode == ThreadMode.ALL_VALUE)
            return mode;
        return ThreadMode.AUTO_VALUE;
    }

    /**
     * Number of milliseconds before the show cache expires and a new show cache is created.
     */
    private static final long SHOW_CACHE_EXPIRE_TIME_SEC = 8000;

    /**
     * Wraps a list of SortableShows along with an expiration time.
     */
    private class ShowCache {
        final private long expireTime = System.currentTimeMillis() + SHOW_CACHE_EXPIRE_TIME_SEC;
        final private List<SortableShow> shows;

        public ShowCache(List<SortableShow> shows) {
            this.shows = shows;
            Collections.sort(this.shows);
        }

        public boolean isExpired() {
            return System.currentTimeMillis() > expireTime;
        }

        public List<SortableShow> getShows() {
            return shows;
        }
    }

    /**
     * A cache of SortableShows keyed on host tags.
     */
    private final ConcurrentHashMap<String, ShowCache> bookableShows =
            new ConcurrentHashMap<String, ShowCache>();

    public boolean testMode = false;

    /**
     * Choose between different scheduling strategies
     */
    private SchedulingMode schedulingMode;

    @Autowired
    public DispatcherDaoJdbc(Environment env) {
        this.schedulingMode = SchedulingMode.valueOf(
                env.getProperty("dispatcher.scheduling_mode", String.class, "PRIORITY_ONLY"));
    }

    @Override
    public SchedulingMode getSchedulingMode() {
        return schedulingMode;
    }

    @Override
    public void setSchedulingMode(SchedulingMode schedulingMode) {
        this.schedulingMode = schedulingMode;
    }

    /**
     * Returns a sorted list of shows that have pending jobs which could benefit from the specified
     * allocation.
     *
     * @param alloc
     * @return a sorted list of shows.
     */
    private List<SortableShow> getBookableShows(AllocationInterface alloc) {
        long startTime = System.currentTimeMillis();
        String key = alloc.getAllocationId();

        ShowCache cached = bookableShows.get(key);
        if (cached == null) {
            bookableShows.put(key, new ShowCache(
                    getJdbcTemplate().query(FIND_SHOWS, SHOW_MAPPER, alloc.getAllocationId())));
        } else if (cached.isExpired()) {
            bookableShows.put(key, new ShowCache(
                    getJdbcTemplate().query(FIND_SHOWS, SHOW_MAPPER, alloc.getAllocationId())));
        }
        prometheusMetrics.setBookingDurationMetric("getBookableShows",
                System.currentTimeMillis() - startTime);

        return bookableShows.get(key).shows;
    }

    private String handleInClause(String key, String query, int inValueLength) {
        String placeholders = String.join(",", Collections.nCopies(inValueLength, "?"));
        return query.replace(key + " IN ?", key + " IN (" + placeholders + ")");
    }

    private Set<String> findDispatchJobs(DispatchHost host, int numJobs, boolean shuffleShows) {
        LinkedHashSet<String> result = new LinkedHashSet<String>();
        List<SortableShow> shows = new LinkedList<SortableShow>(getBookableShows(host));
        // shows were sorted. If we want it in random sequence, we need to shuffle it.
        if (shuffleShows) {
            if (!shows.isEmpty())
                shows.remove(0);
            Collections.shuffle(shows);
        }

        long loopTime = System.currentTimeMillis();
        for (SortableShow s : shows) {
            long lastTime = System.currentTimeMillis();
            if (s.isSkipped(host.tags, (long) host.cores, host.memory)) {
                logger.info("skipping show " + s.getShowId());
                continue;
            }

            if (s.isSkipped(host)) {
                logger.info("skipping show " + s.getShowId() + ", over its subscription.");
                continue;
            }

            /**
             * Check if the show is over its subscription because we're using cached SortableShows,
             * we don't pull a fresh list of shows for a while. If the show is over its subscription
             * the alloc gets add to the SortableShow skipped alloc set.
             */
            if (getJdbcTemplate().queryForObject(
                    "SELECT int_burst - int_cores FROM subscription WHERE pk_show=? AND pk_alloc=?",
                    Integer.class, s.getShowId(), host.getAllocationId()) < 100) {
                s.skip(host);

                prometheusMetrics.setBookingDurationMetric("findDispatchJobs check overburst",
                        System.currentTimeMillis() - lastTime);
                continue;
            }

            if (host.idleGpus == 0 && (schedulingMode == SchedulingMode.BALANCED)) {
                result.addAll(getJdbcTemplate().query(new PreparedStatementCreator() {
                    @Override
                    public PreparedStatement createPreparedStatement(Connection conn)
                            throws SQLException {
                        String query = handleInClause("str_os", FIND_JOBS_BY_SHOW_NO_GPU,
                                host.getOs().length);
                        PreparedStatement find_jobs_stmt = conn.prepareStatement(query);

                        int index = 1;
                        find_jobs_stmt.setString(index++, s.getShowId());
                        find_jobs_stmt.setString(index++, host.getFacilityId());
                        for (String item : host.getOs()) {
                            find_jobs_stmt.setString(index++, item);
                        }
                        find_jobs_stmt.setInt(index++, host.idleCores);
                        find_jobs_stmt.setLong(index++, host.idleMemory);
                        find_jobs_stmt.setInt(index++, threadMode(host.threadMode));
                        find_jobs_stmt.setString(index++, host.getName());
                        find_jobs_stmt.setInt(index++, numJobs * 10);
                        return find_jobs_stmt;
                    }
                }, PKJOB_MAPPER));
                prometheusMetrics.setBookingDurationMetric("findDispatchJobs nogpu findByShowQuery",
                        System.currentTimeMillis() - lastTime);
            } else {
                result.addAll(getJdbcTemplate().query(new PreparedStatementCreator() {
                    @Override
                    public PreparedStatement createPreparedStatement(Connection conn)
                            throws SQLException {
                        String query =
                                handleInClause("str_os", findByShowQuery(), host.getOs().length);
                        PreparedStatement find_jobs_stmt = conn.prepareStatement(query);
                        int index = 1;
                        find_jobs_stmt.setString(index++, s.getShowId());
                        find_jobs_stmt.setString(index++, host.getFacilityId());
                        for (String item : host.getOs()) {
                            find_jobs_stmt.setString(index++, item);
                        }
                        find_jobs_stmt.setInt(index++, host.idleCores);
                        find_jobs_stmt.setLong(index++, host.idleMemory);
                        find_jobs_stmt.setInt(index++, threadMode(host.threadMode));
                        find_jobs_stmt.setInt(index++, host.idleGpus);
                        find_jobs_stmt.setLong(index++, (host.idleGpuMemory > 0) ? 1 : 0);
                        find_jobs_stmt.setLong(index++, host.idleGpuMemory);
                        find_jobs_stmt.setString(index++, host.getName());
                        find_jobs_stmt.setInt(index++, numJobs * 10);
                        return find_jobs_stmt;
                    }
                }, PKJOB_MAPPER));
                prometheusMetrics.setBookingDurationMetric("findDispatchJobs findByShowQuery",
                        System.currentTimeMillis() - lastTime);
            }

            // Collect metrics
            prometheusMetrics.incrementFindJobsByShowQueryCountMetric();
            if (result.size() < 1) {
                if (host.gpuMemory == 0) {
                    s.skip(host.tags, host.idleCores, host.idleMemory);
                }
            } else {
                return result;
            }
        }
        prometheusMetrics.setBookingDurationMetric("findDispatchJobs show loop",
                System.currentTimeMillis() - loopTime);
        return result;

    }

    private String findByShowQuery() {
        switch (schedulingMode) {
            case PRIORITY_ONLY:
                return FIND_JOBS_BY_SHOW_PRIORITY_MODE;
            case FIFO:
                return FIND_JOBS_BY_SHOW_FIFO_MODE;
            case BALANCED:
                return FIND_JOBS_BY_SHOW;
            default:
                return FIND_JOBS_BY_SHOW_PRIORITY_MODE;
        }
    }

    private String findByGroupQuery() {
        switch (schedulingMode) {
            case PRIORITY_ONLY:
                return FIND_JOBS_BY_GROUP_PRIORITY_MODE;
            case FIFO:
                return FIND_JOBS_BY_GROUP_FIFO_MODE;
            case BALANCED:
                return FIND_JOBS_BY_GROUP_BALANCED_MODE;
            default:
                return FIND_JOBS_BY_GROUP_PRIORITY_MODE;
        }
    }

    @Override
    public Set<String> findDispatchJobsForAllShows(DispatchHost host, int numJobs) {
        return findDispatchJobs(host, numJobs, true);
    }

    @Override
    public Set<String> findDispatchJobs(DispatchHost host, int numJobs) {
        return findDispatchJobs(host, numJobs, false);
    }

    @Override
    public Set<String> findDispatchJobs(DispatchHost host, GroupInterface g) {
        LinkedHashSet<String> result = new LinkedHashSet<String>(5);
        long lastTime = System.currentTimeMillis();

        if (host.idleGpus == 0 && (schedulingMode == SchedulingMode.BALANCED)) {
            String query = handleInClause("str_os", FIND_JOBS_BY_GROUP_NO_GPU, host.getOs().length);
            ArrayList<Object> args = new ArrayList<Object>();

            args.add(g.getGroupId());
            args.add(host.getFacilityId());
            for (String item : host.getOs()) {
                args.add(item);
            }
            args.add(host.idleCores);
            args.add(host.idleMemory);
            args.add(threadMode(host.threadMode));
            args.add(host.getName());
            args.add(50);
            result.addAll(getJdbcTemplate().query(query, PKJOB_MAPPER, args.toArray()));
            prometheusMetrics.setBookingDurationMetric("findDispatchJobs by group nogpu query",
                    System.currentTimeMillis() - lastTime);
        } else {
            String query = handleInClause("str_os", findByGroupQuery(), host.getOs().length);
            ArrayList<Object> args = new ArrayList<Object>();

            args.add(g.getGroupId());
            args.add(host.getFacilityId());
            for (String item : host.getOs()) {
                args.add(item);
            }
            args.add(host.idleCores);
            args.add(host.idleMemory);
            args.add(threadMode(host.threadMode));
            args.add(host.idleGpus);
            args.add(host.idleGpuMemory > 0 ? 1 : 0);
            args.add(host.idleGpuMemory);
            args.add(host.getName());
            args.add(50);
            result.addAll(getJdbcTemplate().query(query, PKJOB_MAPPER, args.toArray()));
            prometheusMetrics.setBookingDurationMetric("findDispatchJobs by group query",
                    System.currentTimeMillis() - lastTime);
        }
        return result;
    }

    @Override
    public List<DispatchFrame> findNextDispatchFrames(JobInterface job, VirtualProc proc,
            int limit) {
        long lastTime = System.currentTimeMillis();
        List<DispatchFrame> frames;
        if (proc.isLocalDispatch) {
            frames = getJdbcTemplate().query(FIND_LOCAL_DISPATCH_FRAME_BY_JOB_AND_PROC,
                    FrameDaoJdbc.DISPATCH_FRAME_MAPPER, proc.memoryReserved, proc.gpuMemoryReserved,
                    job.getJobId(), limit);
        } else {
            frames = getJdbcTemplate().query(FIND_DISPATCH_FRAME_BY_JOB_AND_PROC,
                    FrameDaoJdbc.DISPATCH_FRAME_MAPPER, proc.coresReserved, proc.memoryReserved,
                    proc.gpusReserved, (proc.gpuMemoryReserved > 0) ? 1 : 0, proc.gpuMemoryReserved,
                    job.getJobId(), proc.hostName, job.getJobId(), limit);
        }

        prometheusMetrics.setBookingDurationMetric("findNextDispatchFrames by job and proc query",
                System.currentTimeMillis() - lastTime);

        return frames;
    }

    @Override
    public List<DispatchFrame> findNextDispatchFrames(JobInterface job, DispatchHost host,
            int limit) {
        long lastTime = System.currentTimeMillis();
        List<DispatchFrame> frames;

        if (host.isLocalDispatch) {
            frames = getJdbcTemplate().query(FIND_LOCAL_DISPATCH_FRAME_BY_JOB_AND_HOST,
                    FrameDaoJdbc.DISPATCH_FRAME_MAPPER, host.idleMemory, host.idleGpuMemory,
                    job.getJobId(), limit);

        } else {
            frames = getJdbcTemplate().query(FIND_DISPATCH_FRAME_BY_JOB_AND_HOST,
                    FrameDaoJdbc.DISPATCH_FRAME_MAPPER, host.idleCores, host.idleMemory,
                    threadMode(host.threadMode), host.idleGpus, (host.idleGpuMemory > 0) ? 1 : 0,
                    host.idleGpuMemory, job.getJobId(), host.getName(), job.getJobId(), limit);
        }
        prometheusMetrics.setBookingDurationMetric("findNextDispatchFrames by job and host query",
                System.currentTimeMillis() - lastTime);

        return frames;
    }

    @Override
    public List<DispatchFrame> findNextDispatchFrames(LayerInterface layer, VirtualProc proc,
            int limit) {
        long lastTime = System.currentTimeMillis();
        List<DispatchFrame> frames;

        if (proc.isLocalDispatch) {
            frames = getJdbcTemplate().query(FIND_LOCAL_DISPATCH_FRAME_BY_LAYER_AND_PROC,
                    FrameDaoJdbc.DISPATCH_FRAME_MAPPER, proc.memoryReserved, proc.gpuMemoryReserved,
                    layer.getLayerId(), limit);
        } else {
            frames = getJdbcTemplate().query(FIND_DISPATCH_FRAME_BY_LAYER_AND_PROC,
                    FrameDaoJdbc.DISPATCH_FRAME_MAPPER, proc.coresReserved, proc.memoryReserved,
                    proc.gpusReserved, proc.gpuMemoryReserved, layer.getLayerId(),
                    layer.getLayerId(), proc.hostName, limit);
        }

        prometheusMetrics.setBookingDurationMetric("findNextDispatchFrames by layer and proc query",
                System.currentTimeMillis() - lastTime);

        return frames;
    }

    @Override
    public List<DispatchFrame> findNextDispatchFrames(LayerInterface layer, DispatchHost host,
            int limit) {
        long lastTime = System.currentTimeMillis();
        List<DispatchFrame> frames;

        if (host.isLocalDispatch) {
            frames = getJdbcTemplate().query(FIND_LOCAL_DISPATCH_FRAME_BY_LAYER_AND_HOST,
                    FrameDaoJdbc.DISPATCH_FRAME_MAPPER, host.idleMemory, host.idleGpuMemory,
                    layer.getLayerId(), limit);

        } else {
            frames = getJdbcTemplate().query(FIND_DISPATCH_FRAME_BY_LAYER_AND_HOST,
                    FrameDaoJdbc.DISPATCH_FRAME_MAPPER, host.idleCores, host.idleMemory,
                    threadMode(host.threadMode), host.idleGpus, host.idleGpuMemory,
                    layer.getLayerId(), layer.getLayerId(), host.getName(), limit);
        }

        prometheusMetrics.setBookingDurationMetric("findNextDispatchFrames by layer and host query",
                System.currentTimeMillis() - lastTime);

        return frames;
    }

    @Override
    public DispatchFrame findNextDispatchFrame(JobInterface job, VirtualProc proc) {
        return findNextDispatchFrames(job, proc, 1).get(0);
    }

    @Override
    public DispatchFrame findNextDispatchFrame(JobInterface job, DispatchHost host) {
        return findNextDispatchFrames(job, host, 1).get(0);
    }

    @Override
    public boolean findUnderProcedJob(JobInterface excludeJob, VirtualProc proc) {
        long start = System.currentTimeMillis();
        try {
            return getJdbcTemplate().queryForObject(FIND_UNDER_PROCED_JOB_BY_FACILITY,
                    Integer.class, excludeJob.getShowId(), proc.getFacilityId(), proc.os,
                    excludeJob.getShowId(), proc.getFacilityId(), proc.os, proc.coresReserved,
                    proc.memoryReserved, proc.gpusReserved, proc.gpuMemoryReserved,
                    proc.hostName) > 0;
        } catch (org.springframework.dao.EmptyResultDataAccessException e) {
            return false;
        } finally {
            prometheusMetrics.setBookingDurationMetric("findUnderProcedJob query",
                    System.currentTimeMillis() - start);
        }
    }

    @Override
    public boolean higherPriorityJobExists(JobDetail baseJob, VirtualProc proc) {
        long start = System.currentTimeMillis();
        try {
            return getJdbcTemplate().queryForObject(HIGHER_PRIORITY_JOB_BY_FACILITY_EXISTS,
                    Boolean.class, baseJob.priority, proc.getFacilityId(), proc.os,
                    proc.getFacilityId(), proc.os, proc.coresReserved, proc.memoryReserved,
                    proc.gpusReserved, proc.gpuMemoryReserved, proc.hostName);
        } catch (org.springframework.dao.EmptyResultDataAccessException e) {
            return false;
        } finally {
            prometheusMetrics.setBookingDurationMetric("higherPriorityJobExists query",
                    System.currentTimeMillis() - start);
        }
    }

    @Override
    public Set<String> findDispatchJobs(DispatchHost host, ShowInterface show, int numJobs) {
        LinkedHashSet<String> result = new LinkedHashSet<String>(numJobs);
        long start = System.currentTimeMillis();
        if (host.idleGpus == 0 && (schedulingMode == SchedulingMode.BALANCED)) {
            String query = handleInClause("str_os", FIND_JOBS_BY_SHOW_NO_GPU, host.getOs().length);
            ArrayList<Object> args = new ArrayList<Object>();
            args.add(show.getShowId());
            args.add(host.getFacilityId());
            for (String item : host.getOs()) {
                args.add(item);
            }
            args.add(host.idleCores);
            args.add(host.idleMemory);
            args.add(threadMode(host.threadMode));
            args.add(host.getName());
            args.add(numJobs * 10);

            result.addAll(getJdbcTemplate().query(query, PKJOB_MAPPER, args.toArray()));

            prometheusMetrics.setBookingDurationMetric("findDispatchJobs by show nogpu query",
                    System.currentTimeMillis() - start);
        } else {
            String query = handleInClause("str_os", findByShowQuery(), host.getOs().length);
            ArrayList<Object> args = new ArrayList<Object>();
            args.add(show.getShowId());
            args.add(host.getFacilityId());
            for (String item : host.getOs()) {
                args.add(item);
            }
            args.add(host.idleCores);
            args.add(host.idleMemory);
            args.add(threadMode(host.threadMode));
            args.add(host.idleGpus);
            args.add(host.idleGpuMemory > 0 ? 1 : 0);
            args.add(host.idleGpuMemory);
            args.add(host.getName());
            args.add(numJobs * 10);

            result.addAll(getJdbcTemplate().query(query, PKJOB_MAPPER, args.toArray()));

            prometheusMetrics.setBookingDurationMetric("findDispatchJobs by show query",
                    System.currentTimeMillis() - start);
        }

        // Collect metrics
        prometheusMetrics.incrementFindJobsByShowQueryCountMetric();
        return result;
    }

    @Override
    public Set<String> findLocalDispatchJobs(DispatchHost host) {
        LinkedHashSet<String> result = new LinkedHashSet<String>(5);
        long start = System.currentTimeMillis();

        String query = handleInClause("str_os", FIND_JOBS_BY_LOCAL, host.getOs().length);
        ArrayList<Object> args = new ArrayList<Object>();
        args.add(host.getHostId());
        args.add(host.getFacilityId());
        for (String item : host.getOs()) {
            args.add(item);
        }
        args.add(host.getHostId());
        args.add(host.getFacilityId());
        for (String item : host.getOs()) {
            args.add(item);
        }

        result.addAll(getJdbcTemplate().query(query, PKJOB_MAPPER, args.toArray()));

        prometheusMetrics.setBookingDurationMetric("findLocalDispatchJobs query",
                System.currentTimeMillis() - start);
        return result;
    }

    @Override
    public void clearCache() {
        bookableShows.clear();
    }
}
