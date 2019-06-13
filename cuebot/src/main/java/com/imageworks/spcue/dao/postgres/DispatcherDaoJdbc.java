
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
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

import com.imageworks.spcue.dao.AbstractJdbcDao;
import org.apache.log4j.Logger;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.SortableShow;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.DispatcherDao;
import com.imageworks.spcue.grpc.host.ThreadMode;
import com.imageworks.spcue.util.CueUtil;
import org.springframework.stereotype.Repository;

import static com.imageworks.spcue.dao.postgres.DispatchQuery.FIND_DISPATCH_FRAME_BY_JOB_AND_HOST;
import static com.imageworks.spcue.dao.postgres.DispatchQuery.FIND_DISPATCH_FRAME_BY_JOB_AND_PROC;
import static com.imageworks.spcue.dao.postgres.DispatchQuery.FIND_DISPATCH_FRAME_BY_LAYER_AND_HOST;
import static com.imageworks.spcue.dao.postgres.DispatchQuery.FIND_DISPATCH_FRAME_BY_LAYER_AND_PROC;
import static com.imageworks.spcue.dao.postgres.DispatchQuery.FIND_JOBS_BY_GROUP;
import static com.imageworks.spcue.dao.postgres.DispatchQuery.FIND_JOBS_BY_LOCAL;
import static com.imageworks.spcue.dao.postgres.DispatchQuery.FIND_JOBS_BY_SHOW;
import static com.imageworks.spcue.dao.postgres.DispatchQuery.FIND_LOCAL_DISPATCH_FRAME_BY_JOB_AND_HOST;
import static com.imageworks.spcue.dao.postgres.DispatchQuery.FIND_LOCAL_DISPATCH_FRAME_BY_JOB_AND_PROC;
import static com.imageworks.spcue.dao.postgres.DispatchQuery.FIND_LOCAL_DISPATCH_FRAME_BY_LAYER_AND_HOST;
import static com.imageworks.spcue.dao.postgres.DispatchQuery.FIND_LOCAL_DISPATCH_FRAME_BY_LAYER_AND_PROC;
import static com.imageworks.spcue.dao.postgres.DispatchQuery.FIND_SHOWS;
import static com.imageworks.spcue.dao.postgres.DispatchQuery.FIND_UNDER_PROCED_JOB_BY_FACILITY;
import static com.imageworks.spcue.dao.postgres.DispatchQuery.HIGHER_PRIORITY_JOB_BY_FACILITY_EXISTS;


/**
 * Dispatcher DAO
 *
 * @category DAO
 */
@Repository
public class DispatcherDaoJdbc extends AbstractJdbcDao implements DispatcherDao {

    private static final Logger logger = Logger.getLogger(DispatcherDaoJdbc.class);

    public static final RowMapper<String> PKJOB_MAPPER =
        new RowMapper<String>() {
            public String mapRow(ResultSet rs, int rowNum) throws SQLException {
                return rs.getString("pk_job");
            }
    };

    private static final RowMapper<SortableShow> SHOW_MAPPER = new RowMapper<SortableShow>() {
        public SortableShow mapRow(ResultSet rs, int rowNum) throws SQLException {
            return new SortableShow(
                    rs.getString("pk_show"),
                    rs.getFloat("float_tier"));
        }
    };

    private int threadMode(int mode) {
        if (mode == ThreadMode.ALL_VALUE)
            return mode;
        return ThreadMode.AUTO_VALUE;
    }

