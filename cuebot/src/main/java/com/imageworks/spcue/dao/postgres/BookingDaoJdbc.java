
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
import java.util.Calendar;
import java.util.List;

import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.dao.BookingDao;
import com.imageworks.spcue.dispatcher.ResourceReservationFailureException;
import com.imageworks.spcue.util.SqlUtil;

public class BookingDaoJdbc extends
    JdbcDaoSupport implements BookingDao {

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
}

