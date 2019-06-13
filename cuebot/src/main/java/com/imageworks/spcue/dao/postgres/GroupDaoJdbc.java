
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

import com.imageworks.spcue.EntityCreationError;
import com.imageworks.spcue.EntityModificationError;
import com.imageworks.spcue.EntityRemovalError;
import com.imageworks.spcue.GroupDetail;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.dao.GroupDao;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.util.CueUtil;
import com.imageworks.spcue.util.SqlUtil;
import org.springframework.stereotype.Repository;

@Repository
public class GroupDaoJdbc extends AbstractJdbcDao implements GroupDao {

    private static final int MAX_NESTING_LEVEL = 10;

    @Override
    public String getRootGroupId(ShowInterface show) {
        return getJdbcTemplate().queryForObject(
                "SELECT pk_folder FROM folder WHERE pk_show=? AND pk_parent_folder IS NULL",
                String.class, show.getShowId());
    }

    @Override
    public void deleteGroup(GroupInterface group) {

        if (childGroupCount(group) > 0) {
            throw new EntityRemovalError("failed to delete group " + group.getName() +
                    ", still has sub groups");
        }

        if (childJobCount(group) > 0) {
            throw new EntityRemovalError("failed to delete group " + group.getName() +
                    ", still has sub jobs");
        }

        // reparent all jobs to root group
        getJdbcTemplate().update(
                "UPDATE job SET pk_folder=? WHERE pk_folder=?",
                    getRootGroupId(group), group.getId());

        getJdbcTemplate().update(
                "DELETE FROM folder WHERE pk_parent_folder IS NOT NULL AND pk_folder=?", group.getId());
    }

    public static final String INSERT_GROUP =
        "INSERT INTO " +
            "folder " +
        "( " +
            "pk_folder," +
            "pk_parent_folder,"+
            "pk_show, " +
            "pk_dept,"+
            "str_name " +
        ") " +
        "VALUES (?,?,?,?,?)";

    @Override
    public void insertGroup(GroupDetail group) {
        group.id = SqlUtil.genKeyRandom();
        String parentId = group.parentId;
        try {
            getJdbcTemplate().update(INSERT_GROUP,
                    group.id, parentId, group.showId, group.deptId, group.name);
        } catch (Exception e) {
            throw new EntityCreationError("error creating group, " + e);
        }
    }

    @Override
    public void insertGroup(GroupDetail group, GroupInterface parent) {
        if (parent != null) {
            group.parentId = parent.getGroupId();
        }
        insertGroup(group);
    }

    @Override
    public void updateGroupParent(GroupInterface group, GroupInterface dest) {

        if (group.getGroupId().equals(dest.getGroupId())) {
            throw new EntityModificationError("error moving group, " +
                "cannot move group into itself");
        }

        if (!group.getShowId().equals(dest.getShowId())) {
            throw new EntityModificationError("error moving group, " +
                "cannot move groups between shows");
        }

        int recurse = 0;
        String destParent = dest.getGroupId();
        while (true) {
            destParent = getJdbcTemplate().queryForObject(
                    "SELECT pk_parent_folder FROM folder WHERE pk_folder=?",
                    String.class, destParent);
            if (destParent == null) { break; }
            if (destParent.equals(group.getGroupId())) {
                throw new EntityModificationError("error moving group, you cannot move a group " +
                        "into one of its sub groups");
            }
            recurse++;
            if (recurse > MAX_NESTING_LEVEL) {
                throw new EntityModificationError("error moving group, cannot tell " +
                        "if your moving a group into one of its sub groups");
            }
        }

        int result = getJdbcTemplate().update(
                "UPDATE folder SET pk_parent_folder=? WHERE pk_folder=? AND pk_parent_folder IS NOT NULL",
                dest.getId(), group.getId());

        recurseParentChange(group.getId(), dest.getId());
        if (result == 0) {
            throw new EntityModificationError("error moving group, "
                    + group.getName() + ", the group does not exist or its the top level group");
        }
    }

    @Override
    public void updateName(GroupInterface group, String value) {
        getJdbcTemplate().update(
                "UPDATE folder SET str_name=? WHERE pk_folder=?",
                value, group.getId());
    }

    @Override
    public void updateDefaultJobMaxCores(GroupInterface group, int value) {
        if (value <= 0) { value = CueUtil.FEATURE_DISABLED; }
        if (value < CueUtil.ONE_CORE && value != CueUtil.FEATURE_DISABLED) {
            String msg = "The default max cores for a job must " +
                    "be greater than a single core";
            throw new IllegalArgumentException(msg);
        }
        getJdbcTemplate().update(
                "UPDATE folder SET int_job_max_cores=? WHERE pk_folder=?",
                value, group.getId());
    }

