
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

import com.imageworks.spcue.dao.AbstractJdbcDao;
import org.springframework.dao.DataAccessException;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.EntityModificationError;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.SubscriptionEntity;
import com.imageworks.spcue.SubscriptionInterface;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.SubscriptionDao;
import com.imageworks.spcue.util.SqlUtil;
import org.springframework.stereotype.Repository;

@Repository
public class SubscriptionDaoJdbc extends AbstractJdbcDao implements SubscriptionDao {

    private static final String IS_SHOW_OVER_SIZE =
        "SELECT " +
            "COUNT(1) " +
        "FROM " +
            "subscription s " +
        "WHERE " +
            "s.pk_show = ? " +
         "AND " +
            "s.pk_alloc = ? " +
         "AND " +
            "s.int_cores > s.int_size ";

    public boolean isShowOverSize(ShowInterface show, AllocationInterface alloc) {
        try {
            return getJdbcTemplate().queryForObject(IS_SHOW_OVER_SIZE,
                    Integer.class, show.getShowId(), alloc.getAllocationId()) > 0;
        } catch (EmptyResultDataAccessException e) {
            return false;
        }
    }

    public boolean isShowOverSize(VirtualProc proc) {
        try {
            return getJdbcTemplate().queryForObject(IS_SHOW_OVER_SIZE,
                    Integer.class, proc.getShowId(), proc.getAllocationId()) > 0;
        } catch (EmptyResultDataAccessException e) {
            return false;
        }
    }

    private static final  String IS_SHOW_AT_OR_OVER_SIZE =
        "SELECT " +
            "COUNT(1) " +
        "FROM " +
            "subscription s " +
        "WHERE " +
            "s.pk_show = ? " +
        "AND " +
            "s.pk_alloc = ? " +
        "AND " +
            "s.int_cores >= s.int_size ";

    public boolean isShowAtOrOverSize(ShowInterface show, AllocationInterface alloc) {
        try {
            return getJdbcTemplate().queryForObject(IS_SHOW_AT_OR_OVER_SIZE,
                    Integer.class, show.getShowId(), alloc.getAllocationId()) > 0;
        } catch (EmptyResultDataAccessException e) {
            return false;
        }
    }

    private static final  String IS_SHOW_OVER_BURST =
        "SELECT " +
            "COUNT(1) " +
        "FROM " +
            "subscription s " +
        "WHERE " +
            "s.pk_show = ? " +
        "AND " +
            "s.pk_alloc = ? " +
        "AND " +
            "s.int_cores + ? > s.int_burst";

    @Override
    public boolean isShowOverBurst(ShowInterface show, AllocationInterface alloc, int coreUnits) {
        try {
            return getJdbcTemplate().queryForObject(IS_SHOW_OVER_BURST,
                    Integer.class, show.getShowId(), alloc.getAllocationId(),
                    coreUnits) > 0;
        } catch (EmptyResultDataAccessException e) {
            return true;
        }
    }

    private static final  String IS_SHOW_AT_OR_OVER_BURST =
        "SELECT " +
            "COUNT(1) " +
        "FROM " +
            "subscription s " +
        "WHERE " +
            "s.pk_show = ? " +
        "AND " +
            "s.pk_alloc = ? " +
        "AND " +
            "s.int_cores >= s.int_burst";

    @Override
    public boolean isShowAtOrOverBurst(ShowInterface show, AllocationInterface alloc) {
        try {
            return getJdbcTemplate().queryForObject(IS_SHOW_AT_OR_OVER_BURST,
                    Integer.class, show.getShowId(), alloc.getAllocationId()) > 0;
        } catch (EmptyResultDataAccessException e) {
            return true;
        }
    }

    private static final String GET_SUB =
        "SELECT " +
            "subscription.pk_alloc," +
            "subscription.pk_show,"+
            "subscription.int_size,"+
            "subscription.int_burst,"+
            "subscription.pk_subscription,"+
            "(alloc.str_name || '.' || show.str_name) AS str_name " +
        "FROM " +
            "subscription," +
            "alloc," +
            "show," +
            "facility " +
        "WHERE " +
            "subscription.pk_show = show.pk_show " +
        "AND " +
            "subscription.pk_alloc = alloc.pk_alloc " +
        "AND " +
            "alloc.pk_facility = facility.pk_facility ";

    public static RowMapper<SubscriptionEntity> SUB_MAPPER = new RowMapper<SubscriptionEntity>() {
        public SubscriptionEntity mapRow(ResultSet rs, int rowNum) throws SQLException {
            SubscriptionEntity s = new SubscriptionEntity();
            s.allocationId = rs.getString("pk_alloc");
            s.burst = rs.getInt("int_burst");
            s.size = rs.getInt("int_size");
            s.name = rs.getString("str_name");
            s.showId = rs.getString("pk_show");
            s.id = rs.getString("pk_subscription");
            return s;
        }
    };

    public SubscriptionEntity getSubscriptionDetail(String id) {
        return getJdbcTemplate().queryForObject(
                GET_SUB + " AND pk_subscription=?",
                SUB_MAPPER, id);
    }

    private static final String INSERT_SUBSCRIPTION =
        "INSERT INTO " +
            "subscription " +
        "( " +
            "pk_subscription, pk_alloc, pk_show, int_size, int_burst"+
        ") " +
        "VALUES (?,?,?,?,?)";

    public void insertSubscription(SubscriptionEntity detail) {
        detail.id = SqlUtil.genKeyRandom();
        getJdbcTemplate().update(INSERT_SUBSCRIPTION,
                detail.id, detail.allocationId, detail.showId, detail.size, detail.burst);
    }
    private static final String HAS_RUNNING_PROCS =
        "SELECT " +
            "COUNT(1) " +
        "FROM " +
            "subscription s " +
        "WHERE " +
            "s.pk_subscription=? " +
        "AND " +
            "s.int_cores > 0 ";

    public boolean hasRunningProcs(SubscriptionInterface sub) {
        try {
            return getJdbcTemplate().queryForObject(HAS_RUNNING_PROCS,
                    Integer.class, sub.getSubscriptionId()) > 0;
        } catch (DataAccessException e) {
            return false;
        }
    }

    public void deleteSubscription(SubscriptionInterface sub) {
        if (hasRunningProcs(sub)) {
            throw new EntityModificationError("You cannot delete a subscription with running procs");
        }
        getJdbcTemplate().update(
                "DELETE FROM subscription WHERE pk_subscription=?",
                sub.getSubscriptionId());
    }

    public void updateSubscriptionSize(SubscriptionInterface sub, int size) {
        getJdbcTemplate().update(
                "UPDATE subscription SET int_size=? WHERE pk_subscription=?",
                size, sub.getSubscriptionId());
    }

    public void updateSubscriptionBurst(SubscriptionInterface sub, int size) {
        getJdbcTemplate().update(
                "UPDATE subscription SET int_burst=? WHERE pk_subscription=?",
                size, sub.getSubscriptionId());
    }
}

