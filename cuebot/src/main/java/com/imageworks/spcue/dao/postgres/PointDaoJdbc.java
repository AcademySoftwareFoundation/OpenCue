
/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */

package com.imageworks.spcue.dao.postgres;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;

import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.DepartmentInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.PointDetail;
import com.imageworks.spcue.PointInterface;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.dao.PointDao;
import com.imageworks.spcue.util.SqlUtil;

public class PointDaoJdbc extends JdbcDaoSupport implements PointDao {

    @Override
    public void insertPointConf(PointDetail t) {
        t.id = SqlUtil.genKeyRandom();
        getJdbcTemplate().update("INSERT INTO point (pk_point, pk_show, pk_dept) VALUES (?,?,?)",
                t.id, t.getShowId(), t.getDepartmentId());
    }

    @Override
    public boolean isManaged(ShowInterface show, DepartmentInterface dept) {
        try {
            return getJdbcTemplate().queryForObject(
                    "SELECT b_managed FROM point WHERE pk_show=? and pk_dept=?", Integer.class,
                    show.getShowId(), dept.getDepartmentId()) == 1;
        } catch (org.springframework.dao.DataRetrievalFailureException e) {
            return false;
        }
    }

    @Override
    public PointDetail insertPointConf(ShowInterface show, DepartmentInterface dept) {
        PointDetail r = new PointDetail();
        r.deptId = dept.getId();
        r.showId = show.getShowId();
        r.id = SqlUtil.genKeyRandom();
        getJdbcTemplate().update("INSERT INTO point (pk_point, pk_show, pk_dept) VALUES (?,?,?)",
                r.id, r.getShowId(), r.getDepartmentId());
        return r;
    }

    @Override
    public boolean pointConfExists(ShowInterface show, DepartmentInterface dept) {
        return getJdbcTemplate().queryForObject(
                "SELECT COUNT(1) FROM point WHERE pk_show=? AND pk_dept=?", Integer.class,
                show.getShowId(), dept.getDepartmentId()) > 0;
    }

    private static final String UPDATE_TI_MANAGED =
            "UPDATE " + "point " + "SET " + "b_managed = true," + "str_ti_task=?, "
                    + "int_min_cores=? " + "WHERE " + "pk_point=?";

    @Override
    public void updateEnableManaged(PointInterface p, String task, int coreUnits) {
        getJdbcTemplate().update(UPDATE_TI_MANAGED, task, coreUnits, p.getPointId());
    }

    private static final String UPDATE_DISABLE_TI_MANAGED =
            "UPDATE " + "point " + "SET " + "b_managed = false," + "str_ti_task=null, "
                    + "int_min_cores=0 " + "WHERE " + "pk_point=?";

    @Override
    public void updateDisableManaged(PointInterface p) {
        getJdbcTemplate().update(UPDATE_DISABLE_TI_MANAGED, p.getPointId());
    }

    private static final RowMapper<PointDetail> DEPARTMENT_CONFIG_DETAIL_MAPPER =
            new RowMapper<PointDetail>() {
                public PointDetail mapRow(ResultSet rs, int rowNum) throws SQLException {
                    PointDetail rpd = new PointDetail();
                    rpd.deptId = rs.getString("pk_dept");
                    rpd.showId = rs.getString("pk_show");
                    rpd.id = rs.getString("pk_point");
                    rpd.cores = rs.getInt("int_min_cores");
                    rpd.tiTask = rs.getString("str_ti_task");
                    return rpd;
                }
            };

    private static final String GET_DEPARTMENT_CONFIG_DETAIL =
            "SELECT " + "pk_point," + "pk_dept," + "pk_show," + "str_ti_task," + "int_min_cores "
                    + "FROM " + "point " + "WHERE " + "pk_point = ?";

    @Override
    public PointDetail getPointConfDetail(String id) {
        return getJdbcTemplate().queryForObject(GET_DEPARTMENT_CONFIG_DETAIL,
                DEPARTMENT_CONFIG_DETAIL_MAPPER, id);
    }

    private static final String GET_POINT_CONFIG_DETAIL_BY_SHOW_DEPT = "SELECT " + "pk_point,"
            + "pk_dept," + "pk_show," + "str_ti_task," + "int_min_cores, " + "b_managed " + "FROM "
            + "point " + "WHERE " + "pk_show = ? " + "AND " + "pk_dept = ? ";

    @Override
    public PointDetail getPointConfigDetail(ShowInterface show, DepartmentInterface dept) {
        return getJdbcTemplate().queryForObject(GET_POINT_CONFIG_DETAIL_BY_SHOW_DEPT,
                DEPARTMENT_CONFIG_DETAIL_MAPPER, show.getShowId(), dept.getDepartmentId());
    }

    private static final String UPDATE_TI_MANAGED_CORES =
            "UPDATE " + "point " + "SET " + "int_min_cores=? " + "WHERE " + "pk_point=?";

    @Override
    public void updateManagedCores(PointInterface cdept, int cores) {
        getJdbcTemplate().update(UPDATE_TI_MANAGED_CORES, cores, cdept.getPointId());

    }

    private static final String GET_MANAGED_POINT_CONFS =
            "SELECT " + "pk_point," + "pk_dept," + "pk_show," + "str_ti_task," + "int_min_cores, "
                    + "b_managed " + "FROM " + "point " + "WHERE " + "b_managed = true ";

    @Override
    public List<PointDetail> getManagedPointConfs() {
        return getJdbcTemplate().query(GET_MANAGED_POINT_CONFS, DEPARTMENT_CONFIG_DETAIL_MAPPER);
    }

    @Override
    public void updatePointConfUpdateTime(PointInterface t) {
        getJdbcTemplate().update("UPDATE point SET ts_updated=current_timestamp WHERE pk_point=?",
                t.getPointId());
    }

    private static final String IS_OVER_MIN_CORES =
            "SELECT " + "COUNT(1) " + "FROM " + "job," + "point p " + "WHERE "
                    + "job.pk_show = p.pk_show " + "AND " + "job.pk_dept = p.pk_dept " + "AND "
                    + "p.int_cores > p.int_min_cores " + "AND " + "job.pk_job = ?";

    @Override
    public boolean isOverMinCores(JobInterface job) {
        return getJdbcTemplate().queryForObject(IS_OVER_MIN_CORES, Integer.class,
                job.getJobId()) > 0;
    }
}
