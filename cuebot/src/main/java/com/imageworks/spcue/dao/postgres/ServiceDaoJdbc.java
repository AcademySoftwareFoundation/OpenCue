
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
import java.util.LinkedHashSet;

import com.google.common.collect.Sets;
import com.imageworks.spcue.dao.AbstractJdbcDao;
import org.apache.commons.lang.StringUtils;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.ServiceEntity;
import com.imageworks.spcue.ServiceOverrideEntity;
import com.imageworks.spcue.dao.ServiceDao;
import com.imageworks.spcue.util.SqlUtil;
import org.springframework.stereotype.Repository;

@Repository
public class ServiceDaoJdbc extends AbstractJdbcDao implements ServiceDao {

    private static final String SPLITTER = " \\| ";

    private static final String JOINER = " | ";

    public static LinkedHashSet<String> splitTags(String tags) {
        LinkedHashSet<String> set = Sets.newLinkedHashSet();
        for(String s: tags.split(SPLITTER)) {
           set.add(s.replaceAll(" ", ""));
        }
        return set;
    }

    public static String joinTags(LinkedHashSet<String> tags) {
        return StringUtils.join(tags, JOINER);
    }

    public static final RowMapper<ServiceEntity> SERVICE_MAPPER =
        new RowMapper<ServiceEntity>() {
        public ServiceEntity mapRow(ResultSet rs, int rowNum) throws SQLException {
            ServiceEntity s = new ServiceEntity();
            s.id = rs.getString("pk_service");
            s.name = rs.getString("str_name");
            s.minCores = rs.getInt("int_cores_min");
            s.maxCores = rs.getInt("int_cores_max");
            s.minMemory = rs.getLong("int_mem_min");
            s.minGpu = rs.getLong("int_gpu_min");
            s.threadable = rs.getBoolean("b_threadable");
            s.tags = splitTags(rs.getString("str_tags"));
            return s;
        }
    };

    public static final RowMapper<ServiceOverrideEntity> SERVICE_OVERRIDE_MAPPER =
        new RowMapper<ServiceOverrideEntity>() {
        public ServiceOverrideEntity mapRow(ResultSet rs, int rowNum)
                throws SQLException {
            ServiceOverrideEntity s = new ServiceOverrideEntity();
            s.id = rs.getString("pk_show_service");
            s.name = rs.getString("str_name");
            s.minCores = rs.getInt("int_cores_min");
            s.maxCores = rs.getInt("int_cores_max");
            s.minMemory = rs.getLong("int_mem_min");
            s.minGpu = rs.getLong("int_gpu_min");
            s.threadable = rs.getBoolean("b_threadable");
            s.tags = splitTags(rs.getString("str_tags"));
            s.showId = rs.getString("pk_show");
            return s;
        }
    };

    private static final String QUERY_FOR_SERVICE =
        "SELECT " +
            "service.pk_service," +
            "service.str_name," +
            "service.b_threadable," +
            "service.int_cores_min," +
            "service.int_cores_max," +
            "service.int_mem_min," +
            "service.int_gpu_min," +
            "service.str_tags " +
        "FROM " +
            "service ";

    @Override
    public ServiceEntity get(String id) {
        return getJdbcTemplate().queryForObject(
                QUERY_FOR_SERVICE + " WHERE (pk_service=? OR str_name=?)",
                SERVICE_MAPPER, id, id);
    }

    private static final String QUERY_FOR_SERVICE_OVER =
        "SELECT " +
            "show_service.pk_show_service," +
            "show_service.str_name," +
            "show_service.b_threadable," +
            "show_service.int_cores_min," +
            "show_service.int_cores_max, "+
            "show_service.int_mem_min," +
            "show_service.int_gpu_min," +
            "show_service.str_tags, " +
            "show.pk_show " +
         "FROM " +
            "show_service," +
            "show " +
         "WHERE " +
             "show_service.pk_show = show.pk_show ";

    @Override
    public ServiceOverrideEntity getOverride(String id, String show) {
        return getJdbcTemplate()
                .queryForObject(
                        QUERY_FOR_SERVICE_OVER
                                + " AND (show_service.pk_show_service=? OR show_service.str_name=?)"
                                + " AND (show.str_name=? OR show.pk_show=?)",
                        SERVICE_OVERRIDE_MAPPER, id, id, show, show);
    }