    @Override
    public void updateDefaultJobMinCores(GroupInterface group, int value) {
        if (value <= 0) { value = CueUtil.FEATURE_DISABLED; }
        if (value < CueUtil.ONE_CORE && value != CueUtil.FEATURE_DISABLED) {
            String msg = "The default min cores for a job must " +
                    "be greater than a single core";
            throw new IllegalArgumentException(msg);
        }
        getJdbcTemplate().update(
                "UPDATE folder SET int_job_min_cores=? WHERE pk_folder=?",
                value, group.getId());
    }

    @Override
    public void updateMaxCores(GroupInterface group, int value) {
        if (value < 0) { value = CueUtil.FEATURE_DISABLED; }
        if (value < CueUtil.ONE_CORE && value != CueUtil.FEATURE_DISABLED) {
            String msg = "The group max cores feature must " +
                    "be a whole core or greater, pass in: " + value;
            throw new IllegalArgumentException(msg);
        }

        getJdbcTemplate().update(
                "UPDATE folder_resource SET int_max_cores=? WHERE pk_folder=?",
                value, group.getId());
    }

    @Override
    public void updateMinCores(GroupInterface group, int value) {
        if (value < 0) { value = 0; }
        getJdbcTemplate().update(
                "UPDATE folder_resource SET int_min_cores=? WHERE pk_folder=?",
                value, group.getId());
    }

    private static final String IS_OVER_MIN_CORES =
        "SELECT " +
            "COUNT(1) " +
        "FROM " +
            "job,"+
            "folder_resource fr "+
        "WHERE " +
            "job.pk_folder = fr.pk_folder " +
        "AND " +
            "fr.int_cores > fr.int_min_cores " +
        "AND "+
            "job.pk_job = ?";

    @Override
    public boolean isOverMinCores(JobInterface job) {
        return getJdbcTemplate().queryForObject(IS_OVER_MIN_CORES,
                Integer.class, job.getJobId()) > 0;
    }

    @Override
    public void updateDefaultJobPriority(GroupInterface group, int value) {
        if (value < 0) { value = CueUtil.FEATURE_DISABLED; }
        getJdbcTemplate().update(
                "UPDATE folder SET int_job_priority=? WHERE pk_folder=?",
                value, group.getId());
        if (value !=  CueUtil.FEATURE_DISABLED) {
            getJdbcTemplate().update(
                    "UPDATE job_resource SET int_priority=? WHERE pk_job IN (" +
                    "SELECT pk_job from job WHERE pk_folder=?)",
                    value, group.getId());
        }
    }

    private static final String GET_GROUP_DETAIL =
        "SELECT " +
            "folder.pk_folder, " +
            "folder.int_job_max_cores,"+
            "folder.int_job_min_cores,"+
            "folder.int_job_priority,"+
            "folder.str_name,"+
            "folder.pk_parent_folder,"+
            "folder.pk_show,"+
            "folder.pk_dept,"+
            "folder_level.int_level, " +
            "folder_resource.int_min_cores,"+
            "folder_resource.int_max_cores " +
        "FROM " +
            "folder, "+
            "folder_level, " +
            "folder_resource " +
        "WHERE " +
            "folder.pk_folder = folder_level.pk_folder " +
        "AND " +
            "folder.pk_folder = folder_resource.pk_folder";

    private static final String GET_GROUP_DETAIL_BY_JOB =
        "SELECT " +
            "folder.pk_folder, " +
            "folder.int_job_max_cores,"+
            "folder.int_job_min_cores,"+
            "folder.int_job_priority,"+
            "folder.str_name,"+
            "folder.pk_parent_folder,"+
            "folder.pk_show,"+
            "folder.pk_dept,"+
            "folder_level.int_level, " +
            "folder_resource.int_min_cores,"+
            "folder_resource.int_max_cores " +
        "FROM " +
            "folder, "+
            "folder_level, " +
            "folder_resource, " +
            "job "+
        "WHERE " +
            "folder.pk_folder = folder_level.pk_folder " +
        "AND " +
            "folder.pk_folder = folder_resource.pk_folder " +
        "AND " +
            "job.pk_folder = folder.pk_folder " +
        "AND " +
            "job.pk_job = ?";

    @Override
    public GroupDetail getGroupDetail(String id) {
        return getJdbcTemplate().queryForObject(
                GET_GROUP_DETAIL + " AND folder.pk_folder=?", GROUP_DETAIL_MAPPER, id);
    }

