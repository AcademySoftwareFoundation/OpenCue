
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

import com.imageworks.spcue.TrackitTaskDetail;
import com.imageworks.spcue.dao.TrackitDao;

public class TrackitDaoJdbc extends JdbcDaoSupport implements TrackitDao {

    public static final RowMapper<TrackitTaskDetail> TASK_DETAIL_MAPPER =
        new RowMapper<TrackitTaskDetail>() {
            public TrackitTaskDetail mapRow(ResultSet rs, int rowNum) throws SQLException {
                TrackitTaskDetail t = new TrackitTaskDetail();
                t.show = rs.getString("str_show");
                t.shot = rs.getString("str_shot");
                t.status = rs.getString("str_status");
                t.startDate = rs.getDate("dt_start_date");
                t.endDate = rs.getDate("dt_est_end");
                t.frameCount = rs.getInt("int_frame_count");
                t.cgSup = rs.getString("str_cgsup");
                t.weeks = rs.getInt("int_weeks");
                return t;
            }
    };

    private static final String GET_TASKS =
        "SELECT DISTINCT "+
            "(CASE " +
                "WHEN " +
                    "(asset_task.dt_est_end - next_day(sysdate,'monday')) / 7 < 1 THEN 1 " +
                "ELSE " +
                    "CAST(((asset_task.dt_est_end - next_day(sysdate,'monday')) / 7) AS NUMERIC(6,0)) " +
            "END) AS int_weeks,"+
            "show.str_show_id AS str_show, " +
            "asset.str_name AS str_shot, "+
            "asset_task.str_prod_status AS str_status,"+
            "asset_task.dt_start_date, "+
            "asset_task.dt_est_end, "+
            "shot.lng_cut_length AS int_frame_count, "+
            "xmltype(asset.xml_asset_metadata).extract('/header/cgsup/text()').getstringval() AS str_cgsup " +
        "FROM "+
            "element.asset,"+
            "pts.show,"+
            "pts.shot,"+
            "element.asset_task,"+
            "element.asset_pipeline,"+
            "element.x_asset_type,"+
            "element.x_show_task,"+
            "element.asset_task_entitys,"+
            "contact.entity entity, "+
            "element.x_asset_task_status "+
        "WHERE "+
            "asset.pk_asset = asset_task.pk_asset "+
         "AND " +
            "asset.pk_show = show.pk_show "+
         "AND " +
            "asset.str_remote_handle = shot.pk_shot " +
         "AND " +
            "asset.pk_x_asset_type = x_asset_type.pk_x_asset_type " +
         "AND " +
            "asset_task.pk_asset_pipeline = asset_pipeline.pk_asset_pipeline " +
         "AND " +
            "asset_task.pk_asset_task = asset_task_entitys.pk_asset_task (+) "+
         "AND " +
            "asset_task_entitys.pk_entity = entity.pk_entity (+) " +
         "AND " +
            "asset_task.pk_x_asset_task_status = x_asset_task_status.pk_x_asset_task_status " +
         "AND " +
            "asset_pipeline.pk_x_show_task = x_show_task.pk_x_show_task " +
         "AND " +
            "str_group_type = 'Shot' " +
         "AND " +
            "trunc(asset_task.dt_est_end) != '31-DEC-69' " +
         "AND " +
             "show.str_show_id = ? " +
         "AND " +
             "x_show_task.str_value = ? ";

    @Override
    public List<TrackitTaskDetail> getTasks(String show, String dept) {
        return getJdbcTemplate().query(GET_TASKS, TASK_DETAIL_MAPPER, show, dept);
    }
}

