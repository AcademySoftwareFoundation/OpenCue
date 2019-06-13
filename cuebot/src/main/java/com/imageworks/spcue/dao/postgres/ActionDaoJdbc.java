
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
import java.util.ArrayList;
import java.util.List;

import com.imageworks.spcue.dao.AbstractJdbcDao;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.ActionEntity;
import com.imageworks.spcue.ActionInterface;
import com.imageworks.spcue.FilterInterface;
import com.imageworks.spcue.SpcueRuntimeException;
import com.imageworks.spcue.dao.ActionDao;
import com.imageworks.spcue.grpc.filter.ActionType;
import com.imageworks.spcue.grpc.filter.ActionValueType;
import com.imageworks.spcue.util.SqlUtil;
import org.springframework.stereotype.Repository;

@Repository
public class ActionDaoJdbc extends AbstractJdbcDao implements ActionDao {

    public static final String INSERT_ACTION =
        "INSERT INTO " +
            "action " +
        "(" +
            "pk_action,pk_filter,str_action,str_value_type,b_stop" +
        ") VALUES (?,?,?,?,?)";

    public void createAction(ActionEntity action) {
        action.id = SqlUtil.genKeyRandom();
        boolean stopAction = ActionType.STOP_PROCESSING.equals(action.type);
        getJdbcTemplate().update(INSERT_ACTION,
                action.id, action.filterId,action.type.toString(),
                action.valueType.toString(), stopAction);
        updateAction(action);
    }

    private static final String GET_ACTION =
        "SELECT "+
            "action.*," +
            "filter.pk_show "+
        "FROM " +
            "action,"+
            "filter " +
        "WHERE " +
            "action.pk_filter = filter.pk_filter";

    public ActionEntity getAction(String id) {
        return getJdbcTemplate().queryForObject(
                GET_ACTION + " AND pk_action=?",
                ACTION_DETAIL_MAPPER, id);
    }

    public ActionEntity getAction(ActionInterface action) {
        return getJdbcTemplate().queryForObject(
                GET_ACTION + " AND pk_action=?",
                ACTION_DETAIL_MAPPER, action.getActionId());
    }

    public List<ActionEntity> getActions(FilterInterface filter) {
        return getJdbcTemplate().query(
                GET_ACTION + " AND filter.pk_filter=? ORDER BY b_stop ASC, ts_created ASC",
                ACTION_DETAIL_MAPPER, filter.getFilterId());
    }

    public void updateAction(ActionEntity action) {
        if (action.isNew()) {
            throw new SpcueRuntimeException("unable to update action that is not already commited");
        }

        // first we clear out all values

        getJdbcTemplate().update(
                "UPDATE action SET str_value=NULL,int_value=NULL,b_value=NULL,float_value=NULL WHERE pk_action=?",
                action.getActionId());

        StringBuilder query = new StringBuilder(1024);
        query.append("UPDATE action SET str_action=?,str_value_type=?");

        List<Object> args = new ArrayList<Object>(4);
        args.add(action.type.toString());
        args.add(action.valueType.toString());

        switch(action.valueType) {
            case GROUP_TYPE:
                query.append(",pk_folder=?  WHERE pk_action=?");
                args.add(action.groupValue);
                break;

            case STRING_TYPE:
                query.append(",str_value=?  WHERE pk_action=?");
                args.add(action.stringValue);
                break;

            case INTEGER_TYPE:
                query.append(",int_value=? WHERE pk_action=?");
                args.add(action.intValue);
                break;

            case FLOAT_TYPE:
                query.append(",float_value=? WHERE pk_action=?");
                args.add(action.floatValue);
                break;

            case BOOLEAN_TYPE:
                query.append(",b_value=?  WHERE pk_action=?");
                args.add(action.booleanValue);
                break;

            case NONE_TYPE:
                query.append(" WHERE pk_action=?");
                break;

            default:
                throw new SpcueRuntimeException("invalid action value type: " + action.valueType);
        }

        args.add(action.id);
        getJdbcTemplate().update(query.toString(),
                args.toArray());

    }

    public void deleteAction(ActionInterface action) {
        getJdbcTemplate().update("DELETE FROM action WHERE pk_action=?",action.getActionId());
    }

    public static final RowMapper<ActionEntity> ACTION_DETAIL_MAPPER = new RowMapper<ActionEntity>() {
        public ActionEntity mapRow(ResultSet rs, int rowNum) throws SQLException {
            ActionEntity action = new ActionEntity();
            action.id = rs.getString("pk_action");
            action.showId = rs.getString("pk_show");
            action.filterId = rs.getString("pk_filter");
            action.booleanValue = rs.getBoolean("b_value");
            action.groupValue = rs.getString("pk_folder");
            action.intValue = rs.getLong("int_value");
            action.floatValue = rs.getFloat("float_value");
            action.type = ActionType.valueOf(rs.getString("str_action"));
            action.valueType = ActionValueType.valueOf(rs.getString("str_value_type"));
            action.stringValue = rs.getString("str_value");
            return action;
        }
    };
}

