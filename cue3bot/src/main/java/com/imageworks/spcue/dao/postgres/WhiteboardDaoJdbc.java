
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

import com.google.common.collect.Lists;
import com.google.common.collect.Sets;
import com.imageworks.common.spring.remoting.IceServer;
import com.imageworks.spcue.CueClientIce.Action;
import com.imageworks.spcue.CueClientIce.ActionData;
import com.imageworks.spcue.CueClientIce.ActionInterfacePrxHelper;
import com.imageworks.spcue.CueClientIce.Allocation;
import com.imageworks.spcue.CueClientIce.AllocationData;
import com.imageworks.spcue.CueClientIce.AllocationInterfacePrxHelper;
import com.imageworks.spcue.CueClientIce.AllocationStats;
import com.imageworks.spcue.CueClientIce.Comment;
import com.imageworks.spcue.CueClientIce.CommentData;
import com.imageworks.spcue.CueClientIce.CommentInterfacePrxHelper;
import com.imageworks.spcue.CueClientIce.Deed;
import com.imageworks.spcue.CueClientIce.DeedInterfacePrxHelper;
import com.imageworks.spcue.CueClientIce.Department;
import com.imageworks.spcue.CueClientIce.DepartmentData;
import com.imageworks.spcue.CueClientIce.DepartmentInterfacePrxHelper;
import com.imageworks.spcue.CueClientIce.Depend;
import com.imageworks.spcue.CueClientIce.DependData;
import com.imageworks.spcue.CueClientIce.DependInterfacePrxHelper;
import com.imageworks.spcue.CueClientIce.Filter;
import com.imageworks.spcue.CueClientIce.FilterData;
import com.imageworks.spcue.CueClientIce.FilterInterfacePrxHelper;
import com.imageworks.spcue.CueClientIce.Frame;
import com.imageworks.spcue.CueClientIce.FrameData;
import com.imageworks.spcue.CueClientIce.FrameInterfacePrxHelper;
import com.imageworks.spcue.CueClientIce.Group;
import com.imageworks.spcue.CueClientIce.GroupData;
import com.imageworks.spcue.CueClientIce.GroupInterfacePrxHelper;
import com.imageworks.spcue.CueClientIce.GroupStats;
import com.imageworks.spcue.CueClientIce.Host;
import com.imageworks.spcue.CueClientIce.HostData;
import com.imageworks.spcue.CueClientIce.HostInterfacePrxHelper;
import com.imageworks.spcue.CueClientIce.Job;
import com.imageworks.spcue.CueClientIce.JobData;
import com.imageworks.spcue.CueClientIce.JobInterfacePrxHelper;
import com.imageworks.spcue.CueClientIce.JobStats;
import com.imageworks.spcue.CueClientIce.Layer;
import com.imageworks.spcue.CueClientIce.LayerData;
import com.imageworks.spcue.CueClientIce.LayerInterfacePrxHelper;
import com.imageworks.spcue.CueClientIce.LayerStats;
import com.imageworks.spcue.CueClientIce.Matcher;
import com.imageworks.spcue.CueClientIce.MatcherData;
import com.imageworks.spcue.CueClientIce.MatcherInterfacePrxHelper;
import com.imageworks.spcue.CueClientIce.Owner;
import com.imageworks.spcue.CueClientIce.OwnerInterfacePrxHelper;
import com.imageworks.spcue.CueClientIce.Proc;
import com.imageworks.spcue.CueClientIce.ProcData;
import com.imageworks.spcue.CueClientIce.ProcInterfacePrxHelper;
import com.imageworks.spcue.CueClientIce.RenderPartition;
import com.imageworks.spcue.CueClientIce.RenderPartitionInterfacePrxHelper;
import com.imageworks.spcue.CueClientIce.Service;
import com.imageworks.spcue.CueClientIce.ServiceData;
import com.imageworks.spcue.CueClientIce.ServiceInterfacePrxHelper;
import com.imageworks.spcue.CueClientIce.ServiceOverride;
import com.imageworks.spcue.CueClientIce.ServiceOverrideInterfacePrxHelper;
import com.imageworks.spcue.CueClientIce.Show;
import com.imageworks.spcue.CueClientIce.ShowData;
import com.imageworks.spcue.CueClientIce.ShowInterfacePrxHelper;
import com.imageworks.spcue.CueClientIce.ShowStats;
import com.imageworks.spcue.CueClientIce.Subscription;
import com.imageworks.spcue.CueClientIce.SubscriptionData;
import com.imageworks.spcue.CueClientIce.SubscriptionInterfacePrxHelper;
import com.imageworks.spcue.CueClientIce.Task;
import com.imageworks.spcue.CueClientIce.TaskData;
import com.imageworks.spcue.CueClientIce.TaskInterfacePrxHelper;
import com.imageworks.spcue.CueClientIce.UpdatedFrame;
import com.imageworks.spcue.CueClientIce.UpdatedFrameCheckResult;
import com.imageworks.spcue.CueGrpc.Facility;
import com.imageworks.spcue.CueIce.ActionType;
import com.imageworks.spcue.CueIce.ActionValueType;
import com.imageworks.spcue.CueIce.CheckpointState;
import com.imageworks.spcue.CueIce.DependTarget;
import com.imageworks.spcue.CueIce.DependType;
import com.imageworks.spcue.CueIce.FilterType;
import com.imageworks.spcue.CueIce.FrameState;
import com.imageworks.spcue.CueIce.HardwareState;
import com.imageworks.spcue.CueIce.JobState;
import com.imageworks.spcue.CueIce.LayerType;
import com.imageworks.spcue.CueIce.LockState;
import com.imageworks.spcue.CueIce.MatchSubject;
import com.imageworks.spcue.CueIce.MatchType;
import com.imageworks.spcue.CueIce.RenderPartitionType;
import com.imageworks.spcue.CueIce.ThreadMode;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.dao.WhiteboardDao;
import com.imageworks.spcue.dao.criteria.FrameSearch;
import com.imageworks.spcue.dao.criteria.HostSearch;
import com.imageworks.spcue.dao.criteria.JobSearch;
import com.imageworks.spcue.dao.criteria.ProcSearch;
import com.imageworks.spcue.dao.criteria.Sort;
import com.imageworks.spcue.util.Convert;
import com.imageworks.spcue.util.CueUtil;
import org.apache.log4j.Logger;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.List;

public class WhiteboardDaoJdbc extends JdbcDaoSupport implements WhiteboardDao {
    @SuppressWarnings("unused")
    private static final Logger logger = Logger.getLogger(WhiteboardDaoJdbc.class);

    // This is static so the row mappe anonymous classes can get ahold of it
    // for making proxies.
    private static IceServer iceServer;

    public WhiteboardDaoJdbc(IceServer server) {
        WhiteboardDaoJdbc.iceServer = server;
    }

    @Override
    public Service getService(String id) {
        return getJdbcTemplate().queryForObject(
                GET_SERVICE + " WHERE (pk_service=? or str_name=?)",
                SERVICE_MAPPER, id, id);
    }

    @Override
    public Service findService(String name) {
        return getJdbcTemplate().queryForObject(
                GET_SERVICE + " WHERE service.str_name=?",
                SERVICE_MAPPER, name);
    }
    @Override
    public List<Service> getDefaultServices() {
        return getJdbcTemplate().query(GET_SERVICE, SERVICE_MAPPER);
    }

    @Override
    public List<ServiceOverride> getServiceOverrides(com.imageworks.spcue.Show show) {
        return getJdbcTemplate().query(GET_SERVICE_OVERRIDE +
                " AND show_service.pk_show = ?", SERVICE_OVERRIDE_MAPPER, show.getId());
    }

    @Override
    public ServiceOverride getServiceOverride(
            com.imageworks.spcue.Show show, String name) {
        return getJdbcTemplate().queryForObject (
                GET_SERVICE_OVERRIDE +
                " AND show_service.pk_show=? AND (show_service.str_name=? OR" +
                " show_service.pk_show_service=?)",
                SERVICE_OVERRIDE_MAPPER, show.getId(), name, name);
    }

    @Override
    public Filter getFilter(com.imageworks.spcue.Filter filter) {
        return getJdbcTemplate().queryForObject(GET_FILTER + " AND pk_filter=?",
                FILTER_MAPPER, filter.getFilterId());
    }

    @Override
    public Filter findFilter(com.imageworks.spcue.Show show, String name) {
        return getJdbcTemplate().queryForObject(
                GET_FILTER + " AND filter.pk_show=? AND filter.str_name=?",
                FILTER_MAPPER, show.getShowId(), name);
    }

    @Override
    public Filter findFilter(String show, String name) {
        return getJdbcTemplate().queryForObject(
                GET_FILTER + " AND show.str_name=? AND filter.str_name=?",
                FILTER_MAPPER, show, name);
    }

    @Override
    public List<Filter> getFilters(com.imageworks.spcue.Show show) {
        return getJdbcTemplate().query(
                GET_FILTER + " AND show.pk_show=? ORDER BY f_order ASC", FILTER_MAPPER, show.getShowId());
    }

    @Override
    public List<Action> getActions(com.imageworks.spcue.Filter filter) {
        return getJdbcTemplate().query(
                GET_ACTION + " AND filter.pk_filter=? ORDER BY b_stop ASC, ts_created ASC ",
                ACTION_MAPPER, filter.getFilterId());
    }

    @Override
    public List<Matcher> getMatchers(com.imageworks.spcue.Filter filter) {
        return getJdbcTemplate().query(
                GET_MATCHER + " AND filter.pk_filter=? ORDER BY ts_created ASC",
                MATCHER_MAPPER, filter.getFilterId());
    }

    @Override
    public Action getAction(com.imageworks.spcue.Action action) {
        return getJdbcTemplate().queryForObject(
                GET_ACTION + " AND action.pk_action=?",
                ACTION_MAPPER, action.getActionId());
    }

    @Override
    public Matcher getMatcher(com.imageworks.spcue.Matcher matcher) {
        return getJdbcTemplate().queryForObject(
                GET_MATCHER + " AND matcher.pk_matcher=?",
                MATCHER_MAPPER, matcher.getMatcherId());
    }

    @Override
    public Show getShow(String id) {
        return getJdbcTemplate().queryForObject(
                GET_SHOW + " AND show.pk_show=?",
                SHOW_MAPPER, id);
    }