    @Override
    public GroupDetail getGroupDetail(JobInterface job) {
        return getJdbcTemplate().queryForObject(GET_GROUP_DETAIL_BY_JOB,
                GROUP_DETAIL_MAPPER, job.getId());
    }

    @Override
    public GroupDetail getRootGroupDetail(ShowInterface show) {
        return getJdbcTemplate().queryForObject(
                GET_GROUP_DETAIL + " AND folder.pk_show=? AND pk_parent_folder IS NULL",
                GROUP_DETAIL_MAPPER, show.getShowId());
    }

    @Override
    public GroupInterface getGroup(String id) {
        return getJdbcTemplate().queryForObject(
                "SELECT pk_show, pk_folder,str_name FROM folder WHERE pk_folder=?",
                GROUP_MAPPER, id);
    }

    @Override
    public List<GroupInterface> getGroups(List<String> idl) {
        return getJdbcTemplate().query(
                "SELECT pk_show, pk_folder, str_name FROM folder WHERE  " +
                SqlUtil.buildBindVariableArray("pk_folder", idl),
                GROUP_MAPPER, idl.toArray());
    }

    @Override
    public List<GroupInterface> getChildrenRecursive(GroupInterface group) {
        List<GroupInterface> groups = new ArrayList<GroupInterface>(32);
        GroupInterface current = group;
        for (GroupInterface g: getChildren(current)) {
            current = g;
            groups.add(current);
            groups.addAll(getChildrenRecursive(current));
        }
        return groups;
    }

    @Override
    public List<GroupInterface> getChildren(GroupInterface group) {
        return getJdbcTemplate().query(
                "SELECT pk_show, pk_folder, str_name FROM folder WHERE pk_parent_folder = ?",
                GROUP_MAPPER, group.getGroupId());
    }

    private static final String IS_MANAGED =
    	"SELECT " +
    		"COUNT(1) " +
    	"FROM " +
    		"folder, " +
    		"point " +
    	"WHERE " +
    		"folder.pk_show = point.pk_show " +
    	"AND " +
    		"folder.pk_dept = point.pk_dept " +
    	"AND " +
    		"folder.b_exclude_managed = false " +
    	"AND " +
    		"point.b_managed = true " +
    	"AND " +
    		"folder.pk_folder = ?";

    @Override
    public boolean isManaged(GroupInterface group) {
    	return getJdbcTemplate().queryForObject(IS_MANAGED,
    			Integer.class, group.getGroupId()) > 0;
    }

    public static final RowMapper<GroupInterface> GROUP_MAPPER =
        new RowMapper<GroupInterface>() {
            public GroupInterface mapRow(final ResultSet rs, int rowNum) throws SQLException {
                return new GroupInterface() {
                    String id = rs.getString("pk_folder");
                    String show = rs.getString("pk_show");
                    String name = rs.getString("str_name");
                    public String getGroupId() { return id; }
                    public String getShowId() { return show; }
                    public String getId() { return id; }
                    public String getName() { return name; }
                };
        }
    };

    public static final RowMapper<GroupDetail> GROUP_DETAIL_MAPPER =
        new RowMapper<GroupDetail>() {
            public GroupDetail mapRow(ResultSet rs, int rowNum) throws SQLException {
                GroupDetail group = new GroupDetail();
                group.id = rs.getString("pk_folder");
                group.jobMaxCores = rs.getInt("int_job_max_cores");
                group.jobMinCores = rs.getInt("int_job_min_cores");
                group.jobPriority = rs.getInt("int_job_priority");
                group.name = rs.getString("str_name");
                group.parentId = rs.getString("pk_parent_folder");
                group.showId = rs.getString("pk_show");
                group.deptId = rs.getString("pk_dept");
                return group;
        }
    };


    private int childGroupCount(GroupInterface group) {
        return getJdbcTemplate().queryForObject(
                "SELECT COUNT(*) FROM folder WHERE pk_parent_folder=?",
                Integer.class, group.getId());
    }

    private int childJobCount(GroupInterface group) {
        return getJdbcTemplate().queryForObject(
                "SELECT COUNT(*) FROM job WHERE pk_folder=? AND str_state=?",
                Integer.class, group.getId(), JobState.PENDING.toString());
    }

    private void recurseParentChange(final String folderId, final String newParentId) {
        getJdbcTemplate().call(new CallableStatementCreator() {

            public CallableStatement createCallableStatement(Connection con) throws SQLException {
                CallableStatement c = con.prepareCall("{ call recurse_folder_parent_change(?,?) }");
                c.setString(1, folderId);
                c.setString(2, newParentId);
                return c;
            }
        }, new ArrayList<SqlParameter>());
    }
}

