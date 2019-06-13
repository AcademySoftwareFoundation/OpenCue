
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
import java.util.List;

import com.imageworks.spcue.dao.AbstractJdbcDao;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.LightweightDependency;
import com.imageworks.spcue.dao.DependDao;
import com.imageworks.spcue.depend.DependException;
import com.imageworks.spcue.depend.FrameByFrame;
import com.imageworks.spcue.depend.FrameOnFrame;
import com.imageworks.spcue.depend.FrameOnJob;
import com.imageworks.spcue.depend.FrameOnLayer;
import com.imageworks.spcue.depend.JobOnFrame;
import com.imageworks.spcue.depend.JobOnJob;
import com.imageworks.spcue.depend.JobOnLayer;
import com.imageworks.spcue.depend.LayerOnFrame;
import com.imageworks.spcue.depend.LayerOnJob;
import com.imageworks.spcue.depend.LayerOnLayer;
import com.imageworks.spcue.depend.PreviousFrame;
import com.imageworks.spcue.grpc.depend.DependTarget;
import com.imageworks.spcue.grpc.depend.DependType;
import com.imageworks.spcue.util.SqlUtil;
import org.springframework.stereotype.Repository;

@Repository
public class DependDaoJdbc extends AbstractJdbcDao implements DependDao {

    public static final RowMapper<LightweightDependency> DEPEND_MAPPER = new RowMapper<LightweightDependency>() {
        public LightweightDependency mapRow(ResultSet rs, int row) throws SQLException {
            LightweightDependency d  = new LightweightDependency();
            d.id = rs.getString("pk_depend");
            d.type = DependType.valueOf(rs.getString("str_type"));
            d.target = DependTarget.valueOf(rs.getString("str_target"));
            d.anyFrame = rs.getBoolean("b_any");
            d.parent = rs.getString("pk_parent");
            d.active = rs.getBoolean("b_active");
            d.dependErFrameId = rs.getString("pk_frame_depend_er");
            d.dependOnFrameId = rs.getString("pk_frame_depend_on");
            d.dependErLayerId = rs.getString("pk_layer_depend_er");
            d.dependOnLayerId =rs.getString("pk_layer_depend_on");
            d.dependOnJobId = rs.getString("pk_job_depend_on");
            d.dependErJobId = rs.getString("pk_job_depend_er");
            return d;
        }
    };