    @Override
    public List<Show> getShows() {
        return getJdbcTemplate().query(GET_SHOW, SHOW_MAPPER);
    }

    @Override
    public List<Show> getActiveShows() {
        return getJdbcTemplate().query(GET_SHOW + " AND b_active=?",
                SHOW_MAPPER, true);
    }

    @Override
    public Show findShow(String name) {
        return getJdbcTemplate().queryForObject(GET_SHOW + " AND show.str_name=?",
                SHOW_MAPPER, name);
    }

    @Override
    public Subscription getSubscription(String id) {
        return getJdbcTemplate().queryForObject(
                GET_SUBSCRIPTION + " AND subscription.pk_subscription=?",
                SUBSCRIPTION_MAPPER, id);
    }

    @Override
    public Subscription findSubscription(String show, String alloc) {
        return getJdbcTemplate().queryForObject(
                GET_SUBSCRIPTION +
                " AND show.str_name=? AND alloc.str_name=?",
                SUBSCRIPTION_MAPPER, show, alloc);
    }

    @Override
    public List<Subscription> getSubscriptions(com.imageworks.spcue.Show show) {
        return getJdbcTemplate().query(
                GET_SUBSCRIPTION + " AND show.pk_show=?",
                SUBSCRIPTION_MAPPER, show.getShowId());
    }

    @Override
    public List<Subscription> getSubscriptions(com.imageworks.spcue.Allocation alloc) {
        return getJdbcTemplate().query(
                GET_SUBSCRIPTION + " AND subscription.pk_alloc=?",
                SUBSCRIPTION_MAPPER, alloc.getAllocationId());
    }

    @Override
    public Allocation findAllocation(String name) {
        return getJdbcTemplate().queryForObject(
                GET_ALLOCATION + " AND alloc.str_name=?",
                ALLOCATION_MAPPER, name);
    }

    @Override
    public Allocation getAllocation(String id) {
        return getJdbcTemplate().queryForObject(GET_ALLOCATION + " AND alloc.pk_alloc=?",
                ALLOCATION_MAPPER, id);
    }

    @Override
    public List<Allocation> getAllocations() {
        return getJdbcTemplate().query(
                GET_ALLOCATION + " ORDER BY alloc.str_name ",
                ALLOCATION_MAPPER);
    }

    @Override
    public List<Allocation> getAllocations(
            com.imageworks.spcue.FacilityInterface facility) {
        return getJdbcTemplate().query(
                GET_ALLOCATION + " AND alloc.pk_facility = ?",
                ALLOCATION_MAPPER, facility.getFacilityId());
    }

    @Override
    public List<Job> getJobs(com.imageworks.spcue.Group group) {
        return getJdbcTemplate().query(
                GET_PENDING_JOBS + " AND job.pk_folder=? ORDER BY job.str_name ASC",
                JOB_MAPPER, group.getId());
    }

    @Override
    public List<String> getJobNames(JobSearch r) {
        return getJdbcTemplate().query(r.getQuery(GET_JOB_NAMES),
                new RowMapper<String>() {
            public String mapRow(ResultSet rs, int rowNum) throws SQLException {
                return rs.getString(1);
            }
        }, r.getValuesArray());
    }

    @Override
    public List<Job> getJobs(JobSearch r) {
        return getJdbcTemplate().query(
                r.getQuery(GET_JOB) + "ORDER BY job.str_name ASC", JOB_MAPPER, r.getValuesArray());
    }

    @Override
    public Job findJob(String name) {
        return getJdbcTemplate().queryForObject(
                GET_PENDING_JOBS + " AND job.str_name=?",
                JOB_MAPPER, name.toLowerCase());
    }

    @Override
    public Job getJob(String id) {
        return getJdbcTemplate().queryForObject(
                GET_JOB + " AND job.pk_job=?",
                JOB_MAPPER, id);
    }

    @Override
    public Layer getLayer(String id) {
        return getJdbcTemplate().queryForObject(
                GET_LAYER + " AND layer.pk_layer=?",
                LAYER_MAPPER, id);
    }

    @Override
    public Layer findLayer(String job, String layer) {
        return getJdbcTemplate().queryForObject(
                GET_LAYER + " AND job.str_state='Pending' AND job.str_name=? AND layer.str_name=?",
                LAYER_MAPPER, job, layer);
    }

    @Override
    public List<Layer> getLayers(com.imageworks.spcue.Job job) {
        String query = GET_LAYER + " AND layer.pk_job=? ORDER BY layer.int_dispatch_order ASC";
        return getJdbcTemplate().query(
                query, LAYER_MAPPER, job.getJobId());
    }

    @Override
    public List<Group> getGroups(com.imageworks.spcue.Show show) {
       List<Group> groups = getJdbcTemplate().query(
                GET_GROUPS + " AND folder.pk_show=? ORDER BY folder_level.int_level ASC, folder.str_name ASC ",
                GROUP_MAPPER, show.getShowId());
       return groups;
    }

    @Override
    public List<Group> getGroups(com.imageworks.spcue.Group group) {
        List<Group> groups = getJdbcTemplate().query(
                 GET_GROUPS + " AND folder.pk_parent_folder=? ORDER BY folder_level.int_level ASC, folder.f_order DESC, folder.str_name ASC ",
                 GROUP_MAPPER, group.getGroupId());
        return groups;
    }

    @Override
    public Group getGroup(String id) {
        return getJdbcTemplate().queryForObject(
                GET_GROUPS + " AND folder.pk_folder=?",
                GROUP_MAPPER, id);
    }

    @Override
    public Group getRootGroup(com.imageworks.spcue.Show show) {
        return getJdbcTemplate().queryForObject(
                GET_GROUPS + " AND show.pk_show=? AND folder.b_default=?",
                GROUP_MAPPER, show.getShowId(), true);
    }

    @Override
    public Frame findFrame(String job, String layer, int frame) {
        return getJdbcTemplate().queryForObject(FIND_FRAME, FRAME_MAPPER, job, layer, frame);
    }

    @Override
    public Frame getFrame(String id) {
        return getJdbcTemplate().queryForObject(
                GET_FRAME + " AND frame.pk_frame=?", FRAME_MAPPER, id);
    }

    @Override
    public List<Frame> getFrames(FrameSearch r) {
        return getJdbcTemplate().query(r.getSortedQuery(GET_FRAMES_CRITERIA),FRAME_MAPPER,
                r.getValuesArray());
    }

    @Override
    public Depend getDepend(com.imageworks.spcue.Depend depend) {
        return getJdbcTemplate().queryForObject(
                GET_DEPEND + " WHERE pk_depend=?",DEPEND_MAPPER, depend.getId());
    }

    @Override
    public Depend getDepend(com.imageworks.spcue.depend.AbstractDepend depend) {
        return getJdbcTemplate().queryForObject(
                GET_DEPEND + " WHERE pk_depend=?",DEPEND_MAPPER, depend.getId());
    }

    @Override
    public List<Depend> getWhatDependsOnThis(com.imageworks.spcue.Job job) {
        return getJdbcTemplate().query(
                GET_DEPEND + " WHERE pk_parent IS NULL AND pk_job_depend_on=?",
                DEPEND_MAPPER, job.getJobId());
    }

    @Override
    public List<Depend> getWhatDependsOnThis(com.imageworks.spcue.Layer layer) {
        return getJdbcTemplate().query(
                GET_DEPEND + " WHERE pk_parent IS NULL AND pk_layer_depend_on=?",
                DEPEND_MAPPER, layer.getLayerId());

    }

    @Override
    public List<Depend> getWhatDependsOnThis(com.imageworks.spcue.Frame frame) {
        return getJdbcTemplate().query(
                GET_DEPEND + " WHERE pk_frame_depend_on=?",
                DEPEND_MAPPER, frame.getFrameId());
    }

    @Override
    public List<Depend> getWhatThisDependsOn(com.imageworks.spcue.Job job) {
        return getJdbcTemplate().query(
                GET_DEPEND + " WHERE pk_parent IS NULL AND pk_layer_depend_er IS NULL AND " +
                        "pk_frame_depend_er IS NULL AND pk_job_depend_er=?",
                DEPEND_MAPPER, job.getJobId());
    }

    @Override
    public List<Depend> getWhatThisDependsOn(com.imageworks.spcue.Layer layer) {
        return getJdbcTemplate().query(
                GET_DEPEND + " WHERE pk_parent IS NULL AND pk_layer_depend_er=?",
                DEPEND_MAPPER, layer.getLayerId());
    }

    @Override
    public List<Depend> getWhatThisDependsOn(com.imageworks.spcue.Frame frame) {
        /*
         * This should show anything that is making the frame dependent.
         */
        return getJdbcTemplate().query(
                GET_DEPEND + " WHERE " +
                        "(pk_job_depend_er=? AND str_type IN ('JobOnJob','JobOnLayer','JobOnFrame')) OR " +
                        "(pk_layer_depend_er=? AND str_type IN ('LayerOnJob','LayerOnLayer','LayerOnFrame')) " +
                        "OR (pk_frame_depend_er=?)",
                DEPEND_MAPPER, frame.getJobId(), frame.getLayerId(), frame.getFrameId());
    }

    @Override
    public List<Depend> getDepends(com.imageworks.spcue.Job job) {
        return getJdbcTemplate().query(
                GET_DEPEND + " WHERE pk_job_depend_er=? AND str_type != 'FrameOnFrame'",
                DEPEND_MAPPER, job.getJobId());
    }

    @Override
    public Depend getDepend(String id) {
        return getJdbcTemplate().queryForObject(
                GET_DEPEND + " WHERE pk_depend=?",DEPEND_MAPPER,id);
    }

    @Override
    public Group findGroup(String show, String group) {
        return getJdbcTemplate().queryForObject(
                GET_GROUPS + " AND show.str_name=? AND folder.str_name=?",
                GROUP_MAPPER, show, group);
    }

    @Override
    public Host findHost(String name) {
        return getJdbcTemplate().queryForObject(
                GET_HOST + " AND host.str_name=?", HOST_MAPPER, name);
    }

    @Override
    public List<Host> getHosts(HostSearch r) {
        return getJdbcTemplate().query(r.getQuery(GET_HOST), HOST_MAPPER,
                r.getValuesArray());
    }

