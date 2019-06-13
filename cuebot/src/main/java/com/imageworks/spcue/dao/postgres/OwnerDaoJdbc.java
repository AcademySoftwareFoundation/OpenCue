
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
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.Entity;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.OwnerEntity;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.dao.OwnerDao;
import com.imageworks.spcue.util.SqlUtil;
import org.springframework.stereotype.Repository;

@Repository
public class OwnerDaoJdbc  extends AbstractJdbcDao implements OwnerDao {

    public static final RowMapper<OwnerEntity>
        OWNER_MAPPER = new RowMapper<OwnerEntity>() {
            public OwnerEntity mapRow(ResultSet rs, int rowNum) throws SQLException {
                OwnerEntity o = new OwnerEntity();
                o.id = rs.getString("pk_owner");
                o.name = rs.getString("str_username");
                return o;
            }
    };

    @Override
    public boolean deleteOwner(Entity owner) {
        return getJdbcTemplate().update(
                "DELETE FROM owner WHERE pk_owner = ?",
                owner.getId()) > 0;
    }

    private static final String QUERY_FOR_OWNER =
        "SELECT " +
            "owner.pk_owner," +
            "owner.str_username " +
        "FROM " +
            "owner ";

    @Override
    public OwnerEntity findOwner(String name) {
        try {
            return getJdbcTemplate().queryForObject(
                    QUERY_FOR_OWNER + " WHERE str_username = ?",
                    OWNER_MAPPER, name);
        } catch (EmptyResultDataAccessException e) {
            throw new EmptyResultDataAccessException(
                    "Failed to find owner: " + name, 1);
        }
    }

    @Override
    public OwnerEntity getOwner(String id) {
        return getJdbcTemplate().queryForObject(
                QUERY_FOR_OWNER + " WHERE pk_owner = ?",
                OWNER_MAPPER, id);
    }

    @Override
    public OwnerEntity getOwner(HostInterface host) {
        return getJdbcTemplate().queryForObject(
                QUERY_FOR_OWNER +
                "WHERE " +
                    "pk_owner = (" +
                "SELECT "+
                    "pk_owner " +
                "FROM " +
                    "deed " +
                "WHERE " +
                    "pk_host = ?)",
                OWNER_MAPPER, host.getHostId());
    }

    public boolean isOwner(OwnerEntity owner, HostInterface host) {
        return  getJdbcTemplate().queryForObject(
                "SELECT COUNT(1) FROM host, deed" +
                " WHERE host.pk_host = deed.pk_host AND deed.pk_owner=?",
                Integer.class, owner.getId()) > 0;
    }

    private static final String INSERT_OWNER =
        "INSERT INTO " +
            "owner " +
        "(" +
            "pk_owner," +
            "pk_show," +
            "str_username " +
        ") " +
        "VALUES (?,?,?)";

    @Override
    public void insertOwner(OwnerEntity owner, ShowInterface show) {
        owner.id = SqlUtil.genKeyRandom();
        getJdbcTemplate().update(INSERT_OWNER,
                owner.id, show.getShowId(), owner.name);
    }

    @Override
    public void updateShow(Entity owner, ShowInterface show) {
        getJdbcTemplate().update(
                "UPDATE owner SET pk_show = ? WHERE pk_owner = ?",
                show.getShowId(), owner.getId());
    }
}

