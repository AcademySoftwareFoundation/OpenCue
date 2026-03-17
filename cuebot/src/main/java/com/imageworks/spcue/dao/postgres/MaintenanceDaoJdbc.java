
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

import com.imageworks.spcue.MaintenanceTask;
import com.imageworks.spcue.dao.MaintenanceDao;
import com.imageworks.spcue.grpc.host.HardwareState;

public class MaintenanceDaoJdbc extends JdbcDaoSupport implements MaintenanceDao {

    private static final String HOST_DOWN_INTERVAL = "interval '300' second";

    private static final String UPDATE_HOSTS_DOWN =
            "UPDATE " + "host_stat " + "SET " + "str_state = ? " + "WHERE " + "str_state = 'UP' "
                    + "AND " + "current_timestamp - ts_ping > " + HOST_DOWN_INTERVAL;

    public int setUpHostsToDown() {
        return getJdbcTemplate().update(UPDATE_HOSTS_DOWN, HardwareState.DOWN.toString());
    }

    public static final String LOCK_TASK = "UPDATE " + "task_lock " + "SET " + "int_lock = ?, "
            + "ts_lastrun = current_timestamp " + "WHERE " + "str_name = ? " + "AND "
            + "(int_lock = ? OR ? - int_lock > int_timeout)";

    public boolean lockTask(MaintenanceTask task) {
        long now = System.currentTimeMillis();
        return getJdbcTemplate().update(LOCK_TASK, now, task.toString(), 0, now) == 1;
    }

    public static final String LOCK_TASK_MIN = "UPDATE " + "task_lock " + "SET " + "int_lock = ?, "
            + "ts_lastrun = current_timestamp " + "WHERE " + "str_name= ? " + "AND "
            + "int_lock = ? " + "AND " + "interval_to_seconds(current_timestamp - ts_lastrun) > ? ";

    public boolean lockTask(MaintenanceTask task, int minutes) {
        long now = System.currentTimeMillis();
        return getJdbcTemplate().update(LOCK_TASK_MIN, now, task.toString(), 0, minutes * 60) == 1;
    }

    public void unlockTask(MaintenanceTask task) {
        getJdbcTemplate().update("UPDATE task_lock SET int_lock = 0 WHERE str_name=?",
                task.toString());
    }

    private static final String RECALCULATE_SUBS = "SELECT recalculate_subs()";

    @Override
    public void recalculateSubscriptions() {
        getJdbcTemplate().execute(RECALCULATE_SUBS);
    }

    // spotless:off
    /**
     * Finds active, non-composite depends whose depended-upon entity has already completed
     * successfully. Composite depends (b_composite = true) are parent depends that are
     * automatically satisfied when all their child depends are satisfied, so they should
     * not be resolved directly.
     *
     * Section 1: Job-level depends (JOB_ON_JOB, LAYER_ON_JOB, FRAME_ON_JOB) where
     *   every frame in the depended-upon job has SUCCEEDED or been EATEN.
     * Section 2: Layer-level depends (JOB_ON_LAYER, LAYER_ON_LAYER, FRAME_ON_LAYER) where
     *   every frame in the depended-upon layer has SUCCEEDED or been EATEN.
     * Section 3: Frame-level depends (JOB_ON_FRAME, LAYER_ON_FRAME, FRAME_ON_FRAME) where
     *   the specific depended-upon frame has SUCCEEDED or been EATEN.
     */
    private static final String FIND_STALE_DEPEND_IDS =
            // Section 1: Job-level depends where all frames in the job succeeded or were eaten.
            // Pre-filter on job.str_state = 'FINISHED' leverages the i_job_str_state index to
            // skip depends on active jobs. A FINISHED job may still have DEAD frames, so we
            // also verify frame states via NOT EXISTS.
            "SELECT pk_depend FROM depend d "
            + "JOIN job j ON j.pk_job = d.pk_job_depend_on AND j.str_state = 'FINISHED' "
            + "WHERE d.b_active = true "
            + "AND d.b_composite = false "
            + "AND d.pk_layer_depend_on IS NULL "
            + "AND d.pk_frame_depend_on IS NULL "
            + "AND d.str_type IN ('JOB_ON_JOB', 'LAYER_ON_JOB', 'FRAME_ON_JOB') "
            + "AND NOT EXISTS ("
                + "SELECT 1 FROM frame f "
                + "WHERE f.pk_job = d.pk_job_depend_on "
                + "AND f.str_state NOT IN ('SUCCEEDED', 'EATEN')) "

            + "UNION "

            // Section 2: Layer-level depends where all frames in the layer succeeded or were eaten.
            + "SELECT pk_depend FROM depend d "
            + "WHERE d.b_active = true "
            + "AND d.b_composite = false "
            + "AND d.pk_layer_depend_on IS NOT NULL "
            + "AND d.str_type IN ('JOB_ON_LAYER', 'LAYER_ON_LAYER', 'FRAME_ON_LAYER') "
            + "AND NOT EXISTS ("
                + "SELECT 1 FROM frame f "
                + "WHERE f.pk_layer = d.pk_layer_depend_on "
                + "AND f.str_state NOT IN ('SUCCEEDED', 'EATEN')) "

            + "UNION "

            // Section 3: Frame-level depends where the specific frame succeeded or was eaten.
            + "SELECT pk_depend FROM depend d "
            + "WHERE d.b_active = true "
            + "AND d.b_composite = false "
            + "AND d.pk_frame_depend_on IS NOT NULL "
            + "AND d.str_type IN ('JOB_ON_FRAME', 'LAYER_ON_FRAME', 'FRAME_ON_FRAME') "
            + "AND EXISTS ("
                + "SELECT 1 FROM frame f "
                + "WHERE f.pk_frame = d.pk_frame_depend_on "
                + "AND f.str_state IN ('SUCCEEDED', 'EATEN')) "

            + "LIMIT ?";
    // spotless:on

    @Override
    public List<String> findStaleDependIds(int limit) {
        return getJdbcTemplate().queryForList(FIND_STALE_DEPEND_IDS, String.class, limit);
    }

    // spotless:off
    private static final String FIX_STUCK_DEPEND_COUNTS =
            "UPDATE frame SET int_depend_count = 0 "
            + "WHERE pk_frame IN ("
                + "SELECT f.pk_frame FROM frame f "
                + "WHERE f.str_state = 'DEPEND' "
                + "AND f.int_depend_count > 0 "
                + "AND NOT EXISTS ("
                    + "SELECT 1 FROM depend d "
                    + "WHERE d.b_active = true "
                    + "AND d.pk_job_depend_er = f.pk_job "
                    + "AND ("
                        + "d.pk_frame_depend_er = f.pk_frame "
                        + "OR (d.pk_layer_depend_er = f.pk_layer AND d.pk_frame_depend_er IS NULL) "
                        + "OR (d.pk_layer_depend_er IS NULL AND d.pk_frame_depend_er IS NULL)"
                    + ")"
                + ") "
                + "LIMIT ?"
            + ")";
    // spotless:on

    @Override
    public int fixStuckDependCounts(int limit) {
        return getJdbcTemplate().update(FIX_STUCK_DEPEND_COUNTS, limit);
    }
}