    @Override
    public Host getHost(String id) {
        return getJdbcTemplate().queryForObject(
                GET_HOST + " AND host.pk_host=?", HOST_MAPPER, id);
    }

    @Override
    public List<Proc> getProcs(com.imageworks.spcue.Host h) {
        ProcSearch r = new ProcSearch();
        r.addPhrase("host.pk_host", h.getHostId());
        r.addSort(Sort.asc("host.str_name"));
        r.addSort(Sort.asc("proc.ts_dispatched"));
        return getProcs(r);
    }

    @Override
    public List<Proc> getProcs(ProcSearch p) {
        p.addSort(Sort.asc("host.str_name"));
        p.addSort(Sort.asc("proc.ts_dispatched"));
        return getJdbcTemplate().query(p.getQuery(GET_PROC),
                PROC_MAPPER, p.getValuesArray());
    }

    @Override
    public List<Comment> getComments(com.imageworks.spcue.Host h) {
        return getJdbcTemplate().query(
                GET_HOST_COMMENTS, COMMENT_MAPPER, h.getHostId());
    }

    @Override
    public List<Comment> getComments(com.imageworks.spcue.Job j) {
        return getJdbcTemplate().query(
                GET_JOB_COMMENTS, COMMENT_MAPPER, j.getJobId());
    }

    @Override
    public UpdatedFrameCheckResult getUpdatedFrames(com.imageworks.spcue.Job job,
            List<com.imageworks.spcue.Layer> layers, int epochSeconds) {

        if ((System.currentTimeMillis() / 1000) - epochSeconds > 60) {
            long timeDiff = System.currentTimeMillis() - epochSeconds;
            throw new IllegalArgumentException("the last update timestamp cannot be over " +
                    "a minute off the current time, difference was: " + timeDiff);
        }

        UpdatedFrameCheckResult result = new UpdatedFrameCheckResult();
        result.state = JobState.valueOf(getJdbcTemplate().queryForObject(
                "SELECT str_state FROM job WHERE pk_job=?",String.class, job.getJobId()));

        FrameSearch r = new FrameSearch(job);
        List<String> lids = new ArrayList<String>(layers.size());
        for (com.imageworks.spcue.Layer l: layers) {
            lids.add(l.getLayerId());
        }
        r.addPhrase("layer.pk_layer",lids);
        r.addGreaterThanTimestamp("frame.ts_updated", epochSeconds);
        r.setMaxResults(100);

        result.updatedFrames = getJdbcTemplate().query(
                r.getQuery(GET_UPDATED_FRAME), UPDATED_FRAME_MAPPER, r.getValuesArray());
        result.serverTime = (int) (System.currentTimeMillis() / 1000) - 1;

        return result;
    }

    @Override
    public Department getDepartment(
            com.imageworks.spcue.Show show, String name) {
        return getJdbcTemplate().queryForObject(
                GET_DEPARTMENT, DEPARTMENT_MAPPER,
                show.getShowId(), name);
    }

    @Override
    public List<Department> getDepartments (
            com.imageworks.spcue.Show show) {
        return getJdbcTemplate().query(
                GET_DEPARTMENTS, DEPARTMENT_MAPPER,
                show.getShowId());
    }

    @Override
    public List<String> getDepartmentNames() {
        return getJdbcTemplate().query("SELECT str_name FROM dept ORDER BY str_name ASC",
            new RowMapper<String>() {
                public String mapRow(ResultSet rs, int row) throws SQLException {
                    return rs.getString("str_name");
                }
            });
    }

    @Override
    public Task getTask(com.imageworks.spcue.Show show, com.imageworks.spcue.Department dept, String shot) {
        return getJdbcTemplate().queryForObject(
                GET_TASK + " AND point.pk_show=? AND point.pk_dept=? AND task.str_shot=?",
                TASK_MAPPER, show.getShowId(), dept.getDepartmentId(), shot);
    }

    @Override
    public List<Task> getTasks(com.imageworks.spcue.Show show, com.imageworks.spcue.Department dept) {
        if (dept == null) {
            return getJdbcTemplate().query(
                    GET_TASK + " AND point.pk_show=? ORDER BY task.str_shot",
                    TASK_MAPPER, show.getShowId());
        } else {
            return getJdbcTemplate().query(
                    GET_TASK + " AND point.pk_show=? AND point.pk_dept=? ORDER BY task.str_shot",
                    TASK_MAPPER, show.getShowId(), dept.getDepartmentId());
        }
    }


    @Override
    public List<Deed> getDeeds(com.imageworks.spcue.Owner owner) {
        return getJdbcTemplate().query(
                QUERY_FOR_DEED + " AND owner.pk_owner=?",
                DEED_MAPPER, owner.getId());
    }

    @Override
    public List<Deed> getDeeds(com.imageworks.spcue.Show show) {
        return getJdbcTemplate().query(
                QUERY_FOR_DEED + " AND show.pk_show=?",
                DEED_MAPPER, show.getId());
    }

    @Override
    public Host getHost(com.imageworks.spcue.Deed deed) {
        return getJdbcTemplate().queryForObject(
                GET_HOST + " AND host.pk_host=?",
                HOST_MAPPER, deed.id);
    }

    @Override
    public Deed getDeed(com.imageworks.spcue.Host host) {
        return getJdbcTemplate().queryForObject(
                QUERY_FOR_DEED + " AND host.pk_host=?",
                DEED_MAPPER, host.getHostId());
    }

    @Override
    public List<Host> getHosts(com.imageworks.spcue.Owner owner) {
        StringBuilder sb = new StringBuilder(4096);
        String query = GET_HOST;
        query = query.replace("FROM " , "FROM owner, deed,");
        sb.append(query);
        sb.append("AND deed.pk_host = host.pk_host ");
        sb.append("AND deed.pk_owner = owner.pk_owner ");
        sb.append("AND owner.pk_owner = ?");

        return getJdbcTemplate().query(
                sb.toString(), HOST_MAPPER, owner.getId());
    }

    @Override
    public Owner getOwner(com.imageworks.spcue.Deed deed) {
        return getJdbcTemplate().queryForObject(
                QUERY_FOR_OWNER + " AND " +
                "pk_owner = (SELECT deed.pk_owner FROM deed " +
                "WHERE pk_deed=?)", OWNER_MAPPER, deed.getId());
    }

    @Override
    public Owner getOwner(
            com.imageworks.spcue.Host host) {
        return getJdbcTemplate().queryForObject(
                QUERY_FOR_OWNER + " AND " +
                "pk_owner = (SELECT deed.pk_owner FROM deed " +
                "WHERE pk_host=?)", OWNER_MAPPER, host.getHostId());
    }

    @Override
    public List<Owner> getOwners(com.imageworks.spcue.Show show) {
        return getJdbcTemplate().query(
                QUERY_FOR_OWNER + " AND owner.pk_show=?", OWNER_MAPPER,
                show.getShowId());
    }


    @Override
    public RenderPartition getRenderPartition(LocalHostAssignment l) {
        return getJdbcTemplate().queryForObject(QUERY_FOR_RENDER_PART +
                "WHERE host_local.pk_host_local = ?",
                RENDER_PARTION_MAPPER, l.getId());
    }


    @Override
    public List<RenderPartition> getRenderPartitions(
            com.imageworks.spcue.Host host) {
        return getJdbcTemplate().query(QUERY_FOR_RENDER_PART +
                "WHERE host_local.pk_host = ?",
                RENDER_PARTION_MAPPER, host.getHostId());
    }


    @Override
    public Owner getOwner(String name) {
        return getJdbcTemplate().queryForObject(
                QUERY_FOR_OWNER + " AND " +
                        "(" +
                            "owner.str_username = ? " +
                        "OR " +
                            "owner.pk_owner = ?" +
                        ")", OWNER_MAPPER, name, name);
    }

    @Override
    public Facility getFacility(String name) {
        return getJdbcTemplate().queryForObject(
                QUERY_FOR_FACILITY +
                " WHERE facility.pk_facility = ? OR facility.str_name = ?",
                FACILITY_MAPPER, name, name);
    }

    @Override
    public List<Facility> getFacilities() {
        return getJdbcTemplate().query(
                QUERY_FOR_FACILITY, FACILITY_MAPPER);
    }

    /*
     * Row Mappers
     */

    public static final RowMapper<Matcher> MATCHER_MAPPER =
        new RowMapper<Matcher>() {
            public Matcher mapRow(ResultSet rs, int rowNum) throws SQLException {
                Matcher matcher = new Matcher();
                MatcherData data = new MatcherData();

                matcher.data = data;
                matcher.proxy = MatcherInterfacePrxHelper.uncheckedCast(iceServer.getAdapter()
                        .createProxy(new Ice.Identity(rs.getString("pk_matcher"),"manageMatcher")));

                data.input = rs.getString("str_value");
                data.subject = MatchSubject.valueOf(rs.getString("str_subject"));
                data.type = MatchType.valueOf(rs.getString("str_match"));
                return matcher;
            }
    };
    public static final RowMapper<Filter> FILTER_MAPPER =
        new RowMapper<Filter>() {
            public Filter mapRow(ResultSet rs, int rowNum) throws SQLException {
                Filter filter = new Filter();
                FilterData data = new FilterData();

                filter.data = data;
                filter.proxy = FilterInterfacePrxHelper.uncheckedCast(iceServer.getAdapter()
                        .createProxy(new Ice.Identity(rs.getString("pk_filter"),"manageFilter")));

                data.type = FilterType.valueOf(rs.getString("str_type"));
                data.order = rs.getInt("f_order");
                data.name = rs.getString("str_name");
                data.enabled = rs.getBoolean("b_enabled");

                return filter;
            }
    };

