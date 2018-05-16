
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
import java.util.List;

import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.Deed;
import com.imageworks.spcue.Owner;
import com.imageworks.spcue.Host;
import com.imageworks.spcue.dao.DeedDao;
import com.imageworks.spcue.util.SqlUtil;

public class DeedDaoJdbc extends JdbcDaoSupport implements DeedDao {

    public static final RowMapper<Deed>
        DEED_MAPPER = new RowMapper<Deed>() {
            public Deed mapRow(ResultSet rs, int rowNum) throws SQLException {
                Deed o = new Deed();
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
    public boolean deleteDeed(Deed deed) {
        return getJdbcTemplate().update(
                "DELETE FROM deed WHERE pk_deed = ?",
                deed.getId()) > 0;
    }

    @Override
    public boolean deleteDeed(Host host) {
        return getJdbcTemplate().update(
                "DELETE FROM deed WHERE pk_host = ?",
                host.getHostId()) > 0;
    }

    @Override
    public void deleteDeeds(Owner owner) {
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

    public Deed insertDeed(Owner owner, Host host) {
        Deed deed = new Deed();
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
    public Deed getDeed(String id) {
        return getJdbcTemplate().queryForObject(
                QUERY_FOR_DEED + " AND pk_deed = ?",
                DEED_MAPPER, id);
    }

    @Override
    public List<Deed> getDeeds(Owner owner) {
        return getJdbcTemplate().query(
                QUERY_FOR_DEED + " AND owner.pk_owner = ?",
                DEED_MAPPER, owner.getId());
    }

    @Override
    public void setBlackoutTime(Deed deed, int startSeconds, int stopSeconds) {
        getJdbcTemplate().update(
                "UPDATE deed SET int_blackout_start = ?, " +
                "int_blackout_stop = ? WHERE deed.pk_deed = ?",
                startSeconds, stopSeconds, deed.getId());
    }

    @Override
    public void updateBlackoutTimeEnabled(Deed deed, boolean bool) {
        getJdbcTemplate().update(
                "UPDATE deed SET b_blackout = ? WHERE deed.pk_deed = ?",
                bool, deed.getId());
    }
}