    private static final String INSERT_DEPEND =
        "INSERT INTO " +
        "depend " +
            "(" +
                "pk_depend,"+
                "pk_parent,"+
                "pk_job_depend_er," +
                "pk_layer_depend_er," +
                "pk_frame_depend_er," +
                "pk_job_depend_on," +
                "pk_layer_depend_on," +
                "pk_frame_depend_on," +
                "str_type," +
                "b_any, " +
                "str_target, " +
                "b_active, " +
                "str_signature, "+
                "b_composite " +
            ") " +
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)";

    @Override
    public void insertDepend(JobOnJob d) {
        d.setId(SqlUtil.genKeyRandom());
        getJdbcTemplate().update(INSERT_DEPEND,
                d.getId(),
                null,
                d.getDependErJob().getJobId(),
                null,
                null,
                d.getDependOnJob().getJobId(),
                null,
                null,
                DependType.JOB_ON_JOB.toString(),
                d.isAnyFrame(),
                d.getTarget().toString(),
                d.isActive(),
                d.getSignature(),
                d.isComposite());
    }

    @Override
    public void insertDepend(JobOnLayer d) {
        d.setId(SqlUtil.genKeyRandom());
        getJdbcTemplate().update(INSERT_DEPEND,
                d.getId(),
                null,
                d.getDependErJob().getJobId(),
                null,
                null,
                d.getDependOnLayer().getJobId(),
                d.getDependOnLayer().getLayerId(),
                null,
                DependType.JOB_ON_LAYER.toString(),
                d.isAnyFrame(),
                d.getTarget().toString(),
                d.isActive(),
                d.getSignature(),
                d.isComposite());
    }

    @Override
    public void insertDepend(JobOnFrame d) {
        d.setId(SqlUtil.genKeyRandom());
        getJdbcTemplate().update(INSERT_DEPEND,
                d.getId(),
                null,
                d.getDependErJob().getJobId(),
                null,
                null,
                d.getDependOnFrame().getJobId(),
                d.getDependOnFrame().getLayerId(),
                d.getDependOnFrame().getFrameId(),
                DependType.JOB_ON_FRAME.toString(),
                d.isAnyFrame(),
                d.getTarget().toString(),
                d.isActive(),
                d.getSignature(),
                d.isComposite());
    }

    @Override
    public void insertDepend(LayerOnJob d) {
        d.setId(SqlUtil.genKeyRandom());
        getJdbcTemplate().update(INSERT_DEPEND,
                d.getId(),
                null,
                d.getDependErLayer().getJobId(),
                d.getDependErLayer().getLayerId(),
                null,
                d.getDependOnJob().getJobId(),
                null,
                null,
                DependType.LAYER_ON_JOB.toString(),
                d.isAnyFrame(),
                d.getTarget().toString(),
                d.isActive(),
                d.getSignature(),
                d.isComposite());
    }

    @Override
    public void insertDepend(LayerOnLayer d) {
        d.setId(SqlUtil.genKeyRandom());
        getJdbcTemplate().update(INSERT_DEPEND,
                d.getId(),
                null,
                d.getDependErLayer().getJobId(),
                d.getDependErLayer().getLayerId(),
                null,
                d.getDependOnLayer().getJobId(),
                d.getDependOnLayer().getLayerId(),
                null,
                DependType.LAYER_ON_LAYER.toString(),
                d.isAnyFrame(),
                d.getTarget().toString(),
                d.isActive(),
                d.getSignature(),
                d.isComposite());
    }

    @Override
    public void insertDepend(LayerOnFrame d) {
        d.setId(SqlUtil.genKeyRandom());
        getJdbcTemplate().update(INSERT_DEPEND,
                d.getId(),
                null,
                d.getDependErLayer().getJobId(),
                d.getDependErLayer().getLayerId(),
                null,
                d.getDependOnFrame().getJobId(),
                d.getDependOnFrame().getLayerId(),
                d.getDependOnFrame().getFrameId(),
                DependType.LAYER_ON_FRAME.toString(),
                d.isAnyFrame(),
                d.getTarget().toString(),
                d.isActive(),
                d.getSignature(),
                d.isComposite());
    }

    @Override
    public void insertDepend(FrameOnJob d) {
        d.setId(SqlUtil.genKeyRandom());
        getJdbcTemplate().update(INSERT_DEPEND,
                d.getId(),
                null,
                d.getDependErFrame().getJobId(),
                d.getDependErFrame().getLayerId(),
                d.getDependErFrame().getFrameId(),
                d.getDependOnJob().getJobId(),
                null,
                null,
                DependType.FRAME_ON_JOB.toString(),
                d.isAnyFrame(),
                d.getTarget().toString(),
                d.isActive(),
                d.getSignature(),
                d.isComposite());
    }

    @Override
    public void insertDepend(FrameOnLayer d) {
        d.setId(SqlUtil.genKeyRandom());
        getJdbcTemplate().update(INSERT_DEPEND,
                d.getId(),
                null,
                d.getDependErFrame().getJobId(),
                d.getDependErFrame().getLayerId(),
                d.getDependErFrame().getFrameId(),
                d.getDependOnLayer().getJobId(),
                d.getDependOnLayer().getLayerId(),
                null,
                DependType.FRAME_ON_LAYER.toString(),
                d.isAnyFrame(),
                d.getTarget().toString(),
                d.isActive(),
                d.getSignature(),
                d.isComposite());
    }

    @Override
    public void insertDepend(PreviousFrame d) {
        d.setId(SqlUtil.genKeyRandom());
        getJdbcTemplate().update(INSERT_DEPEND,
                d.getId(),
                null,
                d.getDependErLayer().getJobId(),
                d.getDependErLayer().getLayerId(),
                null,
                d.getDependOnLayer().getJobId(),
                d.getDependOnLayer().getLayerId(),
                null,
                DependType.PREVIOUS_FRAME.toString(),
                d.isAnyFrame(),
                d.getTarget().toString(),
                d.isActive(),
                d.getSignature(),
                d.isComposite());
    }

    @Override
    public void insertDepend(FrameOnFrame d) {
        d.setId(SqlUtil.genKeyRandom());
        String parentId = null;
        if (d.getParent() != null) {
            parentId =d.getParent().getId();
        }

        getJdbcTemplate().update(INSERT_DEPEND,
                d.getId(),
                parentId,
                d.getDependErFrame().getJobId(),
                d.getDependErFrame().getLayerId(),
                d.getDependErFrame().getFrameId(),
                d.getDependOnFrame().getJobId(),
                d.getDependOnFrame().getLayerId(),
                d.getDependOnFrame().getFrameId(),
                DependType.FRAME_ON_FRAME.toString(),
                d.isAnyFrame(),
                d.getTarget().toString(),
                d.isActive(),
                d.getSignature(),
                d.isComposite());
    }

    @Override
    public void insertDepend(FrameByFrame d) {
        d.setId(SqlUtil.genKeyRandom());
        getJdbcTemplate().update(INSERT_DEPEND,
                d.getId(),
                null,
                d.getDependErLayer().getJobId(),
                d.getDependErLayer().getLayerId(),
                null,
                d.getDependOnLayer().getJobId(),
                d.getDependOnLayer().getLayerId(),
                null,
                DependType.FRAME_BY_FRAME.toString(),
                d.isAnyFrame(),
                d.getTarget().toString(),
                d.isActive(),
                d.getSignature(),
                d.isComposite());
    }

    private static final String UPDATE_FRAME_STATE =
        "UPDATE " +
            "frame " +
        "SET " +
            "str_state='DEPEND' " +
        "WHERE " +
            "int_depend_count != 0 " +
        "AND " +
             "frame.str_state NOT IN ('SUCCEEDED','EATEN','RUNNING','DEPEND') " +
        "AND " +
            "frame.pk_frame = ?";

    @Override
    public void updateFrameState(FrameInterface f) {
        getJdbcTemplate().update(UPDATE_FRAME_STATE,
                f.getFrameId());
    }

    private static final String UPDATE_DEPEND_COUNT =
        "UPDATE " +
            "frame " +
        "SET " +
            "int_depend_count = int_depend_count + 1 " +
        "WHERE " +
            "pk_frame = ?";

    @Override
    public void incrementDependCount(FrameInterface f) {
        int result = getJdbcTemplate().update(UPDATE_DEPEND_COUNT,
                f.getFrameId());
        if (result == 0) {
            throw new DependException("updating the depend count for " +
                    " the frame " + f.getName() + " in job " + f.getJobId() +
                    "failed.");
        }
    }

    private static final String DECREMENT_DEPEND_COUNT =
        "UPDATE " +
            "frame " +
        "SET " +
            "int_depend_count = int_depend_count -1 " +
        "WHERE " +
            "pk_frame = ? " +
        "AND " +
            "int_depend_count > 0";

    @Override
    public boolean decrementDependCount(FrameInterface f) {
        return getJdbcTemplate().update(DECREMENT_DEPEND_COUNT,
                f.getFrameId()) == 1;
    }

    private static final String[] DELETE_DEPEND = {
        "DELETE FROM depend WHERE pk_parent=?",
        "DELETE FROM depend WHERE pk_depend=?"
    };

    @Override
    public void deleteDepend(LightweightDependency depend) {
        if (depend.type.equals(DependType.FRAME_BY_FRAME)) {
            getJdbcTemplate().update(DELETE_DEPEND[0], depend.getId());
        }
        getJdbcTemplate().update(DELETE_DEPEND[1], depend.getId());
    }

    private static final String GET_LIGHTWEIGHT_DEPEND =
        "SELECT * FROM depend WHERE pk_depend=?";

    @Override
    public LightweightDependency getDepend(String id) {
        return getJdbcTemplate().queryForObject(
                GET_LIGHTWEIGHT_DEPEND,
                DEPEND_MAPPER, id);
    }

    private static final String GET_LIGHTWEIGHT_DEPEND_BY_SIGNATURE =
        "SELECT * FROM depend WHERE str_signature=?";

    @Override
    public LightweightDependency getDependBySignature(String s) {
        return getJdbcTemplate().queryForObject(
                GET_LIGHTWEIGHT_DEPEND_BY_SIGNATURE,
                DEPEND_MAPPER, s);
    }

    private static final String GET_WHAT_DEPENDS_ON_JOB =
        "SELECT " +
            "depend.pk_depend," +
            "depend.str_type," +
            "depend.str_target,"+
            "depend.b_any,"+
            "depend.pk_parent,"+
            "depend.b_active," +
            "depend.pk_frame_depend_er,"+
            "depend.pk_frame_depend_on,"+
            "depend.pk_layer_depend_er,"+
            "depend.pk_layer_depend_on,"+
            "depend.pk_job_depend_er,"+
            "depend.pk_job_depend_on "+
        "FROM " +
            "depend " +
        "WHERE " +
            "pk_job_depend_on=? " +
        "AND " +
            "b_active = true " +
        "AND " +
            "str_type IN (?,?,?)";

    @Override
    public List<LightweightDependency> getWhatDependsOn(JobInterface job) {
        return getJdbcTemplate().query(GET_WHAT_DEPENDS_ON_JOB,
                DEPEND_MAPPER, job.getJobId(),
                DependType.JOB_ON_JOB.toString(),
                DependType.LAYER_ON_JOB.toString(),
                DependType.FRAME_ON_JOB.toString());
    }

    private static final String GET_WHAT_DEPENDS_ON_JOB_WITH_TARGET =
        "SELECT " +
            "depend.pk_depend," +
            "depend.str_type," +
            "depend.str_target,"+
            "depend.b_any,"+
            "depend.pk_parent,"+
            "depend.b_active," +
            "depend.pk_frame_depend_er,"+
            "depend.pk_frame_depend_on,"+
            "depend.pk_layer_depend_er,"+
            "depend.pk_layer_depend_on,"+
            "depend.pk_job_depend_er,"+
            "depend.pk_job_depend_on "+
        "FROM " +
            "depend " +
        "WHERE " +
            "pk_job_depend_on=? " +
        "AND " +
            "b_active = true " +
        "AND " +
            "str_target = ? " +
        "AND " +
            "str_type IN (?,?,?)";

    @Override
    public List<LightweightDependency> getWhatDependsOn(JobInterface job, DependTarget target) {
        if (target.equals(DependTarget.ANY_TARGET)) {
            return getWhatDependsOn(job);
        }
        else {
            return getJdbcTemplate().query(GET_WHAT_DEPENDS_ON_JOB_WITH_TARGET,
                    DEPEND_MAPPER, job.getJobId(), target.toString(),
                    DependType.JOB_ON_JOB.toString(),
                    DependType.LAYER_ON_JOB.toString(),
                    DependType.FRAME_ON_JOB.toString());
        }
    }

    private static final String GET_WHAT_DEPENDS_ON_LAYER =
        "SELECT " +
            "depend.pk_depend," +
            "depend.str_type," +
            "depend.str_target,"+
            "depend.b_any,"+
            "depend.pk_parent,"+
            "depend.b_active," +
            "depend.pk_frame_depend_er,"+
            "depend.pk_frame_depend_on,"+
            "depend.pk_layer_depend_er,"+
            "depend.pk_layer_depend_on,"+
            "depend.pk_job_depend_er,"+
            "depend.pk_job_depend_on "+
        "FROM " +
            "depend " +
        "WHERE " +
            "pk_job_depend_on=? " +
        "AND " +
            "pk_layer_depend_on=? " +
        "AND " +
            "str_type IN (?,?,?) " +
        "AND " +
            "b_active = ?";

    @Override
    public List<LightweightDependency> getWhatDependsOn(LayerInterface layer) {
        return getJdbcTemplate().query(GET_WHAT_DEPENDS_ON_LAYER,
                DEPEND_MAPPER, layer.getJobId(), layer.getLayerId(),
                DependType.JOB_ON_LAYER.toString(),
                DependType.LAYER_ON_LAYER.toString(),
                DependType.FRAME_ON_LAYER.toString(),
                true);
    }

    @Override
    public List<LightweightDependency> getWhatDependsOn(LayerInterface layer, boolean active) {
        return getJdbcTemplate().query(GET_WHAT_DEPENDS_ON_LAYER,
                DEPEND_MAPPER, layer.getJobId(), layer.getLayerId(),
                DependType.JOB_ON_LAYER.toString(),
                DependType.LAYER_ON_LAYER.toString(),
                DependType.FRAME_ON_LAYER.toString(),
                active);
    }


    private static final String GET_WHAT_DEPENDS_ON_FRAME =
        "SELECT " +
            "depend.pk_depend," +
            "depend.str_type," +
            "depend.str_target,"+
            "depend.b_any,"+
            "depend.pk_parent,"+
            "depend.b_active," +
            "depend.pk_frame_depend_er,"+
            "depend.pk_frame_depend_on,"+
            "depend.pk_layer_depend_er,"+
            "depend.pk_layer_depend_on,"+
            "depend.pk_job_depend_er,"+
            "depend.pk_job_depend_on "+
        "FROM " +
            "depend " +
        "WHERE " +
            "b_active = ? " +
        "AND " +
            "pk_job_depend_on = ? " +
        "AND " +
            "(pk_frame_depend_on = ? " +
        "AND " +
            "str_type IN (?,?,?)) " +
        "OR " +
            "(pk_layer_depend_on = ? AND str_type = ? AND b_any = true)";

    @Override
    public List<LightweightDependency> getWhatDependsOn(FrameInterface frame) {
        return getWhatDependsOn(frame, true);
    }

    @Override
    public List<LightweightDependency> getWhatDependsOn(FrameInterface frame, boolean active) {
        return getJdbcTemplate().query(GET_WHAT_DEPENDS_ON_FRAME,
                DEPEND_MAPPER, active, frame.getJobId(), frame.getFrameId(),
                DependType.FRAME_ON_FRAME.toString(),
                DependType.LAYER_ON_FRAME.toString(),
                DependType.JOB_ON_FRAME.toString(),
                frame.getLayerId(),
                DependType.LAYER_ON_LAYER.toString());
    }

    private static final String SET_INACTIVE =
        "UPDATE " +
            "depend " +
        "SET " +
            "b_active=false,"+
            "ts_satisfied=current_timestamp,"+
            "str_signature=pk_depend "+
        "WHERE " +
            "pk_depend = ? " +
        "AND " +
            "b_active = true " +
        "AND " +
            "b_composite = false";

    @Override
    public boolean setInactive(LightweightDependency depend) {
        depend.active = getJdbcTemplate().update(SET_INACTIVE, depend.getId()) == 1;
        return depend.active;
    }

    private static final String SET_ACTIVE =
        "UPDATE " +
            "depend " +
        "SET " +
            "b_active=true "+
        "WHERE " +
            "pk_depend=? " +
        "AND "+
            "b_active=false";

    @Override
    public boolean setActive(LightweightDependency depend) {
        if (!depend.type.equals(DependType.FRAME_ON_FRAME)
                && !depend.type.equals(DependType.LAYER_ON_LAYER)) {
               return false;
        }
        depend.active = getJdbcTemplate().update(
                SET_ACTIVE, depend.getId()) == 1;
        return depend.active;
    }

    private static final String GET_CHILD_DEPENDS =
        "SELECT " +
            "depend.pk_depend," +
            "depend.str_type," +
            "depend.str_target,"+
            "depend.b_any,"+
            "depend.pk_parent,"+
            "depend.b_active," +
            "depend.pk_frame_depend_er,"+
            "depend.pk_frame_depend_on,"+
            "depend.pk_layer_depend_er,"+
            "depend.pk_layer_depend_on,"+
            "depend.pk_job_depend_er,"+
            "depend.pk_job_depend_on "+
        "FROM " +
            "depend " +
        "WHERE " +
            "depend.pk_job_depend_er = ? " +
        "AND " +
            "depend.pk_job_depend_on = ? " +
        "AND " +
            "depend.pk_parent = ? " +
        "AND " +
            "depend.b_active = true ";

    @Override
    public List<LightweightDependency> getChildDepends(LightweightDependency depend) {
        return getJdbcTemplate().query(GET_CHILD_DEPENDS, DEPEND_MAPPER,
                depend.dependErJobId, depend.dependOnJobId, depend.id);
    }

    private static final String GET_WHAT_THIS_JOB_DEPENDS_ON =
        "SELECT " +
            "depend.pk_depend," +
            "depend.str_type," +
            "depend.str_target,"+
            "depend.b_any,"+
            "depend.pk_parent,"+
            "depend.b_active," +
            "depend.pk_frame_depend_er,"+
            "depend.pk_frame_depend_on,"+
            "depend.pk_layer_depend_er,"+
            "depend.pk_layer_depend_on,"+
            "depend.pk_job_depend_er,"+
            "depend.pk_job_depend_on "+
        "FROM " +
            "depend " +
        "WHERE " +
            "depend.pk_job_depend_er = ? " +
        "AND " +
            "depend.b_active = true " +
        "AND " +
            "depend.pk_parent IS NULL ";

    @Override
    public List<LightweightDependency> getWhatThisDependsOn(JobInterface job, DependTarget target) {
        String query = GET_WHAT_THIS_JOB_DEPENDS_ON;
        Object[] values = new Object[] { job.getJobId() };
        if (!target.equals(DependTarget.ANY_TARGET)) {
            query = query + " AND depend.str_target = ?";
            values = new Object[] { job.getJobId(), target.toString() };
        }
        return getJdbcTemplate().query(query,DEPEND_MAPPER, values);

    }

    private static final String GET_WHAT_THIS_LAYER_DEPENDS_ON =
        "SELECT " +
            "depend.pk_depend," +
            "depend.str_type," +
            "depend.str_target,"+
            "depend.b_any,"+
            "depend.pk_parent,"+
            "depend.b_active," +
            "depend.pk_frame_depend_er,"+
            "depend.pk_frame_depend_on,"+
            "depend.pk_layer_depend_er,"+
            "depend.pk_layer_depend_on,"+
            "depend.pk_job_depend_er,"+
            "depend.pk_job_depend_on "+
        "FROM " +
            "depend " +
        "WHERE " +
            "depend.pk_layer_depend_er = ? " +
        "AND " +
            "depend.b_active = true " +
        "AND " +
            "depend.pk_parent IS NULL " +
        "AND " +
            "depend.str_type IN (?,?,?,?) ";

    @Override
    public List<LightweightDependency> getWhatThisDependsOn(LayerInterface layer, DependTarget target) {
        if (!target.equals(DependTarget.ANY_TARGET)) {
            String query = GET_WHAT_THIS_LAYER_DEPENDS_ON + " AND str_target = ?";
            return getJdbcTemplate().query(query, DEPEND_MAPPER,
                    layer.getLayerId(), DependType.LAYER_ON_JOB.toString(),
                    DependType.LAYER_ON_LAYER.toString(), DependType.LAYER_ON_FRAME.toString(),
                    DependType.FRAME_BY_FRAME.toString(), target.toString());
        }
        else {
            return getJdbcTemplate().query(GET_WHAT_THIS_LAYER_DEPENDS_ON, DEPEND_MAPPER,
                    layer.getLayerId(), DependType.LAYER_ON_JOB.toString(),
                    DependType.LAYER_ON_LAYER.toString(), DependType.LAYER_ON_FRAME.toString(),
                    DependType.FRAME_BY_FRAME.toString());
        }
    }

    private static final String GET_WHAT_THIS_FRAME_DEPENDS_ON =
        "SELECT " +
            "depend.pk_depend," +
            "depend.str_type," +
            "depend.str_target,"+
            "depend.b_any,"+
            "depend.pk_parent,"+
            "depend.b_active," +
            "depend.pk_frame_depend_er,"+
            "depend.pk_frame_depend_on,"+
            "depend.pk_layer_depend_er,"+
            "depend.pk_layer_depend_on,"+
            "depend.pk_job_depend_er,"+
            "depend.pk_job_depend_on "+
        "FROM " +
            "depend " +
        "WHERE " +
            "depend.pk_frame_depend_er = ? " +
        "AND " +
            "depend.b_active = true " +
        "AND " +
            "depend.str_type IN (?,?,?) ";

    @Override
    public List<LightweightDependency> getWhatThisDependsOn(FrameInterface frame, DependTarget target) {
        if (!target.equals(DependTarget.ANY_TARGET)) {
            String query = GET_WHAT_THIS_FRAME_DEPENDS_ON + " AND depend.str_target = ?";
            return getJdbcTemplate().query(query, DEPEND_MAPPER,
                    frame.getFrameId(), DependType.FRAME_ON_JOB.toString(),
                    DependType.FRAME_ON_LAYER.toString(), DependType.FRAME_ON_FRAME.toString(),
                    target.toString());
        }
        else {
            return getJdbcTemplate().query(GET_WHAT_THIS_FRAME_DEPENDS_ON, DEPEND_MAPPER,
                    frame.getFrameId(), DependType.FRAME_ON_JOB.toString(),
                    DependType.FRAME_ON_LAYER.toString(), DependType.FRAME_ON_FRAME.toString());
        }
    }
}

