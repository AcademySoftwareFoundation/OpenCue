
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
import java.sql.Timestamp;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;

import com.google.common.collect.Lists;
import com.google.common.collect.Sets;
import com.imageworks.spcue.dao.AbstractJdbcDao;
import org.apache.log4j.Logger;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.ActionInterface;
import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.DeedEntity;
import com.imageworks.spcue.DependInterface;
import com.imageworks.spcue.FilterInterface;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.MatcherInterface;
import com.imageworks.spcue.OwnerEntity;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.dao.WhiteboardDao;
import com.imageworks.spcue.dao.criteria.FrameSearchInterface;
import com.imageworks.spcue.dao.criteria.FrameSearchFactory;
import com.imageworks.spcue.dao.criteria.HostSearchInterface;
import com.imageworks.spcue.dao.criteria.JobSearchInterface;
import com.imageworks.spcue.dao.criteria.ProcSearchInterface;
import com.imageworks.spcue.dao.criteria.ProcSearchFactory;
import com.imageworks.spcue.grpc.comment.Comment;
import com.imageworks.spcue.grpc.comment.CommentSeq;
import com.imageworks.spcue.grpc.depend.Depend;
import com.imageworks.spcue.grpc.depend.DependSeq;
import com.imageworks.spcue.grpc.depend.DependTarget;
import com.imageworks.spcue.grpc.depend.DependType;
import com.imageworks.spcue.grpc.facility.Allocation;
import com.imageworks.spcue.grpc.facility.AllocationSeq;
import com.imageworks.spcue.grpc.facility.AllocationStats;
import com.imageworks.spcue.grpc.facility.Facility;
import com.imageworks.spcue.grpc.facility.FacilitySeq;
import com.imageworks.spcue.grpc.filter.Action;
import com.imageworks.spcue.grpc.filter.ActionSeq;
import com.imageworks.spcue.grpc.filter.ActionType;
import com.imageworks.spcue.grpc.filter.ActionValueType;
import com.imageworks.spcue.grpc.filter.Filter;
import com.imageworks.spcue.grpc.filter.FilterSeq;
import com.imageworks.spcue.grpc.filter.FilterType;
import com.imageworks.spcue.grpc.filter.MatchSubject;
import com.imageworks.spcue.grpc.filter.MatchType;
import com.imageworks.spcue.grpc.filter.Matcher;
import com.imageworks.spcue.grpc.filter.MatcherSeq;
import com.imageworks.spcue.grpc.host.Deed;
import com.imageworks.spcue.grpc.host.DeedSeq;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.host.Host;
import com.imageworks.spcue.grpc.host.HostSeq;
import com.imageworks.spcue.grpc.host.LockState;
import com.imageworks.spcue.grpc.host.NestedHost;
import com.imageworks.spcue.grpc.host.Owner;
import com.imageworks.spcue.grpc.host.Proc;
import com.imageworks.spcue.grpc.host.ProcSeq;
import com.imageworks.spcue.grpc.host.ThreadMode;
import com.imageworks.spcue.grpc.job.CheckpointState;
import com.imageworks.spcue.grpc.job.Frame;
import com.imageworks.spcue.grpc.job.FrameSeq;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.job.Group;
import com.imageworks.spcue.grpc.job.GroupSeq;
import com.imageworks.spcue.grpc.job.GroupStats;
import com.imageworks.spcue.grpc.job.Job;
import com.imageworks.spcue.grpc.job.JobSeq;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.grpc.job.JobStats;
import com.imageworks.spcue.grpc.job.Layer;
import com.imageworks.spcue.grpc.job.LayerSeq;
import com.imageworks.spcue.grpc.job.LayerStats;
import com.imageworks.spcue.grpc.job.LayerType;
import com.imageworks.spcue.grpc.job.UpdatedFrame;
import com.imageworks.spcue.grpc.job.UpdatedFrameCheckResult;
import com.imageworks.spcue.grpc.job.UpdatedFrameSeq;
import com.imageworks.spcue.grpc.renderpartition.RenderPartition;
import com.imageworks.spcue.grpc.renderpartition.RenderPartitionSeq;
import com.imageworks.spcue.grpc.renderpartition.RenderPartitionType;
import com.imageworks.spcue.grpc.service.Service;
import com.imageworks.spcue.grpc.service.ServiceOverride;
import com.imageworks.spcue.grpc.service.ServiceOverrideSeq;
import com.imageworks.spcue.grpc.service.ServiceSeq;
import com.imageworks.spcue.grpc.show.Show;
import com.imageworks.spcue.grpc.show.ShowSeq;
import com.imageworks.spcue.grpc.show.ShowStats;
import com.imageworks.spcue.grpc.subscription.Subscription;
import com.imageworks.spcue.grpc.subscription.SubscriptionSeq;
import com.imageworks.spcue.util.Convert;
import com.imageworks.spcue.util.CueUtil;
import com.imageworks.spcue.util.SqlUtil;
import org.springframework.stereotype.Repository;

@Repository
public class WhiteboardDaoJdbc extends AbstractJdbcDao implements WhiteboardDao {
    @SuppressWarnings("unused")
    private static final Logger logger = Logger.getLogger(WhiteboardDaoJdbc.class);

    private FrameSearchFactory frameSearchFactory;
    private ProcSearchFactory procSearchFactory;

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
    public ServiceSeq getDefaultServices() {
        List<Service> services = getJdbcTemplate().query(GET_SERVICE, SERVICE_MAPPER);
        return ServiceSeq.newBuilder().addAllServices(services).build();
    }

    @Override
    public ServiceOverrideSeq getServiceOverrides(ShowInterface show) {
        return ServiceOverrideSeq.newBuilder().addAllServiceOverrides(getJdbcTemplate().query(
                GET_SERVICE_OVERRIDE + " AND show_service.pk_show = ?",
                SERVICE_OVERRIDE_MAPPER, show.getId())).build();
    }

    @Override
    public ServiceOverride getServiceOverride(ShowInterface show, String name) {
        return getJdbcTemplate().queryForObject (
                GET_SERVICE_OVERRIDE +
                " AND show_service.pk_show=? AND (show_service.str_name=? OR" +
                " show_service.pk_show_service=?)",
                SERVICE_OVERRIDE_MAPPER, show.getId(), name, name);
    }

    @Override
    public Filter getFilter(FilterInterface filter) {
        return getJdbcTemplate().queryForObject(GET_FILTER + " AND pk_filter=?",
                FILTER_MAPPER, filter.getFilterId());
    }

