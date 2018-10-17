
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

import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.MaintenanceTask;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.dao.MaintenanceDao;

public class MaintenanceDaoJdbc extends JdbcDaoSupport implements MaintenanceDao {

    private static final String HOST_DOWN_INTERVAL = "interval '300' second";

    private static final String UPDATE_HOSTS_DOWN =
        "UPDATE " +
            "host_stat " +
        "SET " +
            "str_state=? " +
        "WHERE " +
            "str_state='UP' " +
        "AND " +
            "systimestamp - ts_ping > " + HOST_DOWN_INTERVAL;

    public int setUpHostsToDown() {
        return getJdbcTemplate().update(UPDATE_HOSTS_DOWN,
                HardwareState.DOWN.toString());
    }

    public static final String LOCK_TASK =
        "UPDATE " +
            "task_lock " +
        "SET " +
            "int_lock = ?, " +
            "ts_lastrun = systimestamp " +
        "WHERE " +
            "str_name= ? "+
        "AND " +
            "(int_lock = ? OR ? - int_lock > int_timeout)";

    public boolean lockTask(MaintenanceTask task) {
        long now = System.currentTimeMillis();
        return getJdbcTemplate().update(LOCK_TASK,
                now, task.toString(), 0, now) == 1;
    }

    public static final String LOCK_TASK_MIN =
        "UPDATE " +
            "task_lock " +
        "SET " +
            "int_lock = ?, " +
            "ts_lastrun = systimestamp " +
        "WHERE " +
            "str_name= ? "+
        "AND " +
            "int_lock = ? " +
        "AND " +
            "interval_to_seconds(systimestamp - ts_lastrun) > ? ";

    public boolean lockTask(MaintenanceTask task, int minutes) {
        long now = System.currentTimeMillis();
        return getJdbcTemplate().update(LOCK_TASK_MIN,
                now, task.toString(), 0, minutes * 60) == 1;
    }


    public void unlockTask(MaintenanceTask task) {
        getJdbcTemplate().update(
                "UPDATE task_lock SET int_lock = 0 WHERE str_name=?", task.toString());
    }
}

