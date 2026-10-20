
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

import java.util.List;

import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.dao.HistoricalDao;
import com.imageworks.spcue.grpc.job.JobState;

public class HistoricalDaoJdbc extends JdbcDaoSupport implements HistoricalDao {

    // spotless:off
    private static final String GET_FINISHED_JOBS =
            JobDaoJdbc.GET_JOB
            + "WHERE job.str_state = ? "
            + "AND current_timestamp - job.ts_stopped > ";
    // spotless:on

    public List<JobInterface> getFinishedJobs(int cutoffHours) {
        String interval = "interval '" + cutoffHours + "' hour";
        return getJdbcTemplate().query(GET_FINISHED_JOBS + interval, JobDaoJdbc.JOB_MAPPER,
                JobState.FINISHED.toString());
    }

    public void transferJob(JobInterface job) {
        /**
         * All of the historical transfer happens inside of triggers
         */
        getJdbcTemplate().update("DELETE FROM job WHERE pk_job=?", job.getJobId());
    }

    public FrameHistoryDrain drainFrameHistory(int limit, boolean safe) {
        return getJdbcTemplate().queryForObject(
                "SELECT drained, skipped, merged FROM frame_history_drain(?, false, ?)",
                (rs, rowNum) -> new FrameHistoryDrain(rs.getInt("drained"), rs.getInt("skipped"),
                        rs.getInt("merged")),
                limit, safe);
    }

    // spotless:off
    private static final String GET_FRAME_HISTORY_BACKLOG =
            "SELECT "
                + "COALESCE((SELECT max(id) FROM frame_history_queue) - oldest.id + 1, 0) AS depth, "
                + "COALESCE(epoch(current_timestamp) - oldest.int_ts, 0) AS age "
            + "FROM (SELECT 1) one "
            + "LEFT JOIN (SELECT id, int_ts FROM frame_history_queue ORDER BY id LIMIT 1) oldest "
                + "ON true";
    // spotless:on

    public FrameHistoryBacklog getFrameHistoryBacklog() {
        return getJdbcTemplate().queryForObject(GET_FRAME_HISTORY_BACKLOG,
                (rs, rowNum) -> new FrameHistoryBacklog(rs.getLong("depth"), rs.getLong("age")));
    }
}
