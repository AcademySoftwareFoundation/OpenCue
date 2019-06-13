
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
import org.apache.commons.lang.StringUtils;
import org.springframework.dao.DataAccessException;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.ShowEntity;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.util.SqlUtil;
import org.springframework.stereotype.Repository;

@Repository
public class ShowDaoJdbc extends AbstractJdbcDao implements ShowDao {

    private static final RowMapper<ShowEntity> SHOW_MAPPER =
        new RowMapper<ShowEntity>() {
            public ShowEntity mapRow(ResultSet rs, int rowNum) throws SQLException {
                ShowEntity show = new ShowEntity();
                show.name = rs.getString("str_name");
                show.id = rs.getString("pk_show");
                show.defaultMaxCores = rs.getInt("int_default_max_cores");
                show.defaultMinCores = rs.getInt("int_default_min_cores");
                show.active = rs.getBoolean("b_active");

                if (rs.getString("str_comment_email") != null) {
                    show.commentMail = rs.getString("str_comment_email").split(",");
                }
                else {
                    show.commentMail = new String[0];
                }
                return show;
            }
    };

    private static final String GET_SHOW =
        "SELECT " +
            "show.pk_show, " +
            "show.int_default_max_cores, " +
            "show.int_default_min_cores, " +
            "show.str_name, " +
            "show.b_active, " +
            "show.str_comment_email " +
        "FROM " +
            "show ";

    private static final String GET_SHOW_BY_ALIAS =
        "SELECT " +
            "show.pk_show, " +
            "show.int_default_max_cores, " +
            "show.int_default_min_cores, " +
            "show_alias.str_name, " +
            "show.b_active, " +
            "show.str_comment_email " +
        "FROM " +
            "show, " +
            "show_alias " +
        "WHERE " +
            "show.pk_show = show_alias.pk_show " ;

    public ShowEntity findShowDetail(String name) {
        try {
            return getJdbcTemplate().queryForObject(GET_SHOW + "WHERE show.str_name=?",
                    SHOW_MAPPER, name);
        } catch (EmptyResultDataAccessException e) {
            return getJdbcTemplate().queryForObject(GET_SHOW_BY_ALIAS + "AND show_alias.str_name = ?",
                    SHOW_MAPPER, name);
        }
    }

    public ShowEntity getShowDetail(String id) {
        return getJdbcTemplate().queryForObject(
                GET_SHOW + "WHERE show.pk_show=?", SHOW_MAPPER, id);
    }

    private static final String GET_PREFERRED_SHOW =
        "SELECT " +
            "show.pk_show, " +
            "show.int_default_max_cores, " +
            "show.int_default_min_cores, " +
            "show.str_name, " +
            "show.b_active, " +
            "show.str_comment_email " +
        "FROM " +
            "show, "+
            "owner,"+
            "deed " +
        "WHERE " +
            "show.pk_show = owner.pk_show " +
        "AND " +
            "deed.pk_owner = owner.pk_owner " +
        "AND " +
            "deed.pk_host = ?";

    public ShowEntity getShowDetail(HostInterface host) {
        return getJdbcTemplate().queryForObject(
                GET_PREFERRED_SHOW, SHOW_MAPPER, host.getHostId());
    }

    private static final String INSERT_SHOW =
        "INSERT INTO show (pk_show,str_name) VALUES (?,?)";

    public void insertShow(ShowEntity show) {
        show.id = SqlUtil.genKeyRandom();
        getJdbcTemplate().update(INSERT_SHOW, show.id, show.name);
    }

    private static final String SHOW_EXISTS =
        "SELECT " +
            "COUNT(show.pk_show) " +
        "FROM " +
            "show LEFT JOIN show_alias ON (show.pk_show = show_alias.pk_show )" +
        "WHERE " +
            "(show.str_name = ? OR show_alias.str_name = ?) ";
    public boolean showExists(String name) {
        try {
            return getJdbcTemplate().queryForObject(SHOW_EXISTS,
                    Integer.class, name, name) >= 1;
        } catch (DataAccessException e) {
            return false;
        }
    }

    @Override
    public void delete(ShowInterface s) {
        getJdbcTemplate().update("DELETE FROM point WHERE pk_show=?",
                s.getShowId());
        getJdbcTemplate().update("DELETE FROM folder WHERE pk_show=?",
                s.getShowId());
        getJdbcTemplate().update("DELETE FROM folder WHERE pk_show=?",
                s.getShowId());
        getJdbcTemplate().update("DELETE FROM show_alias WHERE pk_show=?",
                s.getShowId());
        getJdbcTemplate().update("DELETE FROM show WHERE pk_show=?",
                s.getShowId());
    }

    public void updateShowDefaultMinCores(ShowInterface s, int val) {
        if (val < 0) {
            String msg = "Invalid argument, default min cores " + val +
                    "must be greater tham 0";
            throw new IllegalArgumentException(msg);
        }
        getJdbcTemplate().update(
                "UPDATE show SET int_default_min_cores=? WHERE pk_show=?",
                val, s.getShowId());
    }

    public void updateShowDefaultMaxCores(ShowInterface s, int val) {
        if (val < 0) {
            String msg = "Invalid argument, default max cores " + val +
                    "must be greater tham 0";
            throw new IllegalArgumentException(msg);
        }
        getJdbcTemplate().update(
                "UPDATE show SET int_default_max_cores=? WHERE pk_show=?",
                val, s.getShowId());
    }

    @Override
    public void updateBookingEnabled(ShowInterface s, boolean enabled) {
        getJdbcTemplate().update(
                "UPDATE show SET b_booking_enabled = ? WHERE pk_show=?",
                enabled, s.getShowId());
    }

    @Override
    public void updateDispatchingEnabled(ShowInterface s, boolean enabled) {
        getJdbcTemplate().update(
                "UPDATE show SET b_dispatch_enabled = ? WHERE pk_show=?",
                enabled, s.getShowId());
    }

    @Override
    public void updateActive(ShowInterface s, boolean enabled) {
        getJdbcTemplate().update(
                "UPDATE show SET b_active= ? WHERE pk_show=?",
                enabled, s.getShowId());
    }

    @Override
    public void updateShowCommentEmail(ShowInterface s, String[] email) {
        getJdbcTemplate().update(
                "UPDATE show SET str_comment_email = ? WHERE pk_show=?",
                StringUtils.join(email, ","), s.getShowId());
    }

    @Override
    public void updateFrameCounters(ShowInterface s, int exitStatus) {
        String col = "int_frame_success_count = int_frame_success_count + 1";
        if (exitStatus > 0) {
            col = "int_frame_fail_count = int_frame_fail_count + 1";
        }
        getJdbcTemplate().update(
                "UPDATE show SET " + col + " WHERE pk_show=?", s.getShowId());
    }
}

