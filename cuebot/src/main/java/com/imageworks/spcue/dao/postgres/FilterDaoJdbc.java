
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

import java.sql.CallableStatement;
import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

import com.imageworks.spcue.dao.AbstractJdbcDao;
import org.springframework.jdbc.core.CallableStatementCreator;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.SqlParameter;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.FilterEntity;
import com.imageworks.spcue.FilterInterface;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.dao.FilterDao;
import com.imageworks.spcue.grpc.filter.FilterType;
import com.imageworks.spcue.util.SqlUtil;
import org.springframework.stereotype.Repository;

/**
 * A DAO class for loading Filters, Actions, and Matchers.  Part of the
 * job filtering system.
 *
 * @category DAO
 */
@Repository
public class FilterDaoJdbc extends AbstractJdbcDao implements FilterDao {

    private static final String GET_FILTER =
        "SELECT " +
            "filter.* " +
        "FROM "+
            "filter ";

    private static final String GET_ACTIVE_FILTERS =
        "SELECT " +
            "filter.*" +
        "FROM " +
            "filter " +
        "WHERE " +
            "b_enabled = true "+
        "AND " +
            "pk_show=? " +
        "ORDER BY " +
            "f_order ASC";

    private static final String GET_FILTERS =
        "SELECT " +
            "filter.*" +
        "FROM " +
            "filter " +
        "WHERE " +
            "pk_show=? " +
        "ORDER BY " +
            "f_order ASC";

    public static final RowMapper<FilterEntity> FILTER_DETAIL_MAPPER = new RowMapper<FilterEntity>() {
        public FilterEntity mapRow(ResultSet rs, int rowNum) throws SQLException {
            FilterEntity d = new FilterEntity();
            d.type = FilterType.valueOf(rs.getString("str_type"));
            d.id = rs.getString("pk_filter");
            d.name = rs.getString("str_name");
            d.showId = rs.getString("pk_show");
            d.enabled = rs.getBoolean("b_enabled");
            d.order = rs.getFloat("f_order");
            return d;
        }
    };

    public List<FilterEntity> getActiveFilters(ShowInterface show) {
        return getJdbcTemplate().query(
                GET_ACTIVE_FILTERS, FILTER_DETAIL_MAPPER, show.getShowId());
    }

    public List<FilterEntity> getFilters(ShowInterface show) {
        return getJdbcTemplate().query(
                GET_FILTERS, FILTER_DETAIL_MAPPER, show.getShowId());
    }

    public void deleteFilter(FilterInterface f) {
        getJdbcTemplate().update(
                "DELETE FROM action WHERE pk_filter=?",f.getFilterId());
        getJdbcTemplate().update(
                "DELETE FROM matcher WHERE pk_filter=?",f.getFilterId());
        getJdbcTemplate().update(
                "DELETE FROM filter WHERE pk_filter=?",f.getFilterId());
        reorderFilters(f);
    }

    private static final String INSERT_FILTER =
        "INSERT INTO " +
            "filter "+
        "(" +
            "pk_filter," +
            "pk_show,"+
            "str_name,"+
            "str_type,"+
            "f_order "+
        ") VALUES (?,?,?,?,(SELECT COALESCE(MAX(f_order)+1,1) FROM filter WHERE pk_show=?))";

    public void insertFilter(FilterEntity f) {
        f.id = SqlUtil.genKeyRandom();
        getJdbcTemplate().update(INSERT_FILTER,
                f.id, f.getShowId(),f.name, f.type.toString(), f.getShowId());
        reorderFilters(f);
    }

    public void updateSetFilterEnabled(FilterInterface f, boolean enabled) {
        getJdbcTemplate().update(
                "UPDATE filter SET b_enabled=? WHERE pk_filter=?",
                enabled, f.getFilterId());
    }

    public void updateSetFilterName(FilterInterface f, String name) {
        getJdbcTemplate().update(
                "UPDATE filter SET str_name=? WHERE pk_filter=?",
                name, f.getFilterId());
    }

    public void updateSetFilterOrder(FilterInterface f, double order) {
        getJdbcTemplate().update(
                "UPDATE filter SET f_order=? - 0.1 WHERE pk_filter=?",
                order, f.getFilterId());
        reorderFilters(f);
    }

    public void lowerFilterOrder(FilterInterface f, int by) {
        double lower_by = by + 0.1;
        getJdbcTemplate().update(
                "UPDATE filter SET f_order=f_order + ? WHERE pk_filter=?",
                lower_by, f.getFilterId());
        reorderFilters(f);
    }

    public void raiseFilterOrder(FilterInterface f, int by) {
        double raise_by = (by * -1) - 0.1;
        getJdbcTemplate().update(
                "UPDATE filter SET f_order=f_order + ? WHERE pk_filter=?",
                raise_by, f.getFilterId());
        reorderFilters(f);
    }

    public void updateSetFilterType(FilterInterface f, FilterType type) {
        getJdbcTemplate().update(
                "UPDATE filter SET str_type=? WHERE pk_filter=?",
                type.toString(), f.getFilterId());
    }

    public void reorderFilters(final ShowInterface s) {
        getJdbcTemplate().update("LOCK TABLE filter IN SHARE MODE");
        getJdbcTemplate().call(new CallableStatementCreator() {

            public CallableStatement createCallableStatement(Connection con) throws SQLException {
                CallableStatement c = con.prepareCall("{ call reorder_filters(?) }");
                c.setString(1, s.getShowId());
                return c;
            }
        }, new ArrayList<SqlParameter>());
    }

    public FilterEntity findFilter(ShowInterface show, String name) {
        return getJdbcTemplate().queryForObject(
                GET_FILTER + " WHERE pk_show=? AND str_name=?",
                FILTER_DETAIL_MAPPER, show.getShowId(), name);
    }

    public FilterEntity getFilter(String id) {
        return getJdbcTemplate().queryForObject(
                GET_FILTER + " WHERE pk_filter=?",
                FILTER_DETAIL_MAPPER, id);
    }

    public FilterEntity getFilter(FilterInterface filter) {
        return getJdbcTemplate().queryForObject(
                GET_FILTER + " WHERE pk_filter=?",
                FILTER_DETAIL_MAPPER, filter.getFilterId());
    }
}