    public static final RowMapper<Action> ACTION_MAPPER =
        new RowMapper<Action>() {
            public Action mapRow(ResultSet rs, int rowNum) throws SQLException {
                Action action = new Action();
                ActionData data = new ActionData();

                action.data = data;
                action.proxy = ActionInterfacePrxHelper.uncheckedCast(iceServer.getAdapter()
                        .createProxy(new Ice.Identity(rs.getString("pk_action"),"manageAction")));

                data.booleanValue = false;
                data.groupValue = null;
                data.integerValue = 0;
                data.floatValue = 0f;
                data.stringValue = "";
                data.type = ActionType.valueOf(rs.getString("str_action"));
                data.valueType = ActionValueType.valueOf(rs.getString("str_value_type"));

                switch (data.valueType) {
                    case GroupType:
                        data.groupValue =  GroupInterfacePrxHelper.uncheckedCast(iceServer.getAdapter()
                                .createProxy(new Ice.Identity(rs.getString("pk_folder"),"manageGroup")));
                        break;
                    case StringType:
                        data.stringValue = rs.getString("str_value");
                        break;
                    case IntegerType:
                        data.integerValue = rs.getInt("int_value");
                        break;
                    case FloatType:
                        data.floatValue = rs.getFloat("float_value");
                        break;
                    case BooleanType:
                        data.booleanValue = rs.getBoolean("b_value");
                        break;
                }
                return action;
            }
    };

    public static final RowMapper<Facility> FACILITY_MAPPER =
        new RowMapper<Facility>() {
            public Facility mapRow(ResultSet rs, int rowNum) throws SQLException {
                return Facility.newBuilder().setName(rs.getString("str_name")).build();
            }
    };


    public static final RowMapper<Deed> DEED_MAPPER =
        new RowMapper<Deed>() {
            public Deed mapRow(ResultSet rs, int rowNum) throws SQLException {
                Deed d = new Deed();
                d.host = rs.getString("str_host");
                d.owner = rs.getString("str_username");
                d.show = rs.getString("str_show");
                d.blackout = rs.getBoolean("b_blackout");

                d.blackoutStartTime = new int[1];
                d.blackoutStopTime = new int[1];

                d.blackoutStartTime[0] = rs.getInt("int_blackout_start");
                d.blackoutStopTime[0] = rs.getInt("int_blackout_stop");

                d.proxy = DeedInterfacePrxHelper.uncheckedCast(
                        iceServer.getAdapter().createProxy(
                                new Ice.Identity(
                                        rs.getString("pk_deed"),
                                        "manageDeed")));

                return d;
            }
    };

    public static final RowMapper<RenderPartition>
        RENDER_PARTION_MAPPER = new RowMapper<RenderPartition>() {
        public RenderPartition mapRow(ResultSet rs, int rowNum) throws SQLException {

            RenderPartition r = new RenderPartition();

            r.cores = rs.getInt("int_cores_max") - rs.getInt("int_cores_idle");
            r.maxCores = rs.getInt("int_cores_max");
            r.threads = rs.getInt("int_threads");
            r.maxMemory = rs.getLong("int_mem_max");
            r.memory =  rs.getLong("int_mem_max") - rs.getLong("int_mem_idle");
            r.maxGpu = rs.getLong("int_gpu_max");
            r.host = rs.getString("str_host_name");
            r.job = rs.getString("str_job_name");
            r.renderPartType = RenderPartitionType.valueOf(rs.getString("str_type"));

            r.layer = new String[1];
            r.frame = new String[1];

            if (rs.getString("str_layer_name") != null) {
                r.layer[0] = rs.getString("str_layer_name");
            }

            if (rs.getString("str_frame_name") != null) {
                r.frame[0] = rs.getString("str_frame_name") ;
            }

            r.proxy = RenderPartitionInterfacePrxHelper.uncheckedCast(
                    iceServer.getAdapter().createProxy(
                            new Ice.Identity(
                                    rs.getString("pk_host_local"),
                                    "manageRenderPartition")));

            return r;

        }
};

    public static final RowMapper<Owner>
        OWNER_MAPPER = new RowMapper<Owner>() {
            public Owner mapRow(ResultSet rs, int rowNum) throws SQLException {
                Owner o = new Owner();
                o.name = rs.getString("str_username");
                o.show = rs.getString("str_show");
                o.hostCount = rs.getInt("host_count");
                o.proxy = OwnerInterfacePrxHelper.uncheckedCast(
                        iceServer.getAdapter().createProxy(
                                new Ice.Identity(
                                        rs.getString("pk_owner"),
                                        "manageOwner")));

                return o;
            }
    };

    public static final RowMapper<Department> DEPARTMENT_MAPPER =
        new RowMapper<Department>() {
        public Department mapRow(ResultSet rs, int row) throws SQLException {
            Department d = new Department();
            d.data = new DepartmentData();
            d.data.dept = rs.getString("str_dept");
            d.data.name = rs.getString("str_name");
            d.data.tiManaged = rs.getBoolean("b_managed");
            d.data.tiTask = rs.getString("str_ti_task");
            d.data.minCores = Convert.coreUnitsToCores(rs.getInt("int_min_cores"));
            d.proxy = DepartmentInterfacePrxHelper.uncheckedCast(iceServer.getAdapter()
                    .createProxy(new Ice.Identity(rs.getString("pk_point"),"manageDepartment")));
            return d;
        }
    };

    public static final RowMapper<Proc> PROC_MAPPER =
        new RowMapper<Proc>() {
        public Proc mapRow(ResultSet rs, int row) throws SQLException {
            Proc proc = new Proc();
            proc.data = new ProcData();
            proc.data.name  = CueUtil.buildProcName(rs.getString("host_name"),
                    rs.getInt("int_cores_reserved"));

            proc.data.reservedCores = Convert.coreUnitsToCores(rs.getInt("int_cores_reserved"));
            proc.data.reservedMemory = rs.getLong("int_mem_reserved");
            proc.data.reservedGpu = rs.getLong("int_gpu_reserved");
            proc.data.usedMemory = rs.getLong("int_mem_used");
            proc.data.frameName = rs.getString("frame_name");
            proc.data.jobName = rs.getString("job_name");
            proc.data.groupName = rs.getString("folder_name");
            proc.data.showName = rs.getString("show_name");
            proc.data.pingTime = (int) (rs.getTimestamp("ts_ping").getTime() / 1000);
            proc.data.bookedTime = (int) (rs.getTimestamp("ts_booked").getTime() / 1000);
            proc.data.dispatchTime = (int) (rs.getTimestamp("ts_dispatched").getTime() / 1000);
            proc.data.unbooked = rs.getBoolean("b_unbooked");
            proc.data.logPath = String.format("%s/%s.%s.rqlog",
                    rs.getString("str_log_dir"),rs.getString("job_name"),
                    rs.getString("frame_name"));
            proc.data.redirectTarget = rs.getString("str_redirect");
            proc.data.services = rs.getString("str_services").split(",");
            proc.proxy = ProcInterfacePrxHelper.uncheckedCast(iceServer.getAdapter()
                    .createProxy(new Ice.Identity(rs.getString("pk_proc"),"manageProc")));
            return proc;
        }
    };

    public static final RowMapper<Task> TASK_MAPPER =
        new RowMapper<Task>() {
        public Task mapRow(ResultSet rs, int row) throws SQLException {
            Task t = new Task();
            t.data = new TaskData();
            t.data.dept = rs.getString("str_dept");
            t.data.shot = rs.getString("str_shot");
            t.data.minCores = Convert.coreUnitsToWholeCores(rs.getInt("int_min_cores"));
            t.data.adjustCores = Convert.coreUnitsToWholeCores(rs.getInt("int_adjust_cores"));
            t.proxy = TaskInterfacePrxHelper.uncheckedCast(iceServer.getAdapter()
                    .createProxy(new Ice.Identity(rs.getString("pk_task"),"manageTask")));
            return t;
        }
    };

    public static final RowMapper<Comment> COMMENT_MAPPER =
        new RowMapper<Comment>() {

        public Comment mapRow(ResultSet rs, int row) throws SQLException {
            Comment comment = new Comment();
            comment.data = new CommentData();
            comment.data.message = rs.getString("str_message");
            comment.data.subject = rs.getString("str_subject");
            comment.data.timestamp = (int)(rs.getTimestamp("ts_created").getTime() / 1000);
            comment.data.user = rs.getString("str_user");
            comment.proxy = CommentInterfacePrxHelper.uncheckedCast(iceServer.getAdapter()
                    .createProxy(new Ice.Identity(rs.getString("pk_comment"),"manageComment")));
            return comment;
        }
    };

    public static final HostData mapHostData(ResultSet rs) throws SQLException {
        HostData data = new HostData();
        data.name = rs.getString("host_name");
        data.allocName = rs.getString("alloc_name");
        data.bootTime = (int) (rs.getTimestamp("ts_booted").getTime() / 1000);
        data.freeMcp = rs.getLong("int_mcp_free");
        data.freeMemory = rs.getLong("int_mem_free");
        data.freeSwap = rs.getLong("int_swap_free");
        data.freeGpu = rs.getLong("int_gpu_free");
        data.load = rs.getInt("int_load");
        data.nimbyEnabled = rs.getBoolean("b_nimby");
        data.cores = Convert.coreUnitsToCores(rs.getInt("int_cores"));
        data.idleCores = Convert.coreUnitsToCores(rs.getInt("int_cores_idle"));
        data.memory = rs.getLong("int_mem");
        data.idleMemory = rs.getLong("int_mem_idle");
        data.gpu = rs.getLong("int_gpu");
        data.idleGpu = rs.getLong("int_gpu_idle");
        data.state = HardwareState.valueOf(rs.getString("host_state"));
        data.totalMcp = rs.getLong("int_mcp_total");
        data.totalMemory = rs.getLong("int_mem_total");
        data.totalSwap = rs.getLong("int_swap_total");
        data.totalGpu = rs.getLong("int_gpu_total");
        data.pingTime = (int) (rs.getTimestamp("ts_ping").getTime() / 1000);
        data.lockState = LockState.valueOf(rs.getString("str_lock_state"));
        data.hasComment = rs.getBoolean("b_comment");
        data.threadMode = ThreadMode.valueOf(rs.getInt("int_thread_mode"));
        data.os = rs.getString("str_os");

        String tags =  rs.getString("str_tags");
        if (tags != null)
            data.tags = tags.split(" ");
        else
            data.tags = new String[0];

        return data;
    }

    public static final RowMapper<Host> HOST_MAPPER =
        new RowMapper<Host>() {
        public Host mapRow(ResultSet rs, int row) throws SQLException {
            String hid = rs.getString("pk_host");
            Host host = new Host();
            host.data = mapHostData(rs);
            host.proxy = HostInterfacePrxHelper.uncheckedCast(iceServer.getAdapter()
                    .createProxy(new Ice.Identity(hid,"manageHost")));
            return host;
        }
    };

