
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
import java.util.Map;

import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.Department;
import com.imageworks.spcue.Job;
import com.imageworks.spcue.Point;
import com.imageworks.spcue.Show;
import com.imageworks.spcue.Task;
import com.imageworks.spcue.TaskDetail;
import com.imageworks.spcue.dao.TaskDao;
import com.imageworks.spcue.util.SqlUtil;

/**
 * DAO for managing department tasks
 */
public class TaskDaoJdbc extends JdbcDaoSupport implements TaskDao {

    @Override
    public void deleteTasks(Point cdept) {
        getJdbcTemplate().update(
                "DELETE FROM task WHERE pk_point=?",
                cdept.getPointId());
    }

    @Override
    public void deleteTasks(Show show, Department dept) {
        getJdbcTemplate().update(
                "DELETE FROM task WHERE pk_show=? AND pk_dept=?",
                show.getShowId(), dept.getDepartmentId());
    }

    @Override
    public void deleteTask(Task task) {
        getJdbcTemplate().update(
                "DELETE FROM task WHERE pk_task=?",
                task.getId());
    }

    @Override
    public boolean isManaged(Task t) {
        try {
            return getJdbcTemplate().queryForObject("SELECT b_managed FROM point WHERE pk_show=? and pk_dept=?",
                Integer.class, t.getShowId(), t.getDepartmentId()) == 1;
        } catch (org.springframework.dao.DataRetrievalFailureException e) {
            return false;
        }
    }

    private static final String INSERT_TASK =
        "INSERT INTO " +
            "task " +
        "( " +
            "pk_task,"+
            "pk_point,"+
            "str_shot," +
            "int_min_cores" +
        ") " +
        "VALUES (?,?,?,?)";

    @Override
    public void insertTask(TaskDetail task) {
        task.id = SqlUtil.genKeyRandom();
        getJdbcTemplate().update(INSERT_TASK,
                task.id, task.getPointId(), task.shot, task.minCoreUnits);
    }

    private static final String GET_TASK_DETAIL =
        "SELECT " +
            "point.pk_dept,"+
            "point.pk_show,"+
            "point.pk_point,"+
            "task.pk_task," +
            "task.int_min_cores + task.int_adjust_cores AS int_min_cores,"+
            "task.str_shot,"+
            "(task.str_shot || '.' || dept.str_name) AS str_name " +
        "FROM " +
            "point,"+
            "task,"+
            "dept, "+
            "show "+
        "WHERE " +
            "point.pk_dept = dept.pk_dept "+
        "AND " +
            "point.pk_show = show.pk_show " +
        "AND " +
            "point.pk_point = task.pk_point ";

    public static final RowMapper<TaskDetail> TASK_DETAIL_MAPPER =
        new RowMapper<TaskDetail>() {
        public TaskDetail mapRow(ResultSet rs, int row) throws SQLException {
            TaskDetail t = new TaskDetail();
            t.pointId = rs.getString("pk_point");
            t.deptId = rs.getString("pk_dept");
            t.showId = rs.getString("pk_show");
            t.id = rs.getString("pk_task");
            t.minCoreUnits = rs.getInt("int_min_cores");
            t.name = rs.getString("str_name");
            t.shot = rs.getString("str_shot");
            return t;
        }
    };

    @Override
    public TaskDetail getTaskDetail(String id) {
        return getJdbcTemplate().queryForObject(
                GET_TASK_DETAIL + " AND task.pk_task=?",
                TASK_DETAIL_MAPPER, id);
    }

    @Override
    public TaskDetail getTaskDetail(Department d, String shot) {
        return getJdbcTemplate().queryForObject(
                GET_TASK_DETAIL + " AND point.pk_dept = ? AND task.str_shot = ?",
                TASK_DETAIL_MAPPER, d.getDepartmentId(), shot);
    }