    @Override
    public ServiceOverrideEntity getOverride(String id) {
        return getJdbcTemplate().queryForObject(
                QUERY_FOR_SERVICE_OVER + " AND (show_service.pk_show_service=? " +
                        "OR show_service.str_name=?)",
                SERVICE_OVERRIDE_MAPPER, id, id);
    }

    @Override
    public boolean isOverridden(String service, String show) {
        return getJdbcTemplate().queryForObject(
                "SELECT COUNT(1) FROM show_service, show WHERE "
                        + "show_service.pk_show = show.pk_show = ? "
                        + "AND show_service.str_name=? and show.str_name=?",
                Integer.class, service, show) > 0;
    }

    private static final String INSERT_SERVICE =
        "INSERT INTO " +
            "service " +
         "(" +
             "pk_service," +
             "str_name," +
             "b_threadable," +
             "int_cores_min," +
             "int_cores_max, "+
             "int_mem_min," +
             "int_gpu_min," +
             "str_tags" +
         ") VALUES (?,?,?,?,?,?,?,?)";

    @Override
    public void insert(ServiceEntity service) {
        service.id = SqlUtil.genKeyRandom();
        getJdbcTemplate().update(INSERT_SERVICE, service.id,
                service.name, service.threadable, service.minCores,
                service.maxCores, service.minMemory, service.minGpu,
                StringUtils.join(service.tags.toArray(), " | "));
    }

    private static final String INSERT_SERVICE_WITH_SHOW =
        "INSERT INTO " +
            "show_service " +
        "(" +
            "pk_show_service," +
            "pk_show, " +
            "str_name," +
            "b_threadable," +
            "int_cores_min," +
            "int_cores_max," +
            "int_mem_min," +
            "int_gpu_min," +
            "str_tags " +
        ") VALUES (?,?,?,?,?,?,?,?,?)";

    @Override
    public void insert(ServiceOverrideEntity service) {
        service.id = SqlUtil.genKeyRandom();
        getJdbcTemplate().update(INSERT_SERVICE_WITH_SHOW, service.id,
                service.showId, service.name, service.threadable,
                service.minCores, service.maxCores, service.minMemory,
                service.minGpu, joinTags(service.tags));
    }

    private static final String UPDATE_SERVICE =
        "UPDATE " +
            "service " +
        "SET " +
            "str_name=?," +
            "b_threadable=?," +
            "int_cores_min=?," +
            "int_cores_max=?,"+
            "int_mem_min=?," +
            "int_gpu_min=?," +
            "str_tags=? " +
        "WHERE " +
            "pk_service = ?";

    @Override
    public void update(ServiceEntity service) {
        getJdbcTemplate().update(UPDATE_SERVICE, service.name,
                service.threadable, service.minCores, service.maxCores,
                service.minMemory, service.minGpu, joinTags(service.tags),
                service.getId());
    }

    private static final String UPDATE_SERVICE_WITH_SHOW =
        "UPDATE " +
            "show_service " +
        "SET " +
            "str_name=?," +
            "b_threadable=?," +
            "int_cores_min=?," +
            "int_cores_max=?," +
            "int_mem_min=?," +
            "int_gpu_min=?," +
            "str_tags=? " +
        "WHERE " +
            "pk_show_service = ?";

    @Override
    public void update(ServiceOverrideEntity service) {
        getJdbcTemplate().update(UPDATE_SERVICE_WITH_SHOW, service.name,
                service.threadable, service.minCores, service.maxCores,
                service.minMemory, service.minGpu, joinTags(service.tags),
                service.getId());
    }

    @Override
    public void delete(ServiceEntity service) {
        getJdbcTemplate().update(
                "DELETE FROM service WHERE pk_service=?", service.getId());
    }

    @Override
    public void delete(ServiceOverrideEntity service) {
        getJdbcTemplate().update(
                "DELETE FROM show_service WHERE pk_show_service=?",
                service.getId());
    }
}