    public static final RowMapper<Depend> DEPEND_MAPPER =
        new RowMapper<Depend>() {
            public Depend mapRow(ResultSet rs, int rowNum) throws SQLException {
                Depend depend = new Depend();
                DependData data = new DependData();
                data.active = rs.getBoolean("b_active");
                data.anyFrame = rs.getBoolean("b_any");
                data.dependErFrame = rs.getString("depend_er_frame");
                data.dependErLayer = rs.getString("depend_er_layer");
                data.dependErJob = rs.getString("depend_er_job");
                data.dependOnFrame = rs.getString("depend_on_frame");
                data.dependOnLayer = rs.getString("depend_on_layer");
                data.dependOnJob = rs.getString("depend_on_job");
                data.type = DependType.valueOf(rs.getString("str_type"));
                data.target = DependTarget.valueOf(rs.getString("str_target"));
                depend.data = data;
                depend.proxy = DependInterfacePrxHelper.uncheckedCast(iceServer.getAdapter()
                        .createProxy(new Ice.Identity(rs.getString("pk_depend"),"manageDepend")));

                return depend;
            }
    };

    public static final RowMapper<Allocation> ALLOCATION_MAPPER =
        new RowMapper<Allocation>() {
            public Allocation mapRow(ResultSet rs, int rowNum) throws SQLException {
                Allocation a = new Allocation();

                a.data = new AllocationData();
                a.stats = new AllocationStats();
                a.data.name = rs.getString("str_name");
                a.data.facility = rs.getString("facility_name");
                a.data.tag = rs.getString("str_tag");
                a.data.billable = rs.getBoolean("b_billable");
                a.stats.cores = Convert.coreUnitsToCores(rs.getInt("int_cores"));
                a.stats.availableCores = Convert.coreUnitsToCores(rs.getInt("int_available_cores"));
                a.stats.idleCores =  Convert.coreUnitsToCores(rs.getInt("int_idle_cores"));
                a.stats.runningCores = Convert.coreUnitsToCores(rs.getInt("int_running_cores"));
                a.stats.lockedCores = Convert.coreUnitsToCores(rs.getInt("int_locked_cores"));
                a.stats.hosts = rs.getInt("int_hosts");
                a.stats.downHosts = rs.getInt("int_down_hosts");
                a.stats.lockedHosts = rs.getInt("int_locked_hosts");

                a.proxy = AllocationInterfacePrxHelper.uncheckedCast(iceServer.getAdapter()
                        .createProxy(new Ice.Identity(rs.getString("pk_alloc"),"manageAllocation")));
                return a;
            }
    };

    private static final RowMapper<Group> GROUP_MAPPER =
        new RowMapper<Group>() {

            public Group mapRow(ResultSet rs, int rowNum) throws SQLException {
                Group group = new Group();
                group.data = new GroupData();
                group.stats = new GroupStats();

                group.data.name = rs.getString("group_name");
                group.data.department = rs.getString("str_dept");

                group.data.defaultJobPriority = rs.getInt("int_job_priority");
                group.data.defaultJobMinCores =
                    Convert.coreUnitsToCores(rs.getInt("int_job_min_cores"));
                group.data.defaultJobMaxCores =
                    Convert.coreUnitsToCores(rs.getInt("int_job_max_cores"));
                group.data.maxCores = Convert.coreUnitsToCores(rs.getInt("int_max_cores"));
                group.data.minCores = Convert.coreUnitsToCores(rs.getInt("int_min_cores"));

                group.data.level = rs.getInt("int_level");
                group.stats.deadFrames = rs.getInt("int_dead_count");
                group.stats.runningFrames = rs.getInt("int_running_count");
                group.stats.waitingFrames = rs.getInt("int_waiting_count");
                group.stats.dependFrames = rs.getInt("int_depend_count");
                group.stats.pendingJobs = rs.getInt("int_job_count");
                group.stats.reservedCores =  Convert.coreUnitsToCores(rs.getInt("int_cores"));

                group.proxy = GroupInterfacePrxHelper.uncheckedCast(iceServer.getAdapter()
                        .createProxy(new Ice.Identity(rs.getString("pk_folder"),"manageGroup")));
                return group;
        }
    };

    public static final RowMapper<Job> JOB_MAPPER =
        new RowMapper<Job>() {
            public Job mapRow(ResultSet rs, int rowNum) throws SQLException {
                Job job = new Job();
                job.data = new JobData();
                job.data.logDir = rs.getString("str_log_dir");
                job.data.maxCores = Convert.coreUnitsToCores(rs.getInt("int_max_cores"));
                job.data.minCores = Convert.coreUnitsToCores(rs.getInt("int_min_cores"));
                job.data.name = rs.getString("str_name");
                job.data.priority = rs.getInt("int_priority");
                job.data.shot = rs.getString("str_shot");
                job.data.show = rs.getString("str_show");
                job.data.facility = rs.getString("facility_name");
                job.data.group = rs.getString("group_name");
                job.data.state = JobState.valueOf(rs.getString("str_state"));
                job.data.uid = rs.getInt("int_uid");
                job.data.user = rs.getString("str_user");
                job.data.isPaused = rs.getBoolean("b_paused");
                job.data.hasComment = rs.getBoolean("b_comment");
                job.data.autoEat = rs.getBoolean("b_autoeat");
                job.data.startTime = (int) (rs.getTimestamp("ts_started").getTime() / 1000);
                job.data.os = rs.getString("str_os");

                Timestamp ts = rs.getTimestamp("ts_stopped");
                if (ts != null) {
                    job.data.stopTime = (int) (ts.getTime() / 1000);
                }
                else {
                    job.data.stopTime = 0;
                }

                job.stats = mapJobStats(rs);
                job.proxy = JobInterfacePrxHelper.uncheckedCast(iceServer.getAdapter()
                        .createProxy(new Ice.Identity(rs.getString("pk_job"),"manageJob")));

                return job;
            }
        };

        public static JobStats mapJobStats(ResultSet rs) throws SQLException {

            JobStats stats = new JobStats();

            stats.reservedCores = Convert.coreUnitsToCores(rs.getInt("int_cores"));
            stats.maxRss = rs.getLong("int_max_rss");

            stats.totalFrames = rs.getInt("int_frame_count");
            stats.totalLayers = rs.getInt("int_layer_count");
            stats.waitingFrames = rs.getInt("int_waiting_count");
            stats.runningFrames = rs.getInt("int_running_count");
            stats.deadFrames = rs.getInt("int_dead_count");
            stats.succeededFrames = rs.getInt("int_succeeded_count");
            stats.eatenFrames = rs.getInt("int_eaten_count");
            stats.dependFrames = rs.getInt("int_depend_count");
            stats.pendingFrames = stats.waitingFrames + stats.dependFrames;

            stats.failedCoreSec = rs.getLong("int_core_time_fail");
            stats.renderedCoreSec = rs.getLong("int_core_time_success");
            stats.totalCoreSec =  stats.failedCoreSec + stats.renderedCoreSec;

            stats.renderedFrameCount =  rs.getLong("int_frame_success_count");
            stats.failedFrameCount = rs.getLong("int_frame_fail_count");
            stats.highFrameSec = rs.getInt("int_clock_time_high");

            if (stats.renderedFrameCount > 0) {
                stats.avgFrameSec  =
                    (int) (rs.getLong("int_clock_time_success") / stats.renderedFrameCount);
                stats.avgCoreSec =
                    (int) (stats.renderedCoreSec / stats.renderedFrameCount);
                stats.remainingCoreSec = stats.pendingFrames * stats.avgCoreSec;
            }
            else {
                stats.avgFrameSec = 0;
                stats.avgCoreSec = 0;
                stats.remainingCoreSec = 0;
            }

            return stats;
        }

        public static final RowMapper<Layer> LAYER_MAPPER =
            new RowMapper<Layer>() {
                public Layer mapRow(ResultSet rs, int rowNum) throws SQLException {
                    Layer layer = new Layer();
                    layer.data = new LayerData();
                    layer.stats =  new LayerStats();

                    layer.data.chunkSize = rs.getInt("int_chunk_size");
                    layer.data.dispatchOrder = rs.getInt("int_dispatch_order");
                    layer.data.name = rs.getString("str_name");
                    layer.data.range = rs.getString("str_range");
                    layer.data.minCores = Convert.coreUnitsToCores(rs.getInt("int_cores_min"));
                    layer.data.maxCores = Convert.coreUnitsToCores(rs.getInt("int_cores_max"));
                    layer.data.isThreadable = rs.getBoolean("b_threadable");
                    layer.data.minMemory = rs.getLong("int_mem_min");
                    layer.data.minGpu = rs.getLong("int_gpu_min");
                    layer.data.type = LayerType.valueOf(rs.getString("str_type"));
                    layer.data.tags = Sets.newHashSet(
                            rs.getString("str_tags").
                            replaceAll(" ","").split("\\|"));
                    layer.data.services = rs.getString("str_services").split(",");
                    layer.data.memoryOptimzerEnabled = rs.getBoolean("b_optimize");

                    layer.stats.reservedCores = Convert.coreUnitsToCores(rs.getInt("int_cores"));
                    layer.stats.maxRss = rs.getLong("int_max_rss");

                    layer.stats.totalFrames = rs.getInt("int_total_count");
                    layer.stats.waitingFrames = rs.getInt("int_waiting_count");
                    layer.stats.runningFrames = rs.getInt("int_running_count");
                    layer.stats.deadFrames = rs.getInt("int_dead_count");
                    layer.stats.succeededFrames = rs.getInt("int_succeeded_count");
                    layer.stats.eatenFrames = rs.getInt("int_eaten_count");
                    layer.stats.dependFrames = rs.getInt("int_depend_count");
                    layer.stats.pendingFrames = layer.stats.waitingFrames + layer.stats.dependFrames;

                    layer.stats.failedCoreSec = rs.getLong("int_core_time_fail");
                    layer.stats.renderedCoreSec = rs.getLong("int_core_time_success");
                    layer.stats.totalCoreSec =  layer.stats.failedCoreSec + layer.stats.renderedCoreSec;

                    layer.stats.renderedFrameCount =  rs.getLong("int_frame_success_count");
                    layer.stats.failedFrameCount = rs.getLong("int_frame_fail_count");
                    layer.stats.highFrameSec = rs.getInt("int_clock_time_high");
                    layer.stats.lowFrameSec = rs.getInt("int_clock_time_low");

                    if (layer.stats.renderedFrameCount > 0) {
                        layer.stats.avgFrameSec  =
                            (int) (rs.getLong("int_clock_time_success") / layer.stats.renderedFrameCount);
                        layer.stats.avgCoreSec =
                            (int) (layer.stats.renderedCoreSec / layer.stats.renderedFrameCount);
                        layer.stats.remainingCoreSec = layer.stats.pendingFrames * layer.stats.avgCoreSec;
                    }
                    else {
                        layer.stats.avgFrameSec = 0;
                        layer.stats.avgCoreSec = 0;
                        layer.stats.remainingCoreSec = 0;
                    }

                    layer.proxy = LayerInterfacePrxHelper.uncheckedCast(iceServer.getAdapter()
                            .createProxy(new Ice.Identity(rs.getString("pk_layer"),"manageLayer")));

                    layer.parent = JobInterfacePrxHelper.uncheckedCast(iceServer.getAdapter()
                            .createProxy(new Ice.Identity(rs.getString("pk_job"),"manageJob")));

                    return layer;
                }
    };