    @Override
    public TaskDetail getTaskDetail(Job j) {
        Map<String,Object> map = getJdbcTemplate().queryForMap(
                "SELECT pk_dept, str_shot FROM job WHERE job.pk_job=?", j.getJobId());

        return getJdbcTemplate().queryForObject(
                GET_TASK_DETAIL + " AND task.str_shot = ? AND point.pk_dept = ?",
                TASK_DETAIL_MAPPER, map.get("str_shot").toString(), map.get("pk_dept").toString());
    }

    public void updateTaskMinCores(Task t, int value) {
        if (value < 0) {
            throw new IllegalArgumentException("min cores must be greater than or equal to 0");
        }
        getJdbcTemplate().update(
                "UPDATE task SET int_min_cores=? WHERE pk_task=?",
                value, t.getTaskId());
    }

    @Override
    public void adjustTaskMinCores(Task t, int value) {
        if (value < 0) {
            throw new IllegalArgumentException("min cores must be greater than or equal to 0");
        }
        getJdbcTemplate().update(
                "UPDATE task SET int_adjust_cores = ? - int_min_cores WHERE pk_task=?",
                value, t.getTaskId());
    }

    @Override
    public void mergeTask(TaskDetail t) {
        String pkTask = null;
        try {
            pkTask = getJdbcTemplate().queryForObject(
                    "SELECT task.pk_task FROM task, point WHERE task.pk_point = point.pk_point AND " +
                    "task.str_shot = ? AND point.pk_point=?", String.class,
                    t.shot, t.getPointId());

        } catch (EmptyResultDataAccessException dae) {
            // Eat this, its possible that no task exists
        }

        // No need to do anything with this task.
        if (pkTask == null && t.minCoreUnits == 0) {
            return;
        }

        if (t.minCoreUnits == 0) {
            getJdbcTemplate().update("DELETE FROM task WHERE pk_point=? AND str_shot=? ",
                    t.getPointId(), t.shot);
        }
        else if (getJdbcTemplate().update(
                    "UPDATE task SET int_min_cores=? WHERE pk_point=? AND str_shot=?",
                    t.minCoreUnits, t.getPointId(), t.shot) == 0) {
            try {
                insertTask(t);
            }
            catch (org.springframework.dao.DataIntegrityViolationException e) {
                logger.warn("error inserting task " + t.shot + "," + e);
            }
        }
    }

    private static final String CLEAR_TASK_ADJUSTMENTS =
        "UPDATE " +
            "task " +
        "SET " +
            "int_adjust_cores = 0 " +
        "WHERE " +
            "pk_show=? " +
        "AND " +
            "pk_dept = ? ";

    @Override
    public void clearTaskAdjustments(Point cdept) {
        getJdbcTemplate().update(CLEAR_TASK_ADJUSTMENTS,
                cdept.getShowId(), cdept.getDepartmentId());
    }

    private static final String CLEAR_TASK_ADJUSTMENT =
        "UPDATE " +
            "task " +
        "SET " +
            "int_adjust_cores = 0 " +
        "WHERE " +
            "pk_task=?";

    @Override
    public void clearTaskAdjustment(Task t) {
        getJdbcTemplate().update(CLEAR_TASK_ADJUSTMENT, t.getTaskId());
    }

    private static final String IS_JOB_MANAGED =
        "SELECT " +
            "COUNT(1) " +
        "FROM " +
            "job,"+
            "task,"+
            "point " +
        "WHERE " +
            "job.pk_show = point.pk_show " +
        "AND " +
            "job.pk_dept = point.pk_dept " +
        "AND " +
            "task.pk_point = point.pk_point " +
        "AND " +
            "task.str_shot = job.str_shot " +
        "AND " +
            "job.pk_job = ?";

    @Override
    public boolean isManaged(Job j) {
        return getJdbcTemplate().queryForObject(IS_JOB_MANAGED,
                Integer.class, j.getJobId()) > 0;
    }
}