    /**
     * Number of milliseconds before the show cache expires and
     * a new show cache is created.
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

    /**
     * Returns a sorted list of shows that have pending jobs
     * which could benefit from the specified allocation.
     *
     * @param alloc
     * @return a sorted list of shows.
     */
    private List<SortableShow> getBookableShows(AllocationInterface alloc) {
        String key = alloc.getAllocationId();

        ShowCache cached = bookableShows.get(key);
        if (cached == null) {
            bookableShows.put(key, new ShowCache(getJdbcTemplate().query(
                    FIND_SHOWS,
                    SHOW_MAPPER, alloc.getAllocationId())));
        }
        else if (cached.isExpired()) {
            bookableShows.put(key, new ShowCache(getJdbcTemplate().query(
                    FIND_SHOWS,
                    SHOW_MAPPER, alloc.getAllocationId())));
        }

        return bookableShows.get(key).shows;
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

        for (SortableShow s: shows) {

            if (s.isSkipped(host.tags, (long) host.cores, host.memory)) {
                logger.info("skipping show " + s.getShowId());
                continue;
            }

            if (s.isSkipped(host)) {
                logger.info("skipping show " + s.getShowId() + ", over its subscription.");
                continue;
            }

            /**
             * Check if the show is over its subscription because we're using
             * cached SortableShows, we don't pull a fresh list of shows for
             * a while.  If the show is over its subscription the alloc
             * gets add to the SortableShow skipped alloc set.
             */
            if (getJdbcTemplate().queryForObject(
                    "SELECT int_burst - int_cores FROM subscription WHERE pk_show=? AND pk_alloc=?",
                    Integer.class, s.getShowId(), host.getAllocationId()) < 100) {
                s.skip(host);
                continue;
            }

            result.addAll(getJdbcTemplate().query(
                    FIND_JOBS_BY_SHOW,
                    PKJOB_MAPPER,
                    s.getShowId(), host.getFacilityId(), host.os,
                    host.idleCores, host.idleMemory,
                    threadMode(host.threadMode),
                    (host.idleGpu > 0) ? 1: 0, host.idleGpu,
                    host.getName(), numJobs * 10));

            if (result.size() < 1) {
                if (host.gpu == 0) {
                    s.skip(host.tags, host.idleCores, host.idleMemory);
                }
            }
            else {
                return result;
            }
        }
        return result;

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
        result.addAll(getJdbcTemplate().query(
                FIND_JOBS_BY_GROUP,
                PKJOB_MAPPER,
                g.getGroupId(),host.getFacilityId(), host.os,
                host.idleCores, host.idleMemory,
                threadMode(host.threadMode),
                (host.idleGpu > 0) ? 1: 0, host.idleGpu,
                host.getName(), 50));

        return result;
    }

    @Override
    public List<DispatchFrame> findNextDispatchFrames(JobInterface job,
            VirtualProc proc,  int limit) {

        if (proc.isLocalDispatch) {
            return getJdbcTemplate().query(
                    FIND_LOCAL_DISPATCH_FRAME_BY_JOB_AND_PROC,
                    FrameDaoJdbc.DISPATCH_FRAME_MAPPER,
                    proc.memoryReserved,
                    proc.gpuReserved,
                    job.getJobId(),
                    limit);
        }
        else {
            return getJdbcTemplate().query(
                    FIND_DISPATCH_FRAME_BY_JOB_AND_PROC,
                    FrameDaoJdbc.DISPATCH_FRAME_MAPPER,
                    proc.coresReserved,
                    proc.memoryReserved,
                    (proc.gpuReserved > 0) ? 1: 0, proc.gpuReserved,
                    job.getJobId(), job.getJobId(),
                    proc.hostName, limit);
        }
    }

    @Override
    public List<DispatchFrame> findNextDispatchFrames(JobInterface job,
            DispatchHost host, int limit) {

        if (host.isLocalDispatch) {
            return getJdbcTemplate().query(
                    FIND_LOCAL_DISPATCH_FRAME_BY_JOB_AND_HOST,
                    FrameDaoJdbc.DISPATCH_FRAME_MAPPER,
                    host.idleMemory,  host.idleGpu, job.getJobId(),
                    limit);

        } else {
            return getJdbcTemplate().query(
                FIND_DISPATCH_FRAME_BY_JOB_AND_HOST,
                FrameDaoJdbc.DISPATCH_FRAME_MAPPER,
                host.idleCores, host.idleMemory,
                threadMode(host.threadMode),
                (host.idleGpu > 0) ? 1: 0, host.idleGpu,
                job.getJobId(), job.getJobId(),
                host.getName(), limit);
        }
    }