    public static final RowMapper<Subscription> SUBSCRIPTION_MAPPER =
        new RowMapper<Subscription>() {
            public Subscription mapRow(ResultSet rs, int rowNum) throws SQLException {
                Subscription s = new Subscription();
                s.data = new SubscriptionData();
                s.data.burst =  Convert.coreUnitsToCores(rs.getInt("int_burst"));
                s.data.name = rs.getString("name");
                s.data.reservedCores = Convert.coreUnitsToCores(rs.getInt("int_cores"));
                s.data.size =  Convert.coreUnitsToCores(rs.getInt("int_size"));
                s.data.allocationName = rs.getString("alloc_name");
                s.data.showName = rs.getString("show_name");
                s.data.facility = rs.getString("facility_name");

                s.proxy = SubscriptionInterfacePrxHelper.uncheckedCast(iceServer.getAdapter()
                        .createProxy(new Ice.Identity(rs.getString("pk_subscription"),"manageSubscription")));

                return s;
            }
    };

    public static final RowMapper<UpdatedFrame> UPDATED_FRAME_MAPPER =
        new RowMapper<UpdatedFrame>() {
            public UpdatedFrame mapRow(ResultSet rs, int rowNum) throws SQLException {
                UpdatedFrame frame  = new UpdatedFrame();
                frame.id = rs.getString("pk_frame");
                frame.exitStatus = rs.getInt("int_exit_status");
                frame.maxRss = rs.getInt("int_mem_max_used");
                frame.retryCount = rs.getInt("int_retries");
                frame.state = FrameState.valueOf(rs.getString("str_state"));
                frame.usedMemory = rs.getInt("int_mem_used");

                if (rs.getString("str_host") != null) {
                    frame.lastResource = String.format("%s/%2.2f",rs.getString("str_host"),
                            Convert.coreUnitsToCores(rs.getInt("int_cores")));
                }else {
                    frame.lastResource = "";
                }

                java.sql.Timestamp ts_started = rs.getTimestamp("ts_started");
                if (ts_started != null) {
                    frame.startTime = (int) (rs.getTimestamp("ts_started").getTime() / 1000);
                }
                else {
                    frame.startTime = 0;
                }
                java.sql.Timestamp ts_stopped = rs.getTimestamp("ts_stopped");
                if (ts_stopped!= null) {
                    frame.stopTime = (int) (ts_stopped.getTime() / 1000);
                }
                else {
                    frame.stopTime = 0;
                }

                return frame;
            }
    };

    public static final RowMapper<Frame> FRAME_MAPPER =
        new RowMapper<Frame>() {
            public Frame mapRow(ResultSet rs, int rowNum) throws SQLException {
                Frame frame  = new Frame();
                frame.data = new FrameData();
                frame.data.name = rs.getString("str_name");
                frame.data.exitStatus = rs.getInt("int_exit_status");
                frame.data.maxRss = rs.getLong("int_mem_max_used");
                frame.data.number = rs.getInt("int_number");
                frame.data.dispatchOrder = rs.getInt("int_dispatch_order");
                frame.data.retryCount = rs.getInt("int_retries");
                frame.data.state = FrameState.valueOf(rs.getString("str_state"));
                frame.data.layerName = rs.getString("layer_name");
                frame.data.usedMemory = rs.getLong("int_mem_used");
                frame.data.reservedMemory = rs.getLong("int_mem_reserved");
                frame.data.reservedGpu = rs.getLong("int_gpu_reserved");
                frame.data.checkpointState = CheckpointState.valueOf(
                        rs.getString("str_checkpoint_state"));
                frame.data.checkpointCount = rs.getInt("int_checkpoint_count");

                if (rs.getString("str_host") != null) {
                    frame.data.lastResource = CueUtil.buildProcName(rs.getString("str_host"),
                            rs.getInt("int_cores"));
                } else {
                    frame.data.lastResource = "";
                }

                frame.proxy = FrameInterfacePrxHelper.uncheckedCast(iceServer.getAdapter()
                        .createProxy(new Ice.Identity(rs.getString("pk_frame"),"manageFrame")));

                java.sql.Timestamp ts_started = rs.getTimestamp("ts_started");
                if (ts_started != null) {
                    frame.data.startTime = (int) (rs.getTimestamp("ts_started").getTime() / 1000);
                }
                else {
                    frame.data.startTime = 0;
                }
                java.sql.Timestamp ts_stopped = rs.getTimestamp("ts_stopped");
                if (ts_stopped!= null) {
                    frame.data.stopTime = (int) (ts_stopped.getTime() / 1000);
                }
                else {
                    frame.data.stopTime = 0;
                }

                frame.data.totalCoreTime = rs.getInt("int_total_past_core_time");
                if (frame.data.state == FrameState.Running) {
                    frame.data.totalCoreTime = frame.data.totalCoreTime +
                        (int)(System.currentTimeMillis() / 1000 - frame.data.startTime) * rs.getInt("int_cores") / 100;
                }
                return frame;
            }
    };

    private static final RowMapper<Service> SERVICE_MAPPER =
        new RowMapper<Service>() {
            public Service mapRow(ResultSet rs, int rowNum) throws SQLException {
                Service service = new Service();
                service.data = new ServiceData();
                service.data.name = rs.getString("str_name");
                service.data.threadable = rs.getBoolean("b_threadable");
                service.data.minCores = rs.getInt("int_cores_min");
                service.data.maxCores = rs.getInt("int_cores_max");
                service.data.minMemory = rs.getInt("int_mem_min");
                service.data.minGpu = rs.getInt("int_gpu_min");
                service.data.tags = Lists.newArrayList(ServiceDaoJdbc.splitTags(
                        rs.getString("str_tags")));
                service.proxy = ServiceInterfacePrxHelper.uncheckedCast(iceServer.getAdapter()
                        .createProxy(new Ice.Identity(rs.getString("pk_service"),"manageService")));
                return service;
            }
    };

    private static final RowMapper<ServiceOverride> SERVICE_OVERRIDE_MAPPER =
        new RowMapper<ServiceOverride>() {
            public ServiceOverride mapRow(ResultSet rs, int rowNum) throws SQLException {
                ServiceOverride service = new ServiceOverride();
                service.data = new ServiceData();
                service.data.name = rs.getString("str_name");
                service.data.threadable = rs.getBoolean("b_threadable");
                service.data.minCores = rs.getInt("int_cores_min");
                service.data.maxCores = rs.getInt("int_cores_max");
                service.data.minMemory = rs.getInt("int_mem_min");
                service.data.minGpu = rs.getInt("int_gpu_min");
                service.data.tags = Lists.newArrayList(ServiceDaoJdbc.splitTags(
                        rs.getString("str_tags")));
                service.proxy = ServiceOverrideInterfacePrxHelper.uncheckedCast(iceServer.getAdapter()
                        .createProxy(new Ice.Identity(rs.getString("pk_show_service"),
                                "manageServiceOverride")));
                return service;
            }
    };

    public static final RowMapper<Show> SHOW_MAPPER =
        new RowMapper<Show>() {
            public Show mapRow(ResultSet rs, int rowNum) throws SQLException {
                Show s = new Show();
                s.data = new ShowData();
                s.stats = new ShowStats();

                s.data.name = rs.getString("str_name");
                s.data.active = rs.getBoolean("b_active");
                s.data.defaultMaxCores = Convert.coreUnitsToCores(rs.getInt("int_default_max_cores"));
                s.data.defaultMinCores = Convert.coreUnitsToCores(rs.getInt("int_default_min_cores"));
                s.data.bookingEnabled = rs.getBoolean("b_booking_enabled");
                s.data.dispatchEnabled = rs.getBoolean("b_dispatch_enabled");
                s.data.commentEmail = rs.getString("str_comment_email");

                s.stats.pendingFrames = rs.getInt("int_pending_count");
                s.stats.runningFrames = rs.getInt("int_running_count");
                s.stats.deadFrames = rs.getInt("int_dead_count");
                s.stats.createdFrameCount = rs.getLong("int_frame_insert_count");
                s.stats.createdJobCount = rs.getLong("int_job_insert_count");
                s.stats.renderedFrameCount = rs.getLong("int_frame_success_count");
                s.stats.failedFrameCount = rs.getLong("int_frame_fail_count");
                s.stats.reservedCores = Convert.coreUnitsToCores(rs.getInt("int_cores"));
                s.stats.pendingJobs = rs.getInt("int_job_count");

                s.proxy = ShowInterfacePrxHelper.uncheckedCast(iceServer.getAdapter()
                        .createProxy(new Ice.Identity(rs.getString("pk_show"),"manageShow")));

                return s;
            }
    };
    /*
     * Queries
     */

    private static final String GET_JOB_NAMES =
        "SELECT " +
            "job.str_name "+
        "FROM " +
            "job," +
            "show " +
        "WHERE " +
            "job.pk_show = show.pk_show " +
        "AND " +
            "job.str_state = 'Pending' ";

