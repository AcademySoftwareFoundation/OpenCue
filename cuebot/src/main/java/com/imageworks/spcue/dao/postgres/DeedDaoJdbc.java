
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
import java.util.List;

import com.imageworks.spcue.dao.AbstractJdbcDao;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.DeedEntity;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.OwnerEntity;
import com.imageworks.spcue.dao.DeedDao;
import com.imageworks.spcue.util.SqlUtil;
import org.springframework.stereotype.Repository;

@Repository
public class DeedDaoJdbc extends AbstractJdbcDao implements DeedDao {

    public static final RowMapper<DeedEntity>
        DEED_MAPPER = new RowMapper<DeedEntity>() {
            public DeedEntity mapRow(ResultSet rs, int rowNum) throws SQLException {
                DeedEntity o = new DeedEntity();
                o.id = rs.getString("pk_deed");
                o.owner = rs.getString("str_username");
                o.host = rs.getString("str_hostname");
                o.isBlackoutEnabled = rs.getBoolean("b_blackout");
                o.blackoutStart = rs.getInt("int_blackout_start");
                o.blackoutStop = rs.getInt("int_blackout_stop");
                return o;
        }
    };

    @Override
    public boolean deleteDeed(DeedEntity deed) {
        return getJdbcTemplate().update(
                "DELETE FROM deed WHERE pk_deed = ?",
                deed.getId()) > 0;
    }

    @Override
    public boolean deleteDeed(HostInterface host) {
        return getJdbcTemplate().update(
                "DELETE FROM deed WHERE pk_host = ?",
                host.getHostId()) > 0;
    }

    @Override
    public void deleteDeeds(OwnerEntity owner) {
        getJdbcTemplate().update(
                "DELETE FROM deed WHERE pk_owner = ?",
                owner.getId());
    }

    private static final String INSERT_DEED =
        "INSERT INTO " +
            "deed " +
        "("+
            "pk_deed,"+
            "pk_owner,"+
            "pk_host " +
        ") "+
        "VALUES (?,?,?)";

    public DeedEntity insertDeed(OwnerEntity owner, HostInterface host) {
        DeedEntity deed = new DeedEntity();
        deed.id = SqlUtil.genKeyRandom();
        deed.host = host.getName();
        deed.owner = owner.name;

        getJdbcTemplate().update(INSERT_DEED,
                deed.getId(), owner.getId(), host.getId());

        return deed;
    }

    private static final String QUERY_FOR_DEED =
        "SELECT " +
            "deed.pk_deed, "+
            "deed.b_blackout,"+
            "deed.int_blackout_start,"+
            "deed.int_blackout_stop, " +
            "host.str_name as str_hostname, " +
            "owner.str_username " +
        "FROM " +
            "deed,"+
            "host,"+
            "owner " +
        "WHERE " +
            "deed.pk_owner = owner.pk_owner " +
        "AND " +
            "deed.pk_host = host.pk_host ";

    @Override
    public DeedEntity getDeed(String id) {
        return getJdbcTemplate().queryForObject(
                QUERY_FOR_DEED + " AND pk_deed = ?",
                DEED_MAPPER, id);
    }

    @Override
    public List<DeedEntity> getDeeds(OwnerEntity owner) {
        return getJdbcTemplate().query(
                QUERY_FOR_DEED + " AND owner.pk_owner = ?",
                DEED_MAPPER, owner.getId());
    }

    @Override
    public void setBlackoutTime(DeedEntity deed, int startSeconds, int stopSeconds) {
        getJdbcTemplate().update(
                "UPDATE deed SET int_blackout_start = ?, " +
                "int_blackout_stop = ? WHERE deed.pk_deed = ?",
                startSeconds, stopSeconds, deed.getId());
    }

    @Override
    public void updateBlackoutTimeEnabled(DeedEntity deed, boolean bool) {
        getJdbcTemplate().update(
                "UPDATE deed SET b_blackout = ? WHERE deed.pk_deed = ?",
                bool, deed.getId());
    }
}