    @Override
    public Filter findFilter(ShowInterface show, String name) {
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
    public FilterSeq getFilters(ShowInterface show) {
        return FilterSeq.newBuilder().addAllFilters(getJdbcTemplate().query(
                GET_FILTER + " AND show.pk_show=? ORDER BY f_order ASC",
                FILTER_MAPPER, show.getShowId())).build();
    }

    @Override
    public ActionSeq getActions(FilterInterface filter) {
        return ActionSeq.newBuilder().addAllActions(getJdbcTemplate().query(
                GET_ACTION + " AND filter.pk_filter=? ORDER BY b_stop ASC, ts_created ASC ",
                ACTION_MAPPER, filter.getFilterId())).build();
    }

    @Override
    public MatcherSeq getMatchers(FilterInterface filter) {
        return MatcherSeq.newBuilder().addAllMatchers(getJdbcTemplate().query(
                GET_MATCHER + " AND filter.pk_filter=? ORDER BY ts_created ASC",
                MATCHER_MAPPER, filter.getFilterId())).build();
    }

    @Override
    public Action getAction(ActionInterface action) {
        return getJdbcTemplate().queryForObject(
                GET_ACTION + " AND action.pk_action=?",
                ACTION_MAPPER, action.getActionId());
    }

    @Override
    public Matcher getMatcher(MatcherInterface matcher) {
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
    public ShowSeq getShows() {
        List<Show> shows = getJdbcTemplate().query(GET_SHOW, SHOW_MAPPER);
        return ShowSeq.newBuilder().addAllShows(shows).build();
    }

    @Override
    public ShowSeq getActiveShows() {
        List<Show> shows = getJdbcTemplate().query(GET_SHOW + " AND b_active=?",
                SHOW_MAPPER, true);
        return ShowSeq.newBuilder().addAllShows(shows).build();
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
    public SubscriptionSeq getSubscriptions(ShowInterface show) {
        List<Subscription> subscriptions = getJdbcTemplate().query(
                GET_SUBSCRIPTION + " AND show.pk_show=?",
                SUBSCRIPTION_MAPPER, show.getShowId());
        return SubscriptionSeq.newBuilder().addAllSubscriptions(subscriptions).build();
    }

    @Override
    public SubscriptionSeq getSubscriptions(AllocationInterface alloc) {
        List<Subscription> subscriptions = getJdbcTemplate().query(
                GET_SUBSCRIPTION + " AND subscription.pk_alloc=?",
                SUBSCRIPTION_MAPPER, alloc.getAllocationId());
        return SubscriptionSeq.newBuilder().addAllSubscriptions(subscriptions).build();
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
    public AllocationSeq getAllocations() {
        return AllocationSeq.newBuilder().addAllAllocations(getJdbcTemplate().query(
                GET_ALLOCATION + " ORDER BY alloc.str_name ",
                ALLOCATION_MAPPER)).build();
    }

    @Override
    public AllocationSeq getAllocations(
            com.imageworks.spcue.FacilityInterface facility) {
        return AllocationSeq.newBuilder().addAllAllocations(getJdbcTemplate().query(
                GET_ALLOCATION + " AND alloc.pk_facility = ?",
                ALLOCATION_MAPPER, facility.getFacilityId())).build();
    }

    @Override
    public JobSeq getJobs(GroupInterface group) {
        List<Job> jobs = getJdbcTemplate().query(
                GET_PENDING_JOBS + " AND job.pk_folder=? ORDER BY job.str_name ASC",
                JOB_MAPPER, group.getId());
        return JobSeq.newBuilder().addAllJobs(jobs).build();
    }

    @Override
    public List<String> getJobNames(JobSearchInterface r) {
        return getJdbcTemplate().query(r.getFilteredQuery(GET_JOB_NAMES),
                new RowMapper<String>() {
            public String mapRow(ResultSet rs, int rowNum) throws SQLException {
                return rs.getString(1);
            }
        }, r.getValuesArray());
    }

    @Override
    public JobSeq getJobs(JobSearchInterface r) {
        List<Job> jobs = getJdbcTemplate().query(
                r.getFilteredQuery(GET_JOB) + "ORDER BY job.str_name ASC", JOB_MAPPER, r.getValuesArray());
        return JobSeq.newBuilder().addAllJobs(jobs).build();
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
                GET_LAYER + " AND job.str_state='PENDING' AND job.str_name=? AND layer.str_name=?",
                LAYER_MAPPER, job, layer);
    }

    @Override
    public LayerSeq getLayers(JobInterface job) {
        String query = GET_LAYER + " AND layer.pk_job=? ORDER BY layer.int_dispatch_order ASC";
        List<Layer> layers = getJdbcTemplate().query(
                query, LAYER_MAPPER, job.getJobId());
        return LayerSeq.newBuilder().addAllLayers(layers).build();
    }

    @Override
    public GroupSeq getGroups(ShowInterface show) {
       List<Group> groups = getJdbcTemplate().query(
                GET_GROUPS + " AND folder.pk_show=? ORDER BY folder_level.int_level ASC, folder.str_name ASC ",
                GROUP_MAPPER, show.getShowId());
       return GroupSeq.newBuilder().addAllGroups(groups).build();
    }

    @Override
    public GroupSeq getGroups(GroupInterface group) {
        List<Group> groups = getJdbcTemplate().query(
                 GET_GROUPS + " AND folder.pk_parent_folder=? ORDER BY folder_level.int_level ASC, folder.f_order DESC, folder.str_name ASC ",
                 GROUP_MAPPER, group.getGroupId());
        return GroupSeq.newBuilder().addAllGroups(groups).build();
    }

    @Override
    public Group getGroup(String id) {
        return getJdbcTemplate().queryForObject(
                GET_GROUPS + " AND folder.pk_folder=?",
                GROUP_MAPPER, id);
    }

    @Override
    public Group getRootGroup(ShowInterface show) {
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
    public FrameSeq getFrames(FrameSearchInterface r) {
        List<Frame> frames = getJdbcTemplate().query(
                r.getSortedQuery(GET_FRAMES_CRITERIA), FRAME_MAPPER, r.getValuesArray());
        return FrameSeq.newBuilder().addAllFrames(frames).build();
    }

    @Override
    public Depend getDepend(DependInterface depend) {
        return getJdbcTemplate().queryForObject(
                GET_DEPEND + " WHERE pk_depend=?",DEPEND_MAPPER, depend.getId());
    }

    @Override
    public Depend getDepend(com.imageworks.spcue.depend.AbstractDepend depend) {
        return getJdbcTemplate().queryForObject(
                GET_DEPEND + " WHERE pk_depend=?",DEPEND_MAPPER, depend.getId());
    }

    @Override
    public DependSeq getWhatDependsOnThis(JobInterface job) {
        List<Depend> depends = getJdbcTemplate().query(
                GET_DEPEND + " WHERE pk_parent IS NULL AND pk_job_depend_on=?",
                DEPEND_MAPPER, job.getJobId());
        return DependSeq.newBuilder().addAllDepends(depends).build();
    }

    @Override
    public DependSeq getWhatDependsOnThis(LayerInterface layer) {
        List<Depend> depends = getJdbcTemplate().query(
                GET_DEPEND + " WHERE pk_parent IS NULL AND pk_layer_depend_on=?",
                DEPEND_MAPPER, layer.getLayerId());
        return DependSeq.newBuilder().addAllDepends(depends).build();

    }

    @Override
    public DependSeq getWhatDependsOnThis(FrameInterface frame) {
        List<Depend> depends = getJdbcTemplate().query(
                GET_DEPEND + " WHERE pk_frame_depend_on=?",
                DEPEND_MAPPER, frame.getFrameId());
        return DependSeq.newBuilder().addAllDepends(depends).build();
    }

    @Override
    public DependSeq getWhatThisDependsOn(JobInterface job) {
        List<Depend> depends = getJdbcTemplate().query(
                GET_DEPEND + " WHERE pk_parent IS NULL AND pk_layer_depend_er IS NULL AND " +
                        "pk_frame_depend_er IS NULL AND pk_job_depend_er=?",
                DEPEND_MAPPER, job.getJobId());
        return DependSeq.newBuilder().addAllDepends(depends).build();
    }

    @Override
    public DependSeq getWhatThisDependsOn(LayerInterface layer) {
        List<Depend> depends = getJdbcTemplate().query(
                GET_DEPEND + " WHERE pk_parent IS NULL AND pk_layer_depend_er=?",
                DEPEND_MAPPER, layer.getLayerId());
        return DependSeq.newBuilder().addAllDepends(depends).build();
    }

    @Override
    public DependSeq getWhatThisDependsOn(FrameInterface frame) {
        /*
         * This should show anything that is making the frame dependent.
         */
        List<Depend> depends = getJdbcTemplate().query(
                GET_DEPEND + " WHERE " +
                        "(pk_job_depend_er=? AND str_type IN ('JOB_ON_JOB','JOB_ON_LAYER','JOB_ON_FRAME')) OR " +
                        "(pk_layer_depend_er=? AND str_type IN ('LAYER_ON_JOB','LAYER_ON_LAYER','LAYER_ON_FRAME')) " +
                        "OR (pk_frame_depend_er=?)",
                DEPEND_MAPPER, frame.getJobId(), frame.getLayerId(), frame.getFrameId());
        return DependSeq.newBuilder().addAllDepends(depends).build();
    }

    @Override
    public DependSeq getDepends(JobInterface job) {
        List<Depend> depends = getJdbcTemplate().query(
                GET_DEPEND + " WHERE pk_job_depend_er=? AND str_type != 'FRAME_ON_FRAME'",
                DEPEND_MAPPER, job.getJobId());
        return DependSeq.newBuilder().addAllDepends(depends).build();
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
    public HostSeq getHosts(HostSearchInterface r) {
        List<Host> hosts =  getJdbcTemplate().query(
                r.getFilteredQuery(GET_HOST), HOST_MAPPER, r.getValuesArray());
        return HostSeq.newBuilder().addAllHosts(hosts).build();
    }

    @Override
    public Host getHost(String id) {
        return getJdbcTemplate().queryForObject(
                GET_HOST + " AND host.pk_host=?", HOST_MAPPER, id);
    }

    @Override
    public ProcSeq getProcs(HostInterface host) {
        ProcSearchInterface r = procSearchFactory.create();
        r.filterByHost(host);
        r.sortByHostName();
        r.sortByDispatchedTime();
        return ProcSeq.newBuilder().addAllProcs(getProcs(r).getProcsList()).build();
    }

    @Override
    public ProcSeq getProcs(ProcSearchInterface p) {
        p.sortByHostName();
        p.sortByDispatchedTime();
        List<Proc> procs = getJdbcTemplate().query(p.getFilteredQuery(GET_PROC),
                PROC_MAPPER, p.getValuesArray());
        return ProcSeq.newBuilder().addAllProcs(procs).build();
    }

    @Override
    public CommentSeq getComments(HostInterface h) {
        List<Comment> comments = getJdbcTemplate().query(
                GET_HOST_COMMENTS, COMMENT_MAPPER, h.getHostId());
        return CommentSeq.newBuilder().addAllComments(comments).build();
    }

    @Override
    public CommentSeq getComments(JobInterface j) {
        List<Comment> comments = getJdbcTemplate().query(
                GET_JOB_COMMENTS, COMMENT_MAPPER, j.getJobId());
        return CommentSeq.newBuilder().addAllComments(comments).build();
    }

    @Override
    public UpdatedFrameCheckResult getUpdatedFrames(JobInterface job,
            List<LayerInterface> layers, int epochSeconds) {

        if ((System.currentTimeMillis() / 1000) - epochSeconds > 60) {
            long timeDiff = System.currentTimeMillis() - epochSeconds;
            throw new IllegalArgumentException("the last update timestamp cannot be over " +
                    "a minute off the current time, difference was: " + timeDiff);
        }

        UpdatedFrameCheckResult.Builder resultBuilder = UpdatedFrameCheckResult.newBuilder();
        resultBuilder.setState(JobState.valueOf(getJdbcTemplate().queryForObject(
                "SELECT str_state FROM job WHERE pk_job=?", String.class, job.getJobId())));

        FrameSearchInterface r = frameSearchFactory.create(job);
        r.filterByLayers(layers);
        r.filterByChangeDate(epochSeconds);
        r.setMaxResults(100);

        List<UpdatedFrame> updatedFrameList = getJdbcTemplate().query(
                r.getFilteredQuery(GET_UPDATED_FRAME), UPDATED_FRAME_MAPPER, r.getValuesArray());
        resultBuilder.setUpdatedFrames(UpdatedFrameSeq.newBuilder().addAllUpdatedFrames(updatedFrameList).build());
        resultBuilder.setServerTime((int) (System.currentTimeMillis() / 1000) - 1);

        return resultBuilder.build();
    }

    @Override
    public DeedSeq getDeeds(OwnerEntity owner) {
        List<Deed> deeds = getJdbcTemplate().query(
                QUERY_FOR_DEED + " AND owner.pk_owner=?",
                DEED_MAPPER, owner.getId());
        return DeedSeq.newBuilder().addAllDeeds(deeds).build();
    }

    @Override
    public DeedSeq getDeeds(ShowInterface show) {
        List<Deed> deeds =  getJdbcTemplate().query(
                QUERY_FOR_DEED + " AND show.pk_show=?",
                DEED_MAPPER, show.getId());
        return DeedSeq.newBuilder().addAllDeeds(deeds).build();
    }

    @Override
    public Host getHost(DeedEntity deed) {
        return getJdbcTemplate().queryForObject(
                GET_HOST + " AND host.pk_host=?",
                HOST_MAPPER, deed.id);
    }

    @Override
    public Deed getDeed(HostInterface host) {
        return getJdbcTemplate().queryForObject(
                QUERY_FOR_DEED + " AND host.pk_host=?",
                DEED_MAPPER, host.getHostId());
    }

    @Override
    public HostSeq getHosts(OwnerEntity owner) {
        StringBuilder sb = new StringBuilder(4096);
        String query = GET_HOST;
        query = query.replace("FROM " , "FROM owner, deed,");
        sb.append(query);
        sb.append("AND deed.pk_host = host.pk_host ");
        sb.append("AND deed.pk_owner = owner.pk_owner ");
        sb.append("AND owner.pk_owner = ?");

        List<Host> hosts = getJdbcTemplate().query(
                sb.toString(), HOST_MAPPER, owner.getId());
        return HostSeq.newBuilder().addAllHosts(hosts).build();
    }

    @Override
    public Owner getOwner(DeedEntity deed) {
        return getJdbcTemplate().queryForObject(
                QUERY_FOR_OWNER + " AND " +
                "pk_owner = (SELECT deed.pk_owner FROM deed " +
                "WHERE pk_deed=?)", OWNER_MAPPER, deed.getId());
    }

    @Override
    public Owner getOwner(HostInterface host) {
        return getJdbcTemplate().queryForObject(
                QUERY_FOR_OWNER + " AND " +
                "pk_owner = (SELECT deed.pk_owner FROM deed " +
                "WHERE pk_host=?)", OWNER_MAPPER, host.getHostId());
    }

    @Override
    public List<Owner> getOwners(ShowInterface show) {
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
    public RenderPartitionSeq getRenderPartitions(HostInterface host) {
        List<RenderPartition> partitions = getJdbcTemplate().query(QUERY_FOR_RENDER_PART +
                        "WHERE host_local.pk_host = ?",
                RENDER_PARTION_MAPPER, host.getHostId());
        return RenderPartitionSeq.newBuilder().addAllRenderPartitions(partitions).build();
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
    public FacilitySeq getFacilities() {
        return FacilitySeq.newBuilder().addAllFacilities(getJdbcTemplate().query(
                QUERY_FOR_FACILITY, FACILITY_MAPPER)).build();
    }

    /*
     * Row Mappers
     */

    public static final RowMapper<Matcher> MATCHER_MAPPER =
            new RowMapper<Matcher>() {
                public Matcher mapRow(ResultSet rs, int rowNum) throws SQLException {
                    return Matcher.newBuilder()
                            .setId(SqlUtil.getString(rs,"pk_matcher"))
                            .setInput(SqlUtil.getString(rs,"str_value"))
                            .setSubject(MatchSubject.valueOf(SqlUtil.getString(rs,"str_subject")))
                            .setType(MatchType.valueOf(SqlUtil.getString(rs,"str_match")))
                            .build();
                }
            };

    public static final RowMapper<Filter> FILTER_MAPPER =
            new RowMapper<Filter>() {
                public Filter mapRow(ResultSet rs, int rowNum) throws SQLException {
                    return Filter.newBuilder()
                            .setId(SqlUtil.getString(rs,"pk_filter"))
                            .setType(FilterType.valueOf(SqlUtil.getString(rs,"str_type")))
                            .setOrder(rs.getFloat("f_order"))
                            .setName(SqlUtil.getString(rs,"str_name"))
                            .setEnabled(rs.getBoolean("b_enabled"))
                            .build();
                }
            };

    public static final RowMapper<Action> ACTION_MAPPER =
            new RowMapper<Action>() {
                public Action mapRow(ResultSet rs, int rowNum) throws SQLException {
                    Action.Builder builder = Action.newBuilder()
                            .setId(SqlUtil.getString(rs,"pk_action"))
                            .setBooleanValue(false)
                            .setIntegerValue(0)
                            .setFloatValue(0f)
                            .setStringValue("")
                            .setType(ActionType.valueOf(SqlUtil.getString(rs,"str_action")))
                            .setValueType(ActionValueType.valueOf(SqlUtil.getString(rs,"str_value_type")));

                    switch (builder.getValueType()) {
                        case GROUP_TYPE:
                            builder.setGroupValue(SqlUtil.getString(rs,"pk_folder"));
                            break;
                        case STRING_TYPE:
                            builder.setStringValue(SqlUtil.getString(rs,"str_value"));
                            break;
                        case INTEGER_TYPE:
                            builder.setIntegerValue(rs.getInt("int_value"));
                            break;
                        case FLOAT_TYPE:
                            builder.setFloatValue(rs.getFloat("float_value"));
                            break;
                        case BOOLEAN_TYPE:
                            builder.setBooleanValue(rs.getBoolean("b_value"));
                            break;
                    }
                    return builder.build();
                }
            };

    public static final RowMapper<Facility> FACILITY_MAPPER =
        new RowMapper<Facility>() {
            public Facility mapRow(ResultSet rs, int rowNum) throws SQLException {
                return Facility.newBuilder()
                        .setName(rs.getString("str_name"))
                        .setId(rs.getString("pk_facility"))
                        .build();
            }
    };


    public static final RowMapper<Deed> DEED_MAPPER =
            new RowMapper<Deed>() {
                public Deed mapRow(ResultSet rs, int rowNum) throws SQLException {
                    return Deed.newBuilder()
                            .setId(SqlUtil.getString(rs,"pk_deed"))
                            .setHost(SqlUtil.getString(rs,"str_host"))
                            .setOwner(SqlUtil.getString(rs,"str_username"))
                            .setBlackout(rs.getBoolean("b_blackout"))
                            .setBlackoutStartTime(rs.getInt("int_blackout_start"))
                            .setBlackoutStopTime(rs.getInt("int_blackout_stop"))
                            .build();
                }
            };

    public static final RowMapper<RenderPartition>
            RENDER_PARTION_MAPPER = new RowMapper<RenderPartition>() {
        public RenderPartition mapRow(ResultSet rs, int rowNum) throws SQLException {

            RenderPartition.Builder builder = RenderPartition.newBuilder()
                    .setId(SqlUtil.getString(rs,"pk_host_local"))
                    .setCores(rs.getInt("int_cores_max") - rs.getInt("int_cores_idle"))
                    .setMaxCores(rs.getInt("int_cores_max"))
                    .setThreads(rs.getInt("int_threads"))
                    .setMaxMemory(rs.getLong("int_mem_max"))
                    .setMemory( rs.getLong("int_mem_max") - rs.getLong("int_mem_idle"))
                    .setMaxGpu(rs.getLong("int_gpu_max"))
                    .setHost(SqlUtil.getString(rs,"str_host_name"))
                    .setJob(SqlUtil.getString(rs,"str_job_name"))
                    .setRenderPartType(RenderPartitionType.valueOf(SqlUtil.getString(rs,"str_type")))
                    .setLayer("")
                    .setFrame("");

            if (SqlUtil.getString(rs,"str_layer_name") != null) {
                builder.setLayer(SqlUtil.getString(rs,"str_layer_name"));
            }

            if (SqlUtil.getString(rs,"str_frame_name") != null) {
                builder.setFrame(SqlUtil.getString(rs,"str_frame_name"));
            }

            return builder.build();

        }
    };

    public static final RowMapper<Owner>
            OWNER_MAPPER = new RowMapper<Owner>() {
        public Owner mapRow(ResultSet rs, int rowNum) throws SQLException {
            return Owner.newBuilder()
                    .setName(SqlUtil.getString(rs,"str_username"))
                    .setId(SqlUtil.getString(rs,"pk_owner"))
                    .setShow(SqlUtil.getString(rs,"str_show"))
                    .setHostCount(rs.getInt("host_count"))
                    .build();
        }
    };

    public static final RowMapper<Proc> PROC_MAPPER =
            new RowMapper<Proc>() {
                public Proc mapRow(ResultSet rs, int row) throws SQLException {
                    return Proc.newBuilder()
                            .setId(SqlUtil.getString(rs,"pk_proc"))
                            .setName(CueUtil.buildProcName(SqlUtil.getString(rs,"host_name"),
                                    rs.getInt("int_cores_reserved")))
                            .setReservedCores(Convert.coreUnitsToCores(rs.getInt("int_cores_reserved")))
                            .setReservedMemory(rs.getLong("int_mem_reserved"))
                            .setReservedGpu(rs.getLong("int_gpu_reserved"))
                            .setUsedMemory(rs.getLong("int_mem_used"))
                            .setFrameName(SqlUtil.getString(rs, "frame_name"))
                            .setJobName(SqlUtil.getString(rs,"job_name"))
                            .setGroupName(SqlUtil.getString(rs,"folder_name"))
                            .setShowName(SqlUtil.getString(rs,"show_name"))
                            .setPingTime((int) (rs.getTimestamp("ts_ping").getTime() / 1000))
                            .setBookedTime((int) (rs.getTimestamp("ts_booked").getTime() / 1000))
                            .setDispatchTime((int) (rs.getTimestamp("ts_dispatched").getTime() / 1000))
                            .setUnbooked(rs.getBoolean("b_unbooked"))
                            .setLogPath(String.format("%s/%s.%s.rqlog",
                                    SqlUtil.getString(rs,"str_log_dir"), SqlUtil.getString(rs,"job_name"),
                                    SqlUtil.getString(rs,"frame_name")))
                            .setRedirectTarget(SqlUtil.getString(rs, "str_redirect"))
                            .addAllServices(Arrays.asList(SqlUtil.getString(rs,"str_services").split(",")))
                            .build();
                }
            };

    public static final RowMapper<Comment> COMMENT_MAPPER =
            new RowMapper<Comment>() {

                public Comment mapRow(ResultSet rs, int row) throws SQLException {
                    return Comment.newBuilder()
                            .setId(SqlUtil.getString(rs,"pk_comment"))
                            .setMessage(SqlUtil.getString(rs,"str_message"))
                            .setSubject(SqlUtil.getString(rs,"str_subject"))
                            .setTimestamp((int)(rs.getTimestamp("ts_created").getTime() / 1000))
                            .setUser(SqlUtil.getString(rs,"str_user"))
                            .build();
                }
            };


    public static NestedHost.Builder mapNestedHostBuilder(ResultSet rs) throws SQLException {
        NestedHost.Builder builder = NestedHost.newBuilder()
                .setId(SqlUtil.getString(rs,"pk_host"))
                .setName(SqlUtil.getString(rs,"host_name"))
                .setAllocName(SqlUtil.getString(rs,"alloc_name"))
                .setBootTime((int) (rs.getTimestamp("ts_booted").getTime() / 1000))
                .setFreeMcp(rs.getLong("int_mcp_free"))
                .setFreeMemory(rs.getLong("int_mem_free"))
                .setFreeSwap(rs.getLong("int_swap_free"))
                .setFreeGpu(rs.getLong("int_gpu_free"))
                .setLoad(rs.getInt("int_load"))
                .setNimbyEnabled(rs.getBoolean("b_nimby"))
                .setCores(Convert.coreUnitsToCores(rs.getInt("int_cores")))
                .setIdleCores(Convert.coreUnitsToCores(rs.getInt("int_cores_idle")))
                .setMemory(rs.getLong("int_mem"))
                .setIdleMemory(rs.getLong("int_mem_idle"))
                .setGpu(rs.getLong("int_gpu"))
                .setIdleGpu(rs.getLong("int_gpu_idle"))
                .setState(HardwareState.valueOf(SqlUtil.getString(rs,"host_state")))
                .setTotalMcp(rs.getLong("int_mcp_total"))
                .setTotalMemory(rs.getLong("int_mem_total"))
                .setTotalSwap(rs.getLong("int_swap_total"))
                .setTotalGpu(rs.getLong("int_gpu_total"))
                .setPingTime((int) (rs.getTimestamp("ts_ping").getTime() / 1000))
                .setLockState(LockState.valueOf(SqlUtil.getString(rs,"str_lock_state")))
                .setHasComment(rs.getBoolean("b_comment"))
                .setThreadMode(ThreadMode.values()[rs.getInt("int_thread_mode")])
                .setOs(SqlUtil.getString(rs,"str_os"));

        String tags = SqlUtil.getString(rs,"str_tags");
        if (tags != null)
            builder.addAllTags(Arrays.asList(tags.split(" ")));
        return builder;
    }

    public static Host.Builder mapHostBuilder(ResultSet rs) throws SQLException {
        Host.Builder builder = Host.newBuilder();
        builder.setId(SqlUtil.getString(rs,"pk_host"));
        builder.setName(SqlUtil.getString(rs,"host_name"));
        builder.setAllocName(SqlUtil.getString(rs,"alloc_name"));
        builder.setBootTime((int) (rs.getTimestamp("ts_booted").getTime() / 1000));
        builder.setFreeMcp(rs.getLong("int_mcp_free"));
        builder.setFreeMemory(rs.getLong("int_mem_free"));
        builder.setFreeSwap(rs.getLong("int_swap_free"));
        builder.setFreeGpu(rs.getLong("int_gpu_free"));
        builder.setLoad(rs.getInt("int_load"));
        builder.setNimbyEnabled(rs.getBoolean("b_nimby"));
        builder.setCores(Convert.coreUnitsToCores(rs.getInt("int_cores")));
        builder.setIdleCores(Convert.coreUnitsToCores(rs.getInt("int_cores_idle")));
        builder.setMemory(rs.getLong("int_mem"));
        builder.setIdleMemory(rs.getLong("int_mem_idle"));
        builder.setGpu(rs.getLong("int_gpu"));
        builder.setIdleGpu(rs.getLong("int_gpu_idle"));
        builder.setState(HardwareState.valueOf(SqlUtil.getString(rs,"host_state")));
        builder.setTotalMcp(rs.getLong("int_mcp_total"));
        builder.setTotalMemory(rs.getLong("int_mem_total"));
        builder.setTotalSwap(rs.getLong("int_swap_total"));
        builder.setTotalGpu(rs.getLong("int_gpu_total"));
        builder.setPingTime((int) (rs.getTimestamp("ts_ping").getTime() / 1000));
        builder.setLockState(LockState.valueOf(SqlUtil.getString(rs,"str_lock_state")));
        builder.setHasComment(rs.getBoolean("b_comment"));
        builder.setThreadMode(ThreadMode.values()[rs.getInt("int_thread_mode")]);
        builder.setOs(SqlUtil.getString(rs,"str_os"));

        String tags =  SqlUtil.getString(rs,"str_tags");
        if (tags != null)
            builder.addAllTags(Arrays.asList(tags.split(" ")));
        return builder;
    }

    public static final RowMapper<Host> HOST_MAPPER =
            new RowMapper<Host>() {
                public Host mapRow(ResultSet rs, int row) throws SQLException {
                    Host.Builder builder = mapHostBuilder(rs);
                    return builder.build();
                }
            };

    public static final RowMapper<Depend> DEPEND_MAPPER =
            new RowMapper<Depend>() {
                public Depend mapRow(ResultSet rs, int rowNum) throws SQLException {
                    return Depend.newBuilder()
                            .setId(SqlUtil.getString(rs,"pk_depend"))
                            .setActive(rs.getBoolean("b_active"))
                            .setAnyFrame(rs.getBoolean("b_any"))
                            .setDependErFrame(SqlUtil.getString(rs,"depend_er_frame"))
                            .setDependErLayer(SqlUtil.getString(rs,"depend_er_layer"))
                            .setDependErJob(SqlUtil.getString(rs,"depend_er_job"))
                            .setDependOnFrame(SqlUtil.getString(rs,"depend_on_frame"))
                            .setDependOnLayer(SqlUtil.getString(rs,"depend_on_layer"))
                            .setDependOnJob(SqlUtil.getString(rs, "depend_on_job"))
                            .setType(DependType.valueOf(SqlUtil.getString(rs,"str_type")))
                            .setTarget(DependTarget.valueOf(SqlUtil.getString(rs,"str_target")))
                            .build();
                }
            };

    public static final RowMapper<Allocation> ALLOCATION_MAPPER =
        new RowMapper<Allocation>() {
            public Allocation mapRow(ResultSet rs, int rowNum) throws SQLException {
                return Allocation.newBuilder()
                        .setId(rs.getString("pk_alloc"))
                        .setName(rs.getString("str_name"))
                        .setFacility(rs.getString("facility_name"))
                        .setTag(rs.getString("str_tag"))
                        .setBillable(rs.getBoolean("b_billable"))
                        .setStats(AllocationStats.newBuilder()
                                .setCores(Convert.coreUnitsToCores(rs.getInt("int_cores")))
                                .setAvailableCores(Convert.coreUnitsToCores(rs.getInt("int_available_cores")))
                                .setIdleCores(Convert.coreUnitsToCores(rs.getInt("int_idle_cores")))
                                .setRunningCores(Convert.coreUnitsToCores(rs.getInt("int_running_cores")))
                                .setLockedCores(Convert.coreUnitsToCores(rs.getInt("int_locked_cores")))
                                .setHosts(rs.getInt("int_hosts"))
                                .setDownHosts(rs.getInt("int_down_hosts"))
                                .setLockedHosts(rs.getInt("int_locked_hosts"))
                                .build())
                        .build();
            }
    };

    private static final RowMapper<Group> GROUP_MAPPER =
            new RowMapper<Group>() {

                public Group mapRow(ResultSet rs, int rowNum) throws SQLException {
                    GroupStats stats = GroupStats.newBuilder()
                            .setDeadFrames(rs.getInt("int_dead_count"))
                            .setRunningFrames(rs.getInt("int_running_count"))
                            .setWaitingFrames(rs.getInt("int_waiting_count"))
                            .setDependFrames(rs.getInt("int_depend_count"))
                            .setPendingJobs(rs.getInt("int_job_count"))
                            .setReservedCores(Convert.coreUnitsToCores(rs.getInt("int_cores")))
                            .build();
                    return Group.newBuilder()
                            .setId(SqlUtil.getString(rs,"pk_folder"))
                            .setName(SqlUtil.getString(rs,"group_name"))
                            .setDefaultJobPriority(rs.getInt("int_job_priority"))
                            .setDefaultJobMinCores(Convert.coreUnitsToCores(rs.getInt("int_job_min_cores")))
                            .setDefaultJobMaxCores(Convert.coreUnitsToCores(rs.getInt("int_job_max_cores")))
                            .setMaxCores(Convert.coreUnitsToCores(rs.getInt("int_max_cores")))
                            .setMinCores(Convert.coreUnitsToCores(rs.getInt("int_min_cores")))
                            .setLevel(rs.getInt("int_level"))
                            .setParentId(SqlUtil.getString(rs, "pk_parent_folder"))
                            .setGroupStats(stats)
                            .build();
                }
            };

    public static final RowMapper<Job> JOB_MAPPER =
            new RowMapper<Job>() {
                public Job mapRow(ResultSet rs, int rowNum) throws SQLException {
                    Job.Builder jobBuilder = Job.newBuilder()
                            .setId(SqlUtil.getString(rs, "pk_job"))
                            .setLogDir(SqlUtil.getString(rs, "str_log_dir"))
                            .setMaxCores(Convert.coreUnitsToCores(rs.getInt("int_max_cores")))
                            .setMinCores(Convert.coreUnitsToCores(rs.getInt("int_min_cores")))
                            .setName(SqlUtil.getString(rs,"str_name"))
                            .setPriority(rs.getInt("int_priority"))
                            .setShot(SqlUtil.getString(rs,"str_shot"))
                            .setShow(SqlUtil.getString(rs,"str_show"))
                            .setFacility(SqlUtil.getString(rs,"facility_name"))
                            .setGroup(SqlUtil.getString(rs,"group_name"))
                            .setState(JobState.valueOf(SqlUtil.getString(rs,"str_state")))
                            .setUid(rs.getInt("int_uid"))
                            .setUser(SqlUtil.getString(rs,"str_user"))
                            .setIsPaused(rs.getBoolean("b_paused"))
                            .setHasComment(rs.getBoolean("b_comment"))
                            .setAutoEat(rs.getBoolean("b_autoeat"))
                            .setStartTime((int) (rs.getTimestamp("ts_started").getTime() / 1000))
                            .setOs(SqlUtil.getString(rs,"str_os"));

                    Timestamp ts = rs.getTimestamp("ts_stopped");
                    if (ts != null) {
                        jobBuilder.setStopTime((int) (ts.getTime() / 1000));
                    }
                    else {
                        jobBuilder.setStopTime(0);
                    }

                    jobBuilder.setJobStats(mapJobStats(rs));
                    return jobBuilder.build();
                }
            };

    public static JobStats mapJobStats(ResultSet rs) throws SQLException {

        JobStats.Builder statsBuilder = JobStats.newBuilder()
                .setReservedCores(Convert.coreUnitsToCores(rs.getInt("int_cores")))
                .setMaxRss(rs.getLong("int_max_rss"))
                .setTotalFrames(rs.getInt("int_frame_count"))
                .setTotalLayers(rs.getInt("int_layer_count"))
                .setWaitingFrames(rs.getInt("int_waiting_count"))
                .setRunningFrames(rs.getInt("int_running_count"))
                .setDeadFrames(rs.getInt("int_dead_count"))
                .setSucceededFrames(rs.getInt("int_succeeded_count"))
                .setEatenFrames(rs.getInt("int_eaten_count"))
                .setDependFrames(rs.getInt("int_depend_count"))
                .setPendingFrames(rs.getInt("int_waiting_count") + rs.getInt("int_depend_count"))
                .setFailedCoreSec(rs.getLong("int_core_time_fail"))
                .setRenderedCoreSec(rs.getLong("int_core_time_success"))
                .setTotalCoreSec( rs.getLong("int_core_time_fail") + rs.getLong("int_core_time_success"))
                .setRenderedFrameCount( rs.getLong("int_frame_success_count"))
                .setFailedFrameCount(rs.getLong("int_frame_fail_count"))
                .setHighFrameSec(rs.getInt("int_clock_time_high"));

        if (statsBuilder.getRenderedFrameCount() > 0) {
            statsBuilder.setAvgCoreSec(
                    (int) (rs.getLong("int_clock_time_success") / statsBuilder.getRenderedFrameCount()));
            statsBuilder.setAvgCoreSec(
                    (int) (statsBuilder.getRenderedCoreSec() / statsBuilder.getRenderedFrameCount()));
            statsBuilder.setRemainingCoreSec(statsBuilder.getPendingFrames() * statsBuilder.getAvgCoreSec());
        }
        else {
            statsBuilder.setAvgFrameSec(0);
            statsBuilder.setAvgCoreSec(0);
            statsBuilder.setRemainingCoreSec(0);
        }
        return statsBuilder.build();
    }

    public static final RowMapper<Layer> LAYER_MAPPER =
            new RowMapper<Layer>() {
                public Layer mapRow(ResultSet rs, int rowNum) throws SQLException {
                    Layer.Builder builder = Layer.newBuilder()
                            .setId(SqlUtil.getString(rs,"pk_layer"))
                            .setParentId(SqlUtil.getString(rs,"pk_job"))
                            .setChunkSize(rs.getInt("int_chunk_size"))
                            .setDispatchOrder(rs.getInt("int_dispatch_order"))
                            .setName(SqlUtil.getString(rs,"str_name"))
                            .setRange(SqlUtil.getString(rs,"str_range"))
                            .setMinCores(Convert.coreUnitsToCores(rs.getInt("int_cores_min")))
                            .setMaxCores(Convert.coreUnitsToCores(rs.getInt("int_cores_max")))
                            .setIsThreadable(rs.getBoolean("b_threadable"))
                            .setMinMemory(rs.getLong("int_mem_min"))
                            .setMinGpu(rs.getLong("int_gpu_min"))
                            .setType(LayerType.valueOf(SqlUtil.getString(rs,"str_type")))
                            .addAllTags(Sets.newHashSet(
                                    SqlUtil.getString(rs,"str_tags").
                                            replaceAll(" ","").split("\\|")))
                            .addAllServices(Arrays.asList(SqlUtil.getString(rs,"str_services").split(",")))
                            .setMemoryOptimizerEnabled(rs.getBoolean("b_optimize"));

                    LayerStats.Builder statsBuilder = LayerStats.newBuilder()
                            .setReservedCores(Convert.coreUnitsToCores(rs.getInt("int_cores")))
                            .setMaxRss(rs.getLong("int_max_rss"))
                            .setTotalFrames(rs.getInt("int_total_count"))
                            .setWaitingFrames(rs.getInt("int_waiting_count"))
                            .setRunningFrames(rs.getInt("int_running_count"))
                            .setDeadFrames(rs.getInt("int_dead_count"))
                            .setSucceededFrames(rs.getInt("int_succeeded_count"))
                            .setEatenFrames(rs.getInt("int_eaten_count"))
                            .setDependFrames(rs.getInt("int_depend_count"))
                            .setPendingFrames(
                                    rs.getInt("int_waiting_count") + rs.getInt("int_depend_count"))
                            .setFailedCoreSec(rs.getLong("int_core_time_fail"))
                            .setRenderedCoreSec(rs.getLong("int_core_time_success"))
                            .setTotalCoreSec(
                                    rs.getLong("int_core_time_fail") + rs.getLong("int_core_time_success"))
                            .setRenderedFrameCount( rs.getLong("int_frame_success_count"))
                            .setFailedFrameCount(rs.getLong("int_frame_fail_count"))
                            .setHighFrameSec(rs.getInt("int_clock_time_high"))
                            .setLowFrameSec(rs.getInt("int_clock_time_low"));

                    if (statsBuilder.getRenderedFrameCount() > 0) {
                        statsBuilder.setAvgFrameSec(
                                (int) (rs.getLong("int_clock_time_success") / statsBuilder.getRenderedFrameCount()));
                        statsBuilder.setAvgCoreSec(
                                (int) (statsBuilder.getRenderedCoreSec() / statsBuilder.getRenderedFrameCount()));
                        statsBuilder.setRemainingCoreSec(
                                statsBuilder.getPendingFrames() * statsBuilder.getAvgCoreSec());
                    }
                    else {
                        statsBuilder.setAvgFrameSec(0);
                        statsBuilder.setAvgCoreSec(0);
                        statsBuilder.setRemainingCoreSec(0);
                    }
                    builder.setLayerStats(statsBuilder.build());
                    return builder.build();
                }
            };

    public static final RowMapper<Subscription> SUBSCRIPTION_MAPPER =
        new RowMapper<Subscription>() {
            public Subscription mapRow(ResultSet rs, int rowNum) throws SQLException {
                return Subscription.newBuilder()
                        .setId(SqlUtil.getString(rs, "pk_subscription"))
                        .setBurst(rs.getInt("int_burst"))
                        .setName(rs.getString("name"))
                        .setReservedCores(rs.getInt("int_cores"))
                        .setSize(rs.getInt("int_size"))
                        .setAllocationName(rs.getString("alloc_name"))
                        .setShowName(rs.getString("show_name"))
                        .setFacility(rs.getString("facility_name"))
                        .build();
            }
    };

    public static final RowMapper<UpdatedFrame> UPDATED_FRAME_MAPPER =
            new RowMapper<UpdatedFrame>() {
                public UpdatedFrame mapRow(ResultSet rs, int rowNum) throws SQLException {
                    UpdatedFrame.Builder builder = UpdatedFrame.newBuilder()
                            .setId(SqlUtil.getString(rs, "pk_frame"))
                            .setExitStatus(rs.getInt("int_exit_status"))
                            .setMaxRss(rs.getInt("int_mem_max_used"))
                            .setRetryCount(rs.getInt("int_retries"))
                            .setState(FrameState.valueOf(SqlUtil.getString(rs, "str_state")))
                            .setUsedMemory(rs.getInt("int_mem_used"));

                    if (SqlUtil.getString(rs, "str_host") != null) {
                        builder.setLastResource(String.format(Locale.ROOT, "%s/%2.2f",
                                SqlUtil.getString(rs, "str_host"),
                                Convert.coreUnitsToCores(rs.getInt("int_cores"))));
                    } else {
                        builder.setLastResource("");
                    }

                    java.sql.Timestamp ts_started = rs.getTimestamp("ts_started");
                    if (ts_started != null) {
                        builder.setStartTime((int) (rs.getTimestamp("ts_started").getTime() / 1000));
                    } else {
                        builder.setStartTime(0);
                    }
                    java.sql.Timestamp ts_stopped = rs.getTimestamp("ts_stopped");
                    if (ts_stopped != null) {
                        builder.setStopTime((int) (ts_stopped.getTime() / 1000));
                    } else {
                        builder.setStopTime(0);
                    }

                    return builder.build();
                }
            };

    public static final RowMapper<Frame> FRAME_MAPPER =
            new RowMapper<Frame>() {
                public Frame mapRow(ResultSet rs, int rowNum) throws SQLException {
                    Frame.Builder builder = Frame.newBuilder()
                            .setId(SqlUtil.getString(rs,"pk_frame"))
                            .setName(SqlUtil.getString(rs,"str_name"))
                            .setExitStatus(rs.getInt("int_exit_status"))
                            .setMaxRss(rs.getLong("int_mem_max_used"))
                            .setNumber(rs.getInt("int_number"))
                            .setDispatchOrder(rs.getInt("int_dispatch_order"))
                            .setRetryCount(rs.getInt("int_retries"))
                            .setState(FrameState.valueOf(SqlUtil.getString(rs,"str_state")))
                            .setLayerName(SqlUtil.getString(rs,"layer_name"))
                            .setUsedMemory(rs.getLong("int_mem_used"))
                            .setReservedMemory(rs.getLong("int_mem_reserved"))
                            .setReservedGpu(rs.getLong("int_gpu_reserved"))
                            .setCheckpointState(CheckpointState.valueOf(
                                    SqlUtil.getString(rs,"str_checkpoint_state")))
                            .setCheckpointCount(rs.getInt("int_checkpoint_count"));

                    if (SqlUtil.getString(rs,"str_host") != null) {
                        builder.setLastResource(CueUtil.buildProcName(SqlUtil.getString(rs,"str_host"),
                                rs.getInt("int_cores")));
                    } else {
                        builder.setLastResource("");
                    }

                    java.sql.Timestamp ts_started = rs.getTimestamp("ts_started");
                    if (ts_started != null) {
                        builder.setStartTime((int) (rs.getTimestamp("ts_started").getTime() / 1000));
                    }
                    else {
                        builder.setStartTime(0);
                    }
                    java.sql.Timestamp ts_stopped = rs.getTimestamp("ts_stopped");
                    if (ts_stopped!= null) {
                        builder.setStopTime((int) (ts_stopped.getTime() / 1000));
                    }
                    else {
                        builder.setStopTime(0);
                    }

                    builder.setTotalCoreTime(rs.getInt("int_total_past_core_time"));
                    if (builder.getState() == FrameState.RUNNING) {
                        builder.setTotalCoreTime(builder.getTotalCoreTime() +
                                (int)(System.currentTimeMillis() / 1000 - builder.getStartTime()) * rs.getInt("int_cores") / 100);
                    }
                    return builder.build();
                }
            };

    private static final RowMapper<Service> SERVICE_MAPPER =
            new RowMapper<Service>() {
                public Service mapRow(ResultSet rs, int rowNum) throws SQLException {
                    return Service.newBuilder()
                            .setId(SqlUtil.getString(rs,"pk_service"))
                            .setName(SqlUtil.getString(rs,"str_name"))
                            .setThreadable(rs.getBoolean("b_threadable"))
                            .setMinCores(rs.getInt("int_cores_min"))
                            .setMaxCores(rs.getInt("int_cores_max"))
                            .setMinMemory(rs.getInt("int_mem_min"))
                            .setMinGpu(rs.getInt("int_gpu_min"))
                            .addAllTags(Lists.newArrayList(ServiceDaoJdbc.splitTags(
                                    SqlUtil.getString(rs,"str_tags"))))
                            .build();
                }
            };

    private static final RowMapper<ServiceOverride> SERVICE_OVERRIDE_MAPPER =
            new RowMapper<ServiceOverride>() {
                public ServiceOverride mapRow(ResultSet rs, int rowNum) throws SQLException {
                    Service data = Service.newBuilder()
                            .setId(SqlUtil.getString(rs,"pk_show_service"))
                            .setName(SqlUtil.getString(rs,"str_name"))
                            .setThreadable(rs.getBoolean("b_threadable"))
                            .setMinCores(rs.getInt("int_cores_min"))
                            .setMaxCores(rs.getInt("int_cores_max"))
                            .setMinMemory(rs.getInt("int_mem_min"))
                            .setMinGpu(rs.getInt("int_gpu_min"))
                            .addAllTags(Lists.newArrayList(ServiceDaoJdbc.splitTags(
                                    SqlUtil.getString(rs,"str_tags"))))
                            .build();
                    return ServiceOverride.newBuilder()
                            .setId(SqlUtil.getString(rs,"pk_show_service"))
                            .setData(data)
                            .build();
                }
            };

    public static final RowMapper<Show> SHOW_MAPPER =
            new RowMapper<Show>() {
                public Show mapRow(ResultSet rs, int rowNum) throws SQLException {
                    ShowStats stats = ShowStats.newBuilder()
                            .setPendingFrames(rs.getInt("int_pending_count"))
                            .setRunningFrames(rs.getInt("int_running_count"))
                            .setDeadFrames(rs.getInt("int_dead_count"))
                            .setCreatedFrameCount(rs.getLong("int_frame_insert_count"))
                            .setCreatedJobCount(rs.getLong("int_job_insert_count"))
                            .setRenderedFrameCount(rs.getLong("int_frame_success_count"))
                            .setFailedFrameCount(rs.getLong("int_frame_fail_count"))
                            .setReservedCores(Convert.coreUnitsToCores(rs.getInt("int_cores")))
                            .setPendingJobs(rs.getInt("int_job_count"))
                            .build();
                    return Show.newBuilder()
                            .setId(SqlUtil.getString(rs,"pk_show"))
                            .setName(SqlUtil.getString(rs,"str_name"))
                            .setActive(rs.getBoolean("b_active"))
                            .setDefaultMaxCores(Convert.coreUnitsToCores(rs.getInt("int_default_max_cores")))
                            .setDefaultMinCores(Convert.coreUnitsToCores(rs.getInt("int_default_min_cores")))
                            .setBookingEnabled(rs.getBoolean("b_booking_enabled"))
                            .setDispatchEnabled(rs.getBoolean("b_dispatch_enabled"))
                            .setCommentEmail(SqlUtil.getString(rs,"str_comment_email"))
                            .setShowStats(stats)
                            .build();
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
            "job.str_state = 'PENDING' ";

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
            "job.str_state='PENDING' " +
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
        "LEFT JOIN redirect ON proc.pk_proc = redirect.pk_proc " +
        "WHERE true ";

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
            "COALESCE(vs_show_stat.int_pending_count,0) AS int_pending_count," +
            "COALESCE(vs_show_stat.int_running_count,0) AS int_running_count," +
            "COALESCE(vs_show_stat.int_dead_count,0) AS int_dead_count," +
            "COALESCE(vs_show_resource.int_cores,0) AS int_cores, " +
            "COALESCE(vs_show_stat.int_job_count,0) AS int_job_count " +
        "FROM " +
            "show " +
        "LEFT JOIN vs_show_stat ON (vs_show_stat.pk_show = show.pk_show) " +
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
            "job.str_state = 'PENDING' ";

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

    public FrameSearchFactory getFrameSearchFactory() {
        return frameSearchFactory;
    }

    public void setFrameSearchFactory(FrameSearchFactory frameSearchFactory) {
        this.frameSearchFactory = frameSearchFactory;
    }

    public ProcSearchFactory getProcSearchFactory() {
        return procSearchFactory;
    }

    public void setProcSearchFactory(ProcSearchFactory procSearchFactory) {
        this.procSearchFactory = procSearchFactory;
    }
}