    private static final String GET_HOST_COMMENTS =
        "SELECT " +
            "* " +
        "FROM " +
            "comments " +
        "WHERE " +
            "pk_host=? " +
        "ORDER BY " +
            "ts_created ASC";

    private static final String GET_FILTER =
        "SELECT " +
            "filter.* " +
        "FROM " +
            "filter," +
            "show " +
        "WHERE " +
            "filter.pk_show = show.pk_show";

    private static final String GET_FRAME =
        "SELECT " +
            "frame.pk_frame, " +
            "frame.int_exit_status,"+
            "frame.str_name,"+
            "frame.int_number,"+
            "frame.int_dispatch_order,"+
            "frame.ts_started,"+
            "frame.ts_stopped,"+
            "frame.int_retries,"+
            "frame.str_state,"+
            "frame.str_host,"+
            "frame.int_cores,"+
            "frame.int_mem_max_used," +
            "frame.int_mem_used, " +
            "frame.int_mem_reserved, " +
            "frame.int_gpu_reserved, " +
            "frame.str_checkpoint_state,"+
            "frame.int_checkpoint_count,"+
            "frame.int_total_past_core_time,"+
            "layer.str_name AS layer_name," +
            "job.str_name AS job_name "+
        "FROM "+
             "job, " +
             "layer, "+
             "frame " +
        "WHERE " +
            "frame.pk_layer = layer.pk_layer "+
        "AND "+
            "frame.pk_job= job.pk_job";

    private static final String FIND_FRAME = GET_FRAME + " " +
        "AND " +
            "job.str_state='Pending' " +
        "AND " +
            "job.str_name=? " +
        "AND " +
            "layer.str_name=? " +
        "AND " +
            "frame.int_number=?";

    private static final String GET_PROC =
        "SELECT " +
            "host.str_name AS host_name, " +
            "job.str_name AS job_name, " +
            "job.str_log_dir, " +
            "folder.str_name as folder_name, " +
            "show.str_name AS show_name, " +
            "frame.str_name AS frame_name, " +
            "layer.str_services, " +
            "proc.pk_proc, " +
            "proc.pk_host, " +
            "proc.int_cores_reserved, " +
            "proc.int_mem_reserved, " +
            "proc.int_mem_used, " +
            "proc.int_mem_max_used, " +
            "proc.int_gpu_reserved, " +
            "proc.ts_ping, " +
            "proc.ts_booked, " +
            "proc.ts_dispatched, " +
            "proc.b_unbooked, " +
            "redirect.str_name AS str_redirect " +
        "FROM proc " +
        "JOIN host ON proc.pk_host = host.pk_host " +
        "JOIN alloc ON host.pk_alloc = alloc.pk_alloc " +
        "JOIN frame ON proc.pk_frame = frame.pk_frame " +
        "JOIN layer ON proc.pk_layer = layer.pk_layer " +
        "JOIN job ON proc.pk_job = job.pk_job " +
        "JOIN folder ON job.pk_folder = folder.pk_folder " +
        "JOIN show ON proc.pk_show = show.pk_show " +
        "LEFT JOIN redirect ON proc.pk_proc = redirect.pk_proc";

    private static final String GET_JOB_COMMENTS =
        "SELECT " +
            "* " +
        "FROM " +
            "comments " +
        "WHERE " +
            "pk_job=? " +
        "ORDER BY " +
            "ts_created ASC";

    private static final String GET_UPDATED_FRAME =
        "SELECT " +
            "frame.pk_frame, " +
            "frame.int_exit_status,"+
            "frame.ts_started,"+
            "frame.ts_stopped,"+
            "frame.int_retries,"+
            "frame.str_state,"+
            "frame.str_host,"+
            "frame.int_cores,"+
            "COALESCE(proc.int_mem_max_used, frame.int_mem_max_used) AS int_mem_max_used," +
            "COALESCE(proc.int_mem_used, frame.int_mem_used) AS int_mem_used " +
        "FROM "+
             "job, " +
             "layer,"+
             "frame LEFT JOIN proc ON (proc.pk_frame = frame.pk_frame) " +
        "WHERE " +
            "frame.pk_layer = layer.pk_layer "+
        "AND "+
            "frame.pk_job= job.pk_job";

    private static final String GET_ALLOCATION =
        "SELECT " +
            "alloc.pk_alloc, " +
            "alloc.str_name, " +
            "alloc.str_tag, " +
            "alloc.b_billable,"+
            "facility.str_name AS facility_name,"+
            "vs_alloc_usage.int_cores,"+
            "vs_alloc_usage.int_idle_cores,"+
            "vs_alloc_usage.int_running_cores,"+
            "vs_alloc_usage.int_available_cores,"+
            "vs_alloc_usage.int_locked_cores,"+
            "vs_alloc_usage.int_hosts,"+
            "vs_alloc_usage.int_locked_hosts,"+
            "vs_alloc_usage.int_down_hosts "+
        "FROM " +
            "alloc, " +
            "facility, " +
            "vs_alloc_usage " +
        "WHERE " +
            "alloc.pk_alloc = vs_alloc_usage.pk_alloc " +
        "AND " +
            "alloc.pk_facility = facility.pk_facility " +
        "AND " +
            "alloc.b_enabled = true";


    private static final String GET_MATCHER =
        "SELECT " +
            "filter.pk_show," +
            "matcher.* " +
        "FROM " +
            "filter,"+
            "matcher " +
        "WHERE " +
            "filter.pk_filter = matcher.pk_filter";

    private static final String GET_DEPARTMENT =
        "SELECT " +
            "dept.str_name AS str_dept," +
            "show.str_name || '.' || dept.str_name AS str_name, " +
            "pk_point,"+
            "str_ti_task,"+
            "int_cores,"+
            "int_min_cores,"+
            "b_managed " +
        "FROM " +
            "point," +
            "dept,"+
            "show " +
        "WHERE " +
            "point.pk_show = show.pk_show " +
        "AND " +
            "point.pk_dept = dept.pk_dept " +
        "AND " +
            "point.pk_show = ? " +
        "AND " +
            "dept.str_name = ?";

    private static final String GET_DEPARTMENTS =
        "SELECT " +
            "dept.str_name AS str_dept," +
            "show.str_name || '.' || dept.str_name AS str_name, " +
            "pk_point,"+
            "str_ti_task,"+
            "int_cores,"+
            "int_min_cores,"+
            "b_managed " +
        "FROM " +
            "point," +
            "dept,"+
            "show " +
        "WHERE " +
            "point.pk_show = show.pk_show " +
        "AND " +
            "point.pk_dept = dept.pk_dept " +
        "AND " +
            "point.pk_show = ? ";

    private static final String QUERY_FOR_OWNER =
        "SELECT " +
            "owner.pk_owner," +
            "owner.str_username,"+
            "show.str_name AS str_show, " +
            "(SELECT COUNT(1) FROM deed WHERE deed.pk_owner = owner.pk_owner) " +
                " AS host_count " +
        "FROM " +
            "owner, " +
            "show " +
        "WHERE " +
            "owner.pk_show = show.pk_show";

    private static final String QUERY_FOR_RENDER_PART =
        "SELECT " +
            "host_local.pk_host_local,"+
            "host_local.int_cores_idle,"+
            "host_local.int_cores_max,"+
            "host_local.int_threads,"+
            "host_local.int_mem_idle,"+
            "host_local.int_mem_max,"+
            "host_local.int_gpu_idle,"+
            "host_local.int_gpu_max,"+
            "host_local.str_type,"+
            "(SELECT str_name FROM host WHERE host.pk_host = host_local.pk_host) " +
                "AS str_host_name,"+
            "(SELECT str_name FROM job WHERE job.pk_job = host_local.pk_job) " +
                "AS str_job_name,"+
            "(SELECT str_name FROM layer WHERE layer.pk_layer = host_local.pk_layer) " +
                "AS str_layer_name,"+
            "(SELECT str_name FROM frame WHERE frame.pk_frame = host_local.pk_frame) " +
                "AS str_frame_name " +
        "FROM " +
            "host_local ";

    private static final String QUERY_FOR_FACILITY =
        "SELECT " +
            "facility.pk_facility," +
            "facility.str_name " +
        "FROM " +
            "facility ";

    public static final String GET_GROUPS =
        "SELECT " +
            "show.pk_show, " +
            "show.str_name AS str_show," +
            "dept.str_name AS str_dept," +
            "folder.pk_folder," +
            "folder.pk_parent_folder," +
            "folder.str_name AS group_name," +
            "folder.int_job_priority,"+
            "folder.int_job_min_cores," +
            "folder.int_job_max_cores," +
            "folder_resource.int_min_cores,"+
            "folder_resource.int_max_cores,"+
            "folder.b_default, " +
            "folder_level.int_level, " +
            "c.int_waiting_count, " +
            "c.int_depend_count, " +
            "c.int_running_count,"+
            "c.int_dead_count,"+
            "c.int_job_count,"+
            "c.int_cores " +
        "FROM " +
            "folder, " +
            "folder_level," +
            "folder_resource, "+
            "vs_folder_counts c, " +
            "show," +
            "dept " +
        "WHERE " +
            "show.pk_show = folder.pk_show "+
         "AND " +
             "folder.pk_folder = folder_level.pk_folder " +
         "AND " +
             "folder.pk_folder = folder_resource.pk_folder " +
         "AND " +
             "folder.pk_folder = c.pk_folder " +
         "AND " +
             "folder.pk_dept = dept.pk_dept ";

    private static final String GET_ACTION =
        "SELECT " +
            "filter.pk_show," +
            "action.* " +
        "FROM " +
            "filter,"+
            "action " +
        "WHERE " +
            "filter.pk_filter = action.pk_filter ";