    @Override
    public List<DispatchFrame> findNextDispatchFrames(LayerInterface layer,
            VirtualProc proc,  int limit) {

        if (proc.isLocalDispatch) {
            return getJdbcTemplate().query(
                    FIND_LOCAL_DISPATCH_FRAME_BY_LAYER_AND_PROC,
                    FrameDaoJdbc.DISPATCH_FRAME_MAPPER,
                    proc.memoryReserved, proc.gpuReserved,
                    layer.getLayerId(),
                    limit);
        }
        else {
            return getJdbcTemplate().query(
                    FIND_DISPATCH_FRAME_BY_LAYER_AND_PROC,
                    FrameDaoJdbc.DISPATCH_FRAME_MAPPER,
                    proc.coresReserved, proc.memoryReserved,
                    proc.gpuReserved,
                    layer.getLayerId(), layer.getLayerId(),
                    proc.hostName, limit);
        }
    }

    @Override
    public List<DispatchFrame> findNextDispatchFrames(LayerInterface layer,
            DispatchHost host, int limit) {

        if (host.isLocalDispatch) {
            return getJdbcTemplate().query(
                    FIND_LOCAL_DISPATCH_FRAME_BY_LAYER_AND_HOST,
                    FrameDaoJdbc.DISPATCH_FRAME_MAPPER,
                    host.idleMemory, host.idleGpu, layer.getLayerId(),
                    limit);

        } else {
            return getJdbcTemplate().query(
                FIND_DISPATCH_FRAME_BY_LAYER_AND_HOST,
                FrameDaoJdbc.DISPATCH_FRAME_MAPPER,
                host.idleCores, host.idleMemory,
                threadMode(host.threadMode),
                host.idleGpu, layer.getLayerId(), layer.getLayerId(),
                host.getName(), limit);
        }
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
            return getJdbcTemplate().queryForObject(
                    FIND_UNDER_PROCED_JOB_BY_FACILITY,
                    Integer.class, excludeJob.getShowId(), proc.getFacilityId(),
                    proc.os, excludeJob.getShowId(),
                    proc.getFacilityId(), proc.os,
                    proc.coresReserved, proc.memoryReserved, proc.gpuReserved,
                    proc.hostName) > 0;
         } catch (org.springframework.dao.EmptyResultDataAccessException e) {
             return false;
         }
         finally {
             logger.trace("findUnderProcedJob(Job excludeJob, VirtualProc proc) " + CueUtil.duration(start));
         }
    }

    @Override
    public boolean higherPriorityJobExists(JobDetail baseJob, VirtualProc proc) {
        long start = System.currentTimeMillis();
        try {
            return getJdbcTemplate().queryForObject(
                    HIGHER_PRIORITY_JOB_BY_FACILITY_EXISTS,
                    Boolean.class, baseJob.priority, proc.getFacilityId(),
                    proc.os, proc.getFacilityId(), proc.os,
                    proc.coresReserved, proc.memoryReserved, proc.gpuReserved,
                    proc.hostName);
        } catch (org.springframework.dao.EmptyResultDataAccessException e) {
            return false;
        }
        finally {
            logger.trace("higherPriorityJobExists(JobDetail baseJob, VirtualProc proc) " + CueUtil.duration(start));
        }
    }

    @Override
    public Set<String> findDispatchJobs(DispatchHost host,
            ShowInterface show, int numJobs) {
        LinkedHashSet<String> result = new LinkedHashSet<String>(numJobs);

        result.addAll(getJdbcTemplate().query(
                FIND_JOBS_BY_SHOW,
                PKJOB_MAPPER,
                show.getShowId(), host.getFacilityId(), host.os,
                host.idleCores, host.idleMemory,
                threadMode(host.threadMode),
                (host.idleGpu > 0) ? 1: 0, host.idleGpu,
                host.getName(), numJobs * 10));

        return result;
    }

    @Override
    public Set<String> findLocalDispatchJobs(DispatchHost host) {
        LinkedHashSet<String> result = new LinkedHashSet<String>(5);
        result.addAll(getJdbcTemplate().query(
                    FIND_JOBS_BY_LOCAL,
                    PKJOB_MAPPER,
                    host.getHostId(), host.getFacilityId(),
                    host.os, host.getHostId(), host.getFacilityId(), host.os));

        return result;
    }
}

