
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

import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.LimitEntity;
import com.imageworks.spcue.LimitInterface;
import com.imageworks.spcue.dao.LimitDao;
import com.imageworks.spcue.util.SqlUtil;

public class LimitDaoJdbc extends JdbcDaoSupport implements LimitDao {

    public static final RowMapper<LimitEntity> LIMIT_MAPPER = new RowMapper<LimitEntity>() {
        public LimitEntity mapRow(ResultSet rs, int rowNum) throws SQLException {
            LimitEntity limit = new LimitEntity();
            limit.id = rs.getString("pk_limit_record");
            limit.name = rs.getString("str_name");
            limit.maxValue = rs.getInt("int_max_value");
            limit.currentRunning = rs.getInt("int_current_running");
            return limit;
        }
    };

    @Override
    public String createLimit(String name, int maxValue) {
        String limitId = SqlUtil.genKeyRandom();
        getJdbcTemplate().update(
                "INSERT INTO limit_record (pk_limit_record,str_name, int_max_value) VALUES (?,?,?)",
                limitId, name, maxValue);
        return limitId;
    }

    @Override
    public void deleteLimit(LimitInterface limit) {
        getJdbcTemplate().update("DELETE FROM limit_record WHERE pk_limit_recor=?",
                limit.getId());
    }

    @Override
    public LimitEntity findLimit(String name){
        String findLimitQuery = GET_LIMIT_BASE +
                "WHERE " +
                    "limit-record.str_name=? " +
                "GROUP BY " +
                    "limit_record.str_name, " +
                    "limit_record.pk_limit_record, " +
                    "limit_record.int_max_value";
        return getJdbcTemplate().queryForObject(findLimitQuery, LIMIT_MAPPER, name);
    }

    @Override
    public LimitEntity getLimit(String id) {
        String getLimitQuery = GET_LIMIT_BASE +
                "WHERE " +
                    "limit_record.pk_limit_record=? " +
                "GROUP BY " +
                    "limit_record.str_name, " +
                    "limit_record.pk_limit_record, " +
                    "limit_record.int_max_value";
        return getJdbcTemplate().queryForObject(getLimitQuery, LIMIT_MAPPER, id);
    }

    @Override
    public void setLimitName(LimitInterface limit, String name) {
        getJdbcTemplate().update("UPDATE limit_record SET str_name = ? WHERE pk_limit_record = ?",
                name, limit.getId());
    }

    public void setMaxValue(LimitInterface limit, int maxValue) {
        getJdbcTemplate().update("UPDATE limit_record SET int_max_value = ? WHERE pk_limit_record = ?",
                maxValue, limit.getId());
    }

    private static final String GET_LIMIT_BASE =
        "SELECT " +
            "limit_record.pk_limit_record, " +
            "limit_record.str_name, " +
            "limit_record.int_max_value," +
            "SUM(layer_stat.int_running_count) AS int_current_running " +
        "FROM " +
            "limit_record " +
        "LEFT JOIN " +
            "layer_limit ON layer_limit.pk_limit_record = limit_record.pk_limit_record " +
        "LEFT JOIN " +
            "layer ON layer.pk_layer = layer_limit.pk_layer " +
        "LEFT JOIN " +
            "layer_stat ON layer_stat.pk_layer = layer.pk_layer ";
}