    private static final String GET_JOB =
        "SELECT " +
            "job.pk_job,"+
            "job.str_log_dir," +
            "job_resource.int_max_cores," +
            "job_resource.int_min_cores," +
            "job.str_name," +
            "job.str_shot,"+
            "job.str_state,"+
            "job.int_uid,"+
            "job.str_user,"+
            "job.b_paused,"+
            "job.ts_started,"+
            "job.ts_stopped,"+
            "job.b_comment,"+
            "job.b_autoeat,"+
            "job.str_os,"+
            "job_resource.int_priority,"+
            "job.int_frame_count, " +
            "job.int_layer_count, " +
            "show.str_name as str_show," +
            "show.pk_show as id_show,"+
            "facility.str_name AS facility_name,"+
            "folder.str_name AS group_name,"+
            "job_stat.int_waiting_count, "+
            "job_stat.int_running_count, "+
            "job_stat.int_dead_count, " +
            "job_stat.int_eaten_count," +
            "job_stat.int_depend_count, "+
            "job_stat.int_succeeded_count, "+
            "job_usage.int_core_time_success, "+
            "job_usage.int_core_time_fail, " +
            "job_usage.int_frame_success_count, "+
            "job_usage.int_frame_fail_count, "+
            "job_usage.int_clock_time_high,"+
            "job_usage.int_clock_time_success,"+
            "job_mem.int_max_rss,"+
            "(job_resource.int_cores + job_resource.int_local_cores) AS int_cores " +
        "FROM " +
            "job,"+
            "folder,"+
            "show," +
            "facility,"+
            "job_stat," +
            "job_resource, " +
            "job_mem, " +
            "job_usage " +
        "WHERE " +
            "job.pk_show = show.pk_show " +
        "AND " +
            "job.pk_folder = folder.pk_folder " +
        "AND " +
            "job.pk_facility = facility.pk_facility " +
        "AND " +
            "job.pk_job = job_stat.pk_job " +
        "AND " +
            "job.pk_job = job_resource.pk_job " +
        "AND " +
            "job.pk_job = job_mem.pk_job " +
        "AND " +
            "job.pk_job = job_usage.pk_job ";

    private static final String GET_LAYER =
        "SELECT " +
            "layer.*," +
            "layer_stat.int_total_count," +
            "layer_stat.int_waiting_count," +
            "layer_stat.int_running_count," +
            "layer_stat.int_dead_count," +
            "layer_stat.int_depend_count," +
            "layer_stat.int_eaten_count," +
            "layer_stat.int_succeeded_count," +
            "layer_usage.int_core_time_success," +
            "layer_usage.int_core_time_fail, "+
            "layer_usage.int_frame_success_count, "+
            "layer_usage.int_frame_fail_count, "+
            "layer_usage.int_clock_time_low, "+
            "layer_usage.int_clock_time_high," +
            "layer_usage.int_clock_time_success," +
            "layer_usage.int_clock_time_fail," +
            "layer_mem.int_max_rss,"+
            "layer_resource.int_cores " +
        "FROM " +
            "layer, " +
            "job," +
            "layer_stat, " +
            "layer_resource, " +
            "layer_usage, " +
            "layer_mem " +
        "WHERE " +
            "layer.pk_job = job.pk_job " +
        "AND " +
            "layer.pk_layer = layer_stat.pk_layer "+
        "AND " +
            "layer.pk_layer = layer_resource.pk_layer " +
        "AND " +
            "layer.pk_layer = layer_usage.pk_layer " +
        "AND " +
            "layer.pk_layer = layer_mem.pk_layer ";

    private static final String GET_SHOW =
        "SELECT " +
            "show.*," +
            "COALESCE(vs_show_stat.int_pending_count, 0) AS int_pending_count," +
            "COALESCE(vs_show_stat.int_running_count, 0) AS int_running_count," +
            "COALESCE(vs_show_stat.int_dead_count, 0) AS int_dead_count," +
            "COALESCE(vs_show_resource.int_cores, 0) AS int_cores, " +
            "COALESCE(vs_show_stat.int_job_count, 0) AS int_job_count " +
        "FROM " +
            "show " +
        "LEFT JOIN vs_show_stat ON (vs_show_stat.pk_show = show.pk_show) "+
        "LEFT JOIN vs_show_resource ON (vs_show_resource.pk_show=show.pk_show) " +
        "WHERE " +
            "1 = 1 ";

    private static final String GET_SERVICE =
        "SELECT " +
            "service.pk_service,"+
            "service.str_name," +
            "service.b_threadable," +
            "service.int_cores_min," +
            "service.int_cores_max," +
            "service.int_mem_min," +
            "service.int_gpu_min," +
            "service.str_tags " +
        "FROM "+
            "service ";

    private static final String GET_SERVICE_OVERRIDE =
        "SELECT " +
            "show_service.pk_show_service,"+
            "show_service.str_name," +
            "show_service.b_threadable," +
            "show_service.int_cores_min," +
            "show_service.int_cores_max," +
            "show_service.int_mem_min," +
            "show_service.int_gpu_min," +
            "show_service.str_tags " +
        "FROM "+
            "show_service, " +
            "show " +
        "WHERE " +
            "show_service.pk_show = show.pk_show ";

    private static final String GET_TASK =
        "SELECT " +
            "task.pk_task," +
            "task.str_shot,"+
            "task.int_min_cores + task.int_adjust_cores AS int_min_cores, "+
            "task.int_adjust_cores, " +
            "dept.str_name AS str_dept "+
        "FROM " +
            "task,"+
            "dept, " +
            "point "+
        "WHERE " +
            "task.pk_point = point.pk_point " +
        "AND " +
            "point.pk_dept = dept.pk_dept ";

    private static final String GET_HOST =
        "SELECT " +
            "host.pk_host, "+
            "host.str_name AS host_name," +
            "host_stat.str_state AS host_state,"+
            "host.b_nimby,"+
            "host_stat.ts_booted,"+
            "host_stat.ts_ping,"+
            "host.int_cores,"+
            "host.int_cores_idle,"+
            "host.int_mem,"+
            "host.int_mem_idle,"+
            "host.int_gpu,"+
            "host.int_gpu_idle,"+
            "host.str_tags,"+
            "host.str_lock_state,"+
            "host.b_comment,"+
            "host.int_thread_mode,"+
            "host_stat.str_os,"+
            "host_stat.int_mem_total,"+
            "host_stat.int_mem_free,"+
            "host_stat.int_swap_total,"+
            "host_stat.int_swap_free,"+
            "host_stat.int_mcp_total,"+
            "host_stat.int_mcp_free,"+
            "host_stat.int_gpu_total,"+
            "host_stat.int_gpu_free,"+
            "host_stat.int_load, " +
            "alloc.str_name AS alloc_name " +
        "FROM " +
            "alloc," +
            "facility, "+
            "host_stat,"+
            "host "+
        "WHERE " +
            "host.pk_alloc = alloc.pk_alloc " +
        "AND " +
            "facility.pk_facility = alloc.pk_facility " +
        "AND "+
            "host.pk_host = host_stat.pk_host ";

    private static final String GET_DEPEND =
        "SELECT " +
            "depend.pk_depend, "+
            "depend.str_type, "+
            "depend.b_active, "+
            "depend.b_any, "+
            "depend.str_target, "+
            "(SELECT str_name FROM job j WHERE j.pk_job = depend.pk_job_depend_on) AS depend_on_job, "+
            "(SELECT str_name FROM job j WHERE j.pk_job = depend.pk_job_depend_er) AS depend_er_job, "+
            "(SELECT str_name FROM layer l WHERE l.pk_layer = depend.pk_layer_depend_on) AS depend_on_layer, "+
            "(SELECT str_name FROM layer l WHERE l.pk_layer = depend.pk_layer_depend_er) AS depend_er_layer, "+
            "(SELECT str_name FROM frame f WHERE f.pk_frame = depend.pk_frame_depend_on) AS depend_on_frame, "+
            "(SELECT str_name FROM frame f WHERE f.pk_frame = depend.pk_frame_depend_er) AS depend_er_frame "+
      "FROM " +
          "depend ";

    private static final String GET_SUBSCRIPTION =
        "SELECT " +
            "subscription.pk_subscription, " +
            "(alloc.str_name || '.' || show.str_name) AS name, "+
            "subscription.int_burst, " +
            "subscription.int_size, " +
            "subscription.int_cores, " +
            "show.str_name AS show_name, " +
            "alloc.str_name AS alloc_name, " +
            "facility.str_name AS facility_name " +
        "FROM "+
            "show, " +
            "alloc, " +
            "facility,"+
            "subscription " +
        "WHERE " +
            "subscription.pk_show = show.pk_show " +
        "AND " +
            "subscription.pk_alloc = alloc.pk_alloc " +
        "AND " +
            "alloc.pk_facility = facility.pk_facility ";

    private static final String GET_PENDING_JOBS =
        GET_JOB +
        "AND " +
            "job.str_state = 'Pending' ";

    private static final String GET_FRAMES_CRITERIA =

        "SELECT " +
            "frame.pk_frame, " +
            "frame.int_exit_status,"+
            "frame.str_name,"+
            "frame.int_number,"+
            "frame.int_dispatch_order,"+
            "frame.ts_started,"+
            "frame.ts_stopped,"+
            "frame.int_retries,"+
            "frame.str_state,"+
            "frame.str_host,"+
            "frame.int_cores,"+
            "frame.int_mem_max_used," +
            "frame.int_mem_used, " +
            "frame.int_mem_reserved, " +
            "frame.int_gpu_reserved, " +
            "frame.str_checkpoint_state,"+
            "frame.int_checkpoint_count,"+
            "frame.int_total_past_core_time,"+
            "layer.str_name AS layer_name," +
            "job.str_name AS job_name, "+
            "ROW_NUMBER() OVER " +
                "(ORDER BY frame.int_dispatch_order ASC, layer.int_dispatch_order ASC) AS row_number " +
        "FROM "+
             "job, " +
             "layer,"+
             "frame " +
        "WHERE " +
            "frame.pk_layer = layer.pk_layer "+
        "AND "+
            "frame.pk_job= job.pk_job ";

    private static final String QUERY_FOR_DEED =
        "SELECT " +
            "host.str_name AS str_host,"+
            "show.str_name AS str_show,"+
            "owner.str_username," +
            "deed.b_blackout,"+
            "deed.int_blackout_start,"+
            "deed.int_blackout_stop,"+
            "deed.pk_deed " +
        "FROM " +
            "deed,"+
            "owner,"+
            "host,"+
            "show "+
        "WHERE " +
            "deed.pk_host = host.pk_host " +
        "AND " +
            "deed.pk_owner = owner.pk_owner " +
        "AND " +
            "owner.pk_show = show.pk_show ";
}

