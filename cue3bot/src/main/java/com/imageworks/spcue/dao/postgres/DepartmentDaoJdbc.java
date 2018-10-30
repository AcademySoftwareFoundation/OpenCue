
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

import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.Department;
import com.imageworks.spcue.DepartmentEntity;
import com.imageworks.spcue.dao.DepartmentDao;
import com.imageworks.spcue.util.SqlUtil;

public class DepartmentDaoJdbc extends JdbcDaoSupport implements DepartmentDao {

    public static final RowMapper<Department> DEPARTMENT_MAPPER = new RowMapper<Department>() {
        public Department mapRow(ResultSet rs, int rowNum) throws SQLException {
            DepartmentEntity d = new DepartmentEntity();
            d.id = rs.getString("pk_dept");
            d.name = rs.getString("str_name");
            return d;
        }
    };

    @Override
    public boolean departmentExists(String name) {
        return getJdbcTemplate().queryForObject(
                "SELECT COUNT(1) FROM dept WHERE str_name=?",
                Integer.class, name) > 0;
    }

    @Override
    public Department findDepartment(String name) {
        return getJdbcTemplate().queryForObject(
                "SELECT pk_dept, str_name FROM dept WHERE str_name=?",
                DEPARTMENT_MAPPER, name);
    }

    @Override
    public Department getDefaultDepartment() {
        return getJdbcTemplate().queryForObject(
                "SELECT pk_dept, str_name FROM dept WHERE b_default=true",
                DEPARTMENT_MAPPER);
    }

    @Override
    public Department getDepartment(String id) {
        return getJdbcTemplate().queryForObject(
                "SELECT pk_dept, str_name FROM dept WHERE pk_dept=?",
                DEPARTMENT_MAPPER, id);
    }

    @Override
    public void deleteDepartment(Department d) {
        getJdbcTemplate().update("DELETE FROM dept WHERE pk_dept=?",
                d.getDepartmentId());
    }

    @Override
    public void insertDepartment(String name) {
        getJdbcTemplate().update("INSERT INTO dept (pk_dept,str_name) VALUES (?,?)",
                SqlUtil.genKeyRandom(), name);
    }
}

