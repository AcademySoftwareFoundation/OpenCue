
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



package com.imageworks.spcue.service;

import java.util.List;

import org.apache.log4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

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
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.NestedWhiteboardDao;
import com.imageworks.spcue.dao.WhiteboardDao;
import com.imageworks.spcue.dao.criteria.FrameSearchInterface;
import com.imageworks.spcue.dao.criteria.HostSearchInterface;
import com.imageworks.spcue.dao.criteria.JobSearchInterface;
import com.imageworks.spcue.dao.criteria.ProcSearchInterface;
import com.imageworks.spcue.depend.AbstractDepend;
import com.imageworks.spcue.grpc.comment.CommentSeq;
import com.imageworks.spcue.grpc.depend.Depend;
import com.imageworks.spcue.grpc.depend.DependSeq;
import com.imageworks.spcue.grpc.facility.Allocation;
import com.imageworks.spcue.grpc.facility.AllocationSeq;
import com.imageworks.spcue.grpc.facility.Facility;
import com.imageworks.spcue.grpc.facility.FacilitySeq;
import com.imageworks.spcue.grpc.filter.Action;
import com.imageworks.spcue.grpc.filter.ActionSeq;
import com.imageworks.spcue.grpc.filter.Filter;
import com.imageworks.spcue.grpc.filter.FilterSeq;
import com.imageworks.spcue.grpc.filter.Matcher;
import com.imageworks.spcue.grpc.filter.MatcherSeq;
import com.imageworks.spcue.grpc.host.Deed;
import com.imageworks.spcue.grpc.host.DeedSeq;
import com.imageworks.spcue.grpc.host.Host;
import com.imageworks.spcue.grpc.host.HostSeq;
import com.imageworks.spcue.grpc.host.NestedHostSeq;
import com.imageworks.spcue.grpc.host.Owner;
import com.imageworks.spcue.grpc.host.ProcSeq;
import com.imageworks.spcue.grpc.job.Frame;
import com.imageworks.spcue.grpc.job.FrameSeq;
import com.imageworks.spcue.grpc.job.Group;
import com.imageworks.spcue.grpc.job.GroupSeq;
import com.imageworks.spcue.grpc.job.Job;
import com.imageworks.spcue.grpc.job.JobSeq;
import com.imageworks.spcue.grpc.job.Layer;
import com.imageworks.spcue.grpc.job.LayerSeq;
import com.imageworks.spcue.grpc.job.NestedGroup;
import com.imageworks.spcue.grpc.job.UpdatedFrameCheckResult;
import com.imageworks.spcue.grpc.renderpartition.RenderPartition;
import com.imageworks.spcue.grpc.renderpartition.RenderPartitionSeq;
import com.imageworks.spcue.grpc.service.Service;
import com.imageworks.spcue.grpc.service.ServiceOverride;
import com.imageworks.spcue.grpc.service.ServiceOverrideSeq;
import com.imageworks.spcue.grpc.service.ServiceSeq;
import com.imageworks.spcue.grpc.show.Show;
import com.imageworks.spcue.grpc.show.ShowSeq;
import com.imageworks.spcue.grpc.subscription.Subscription;
import com.imageworks.spcue.grpc.subscription.SubscriptionSeq;
import com.imageworks.spcue.grpc.task.Task;
import com.imageworks.spcue.grpc.task.TaskSeq;


/**
* Traditionally the "Whiteboard" was an actually whiteboard the PSTs used to
* use to track jobs.  Over time that term has come to mean an interface
* from which you can query cue data.  The WhiteboardService defines
* all the methods from which clients can obtain data.  All grpc servants
* that return something go through here.
*
* The whiteboard is a ready only transaction with a SERIALIZABLE transaction
* level.  Moving the SERIALIZABLE actually makes the requests run faster
* because the readers view of the DB is fixed throughout the transaction.
*
*/
@org.springframework.stereotype.Service
@Transactional(readOnly = true, propagation = Propagation.REQUIRED)
public class WhiteboardService implements Whiteboard {

    @SuppressWarnings("unused")
    private static final Logger logger = Logger.getLogger(WhiteboardService.class);

    @Autowired
    private WhiteboardDao whiteboardDao;

    @Autowired
    private NestedWhiteboardDao nestedWhiteboardDao;

    @Autowired
    private JobDao jobDao;

    public boolean isJobPending(String name) {
        return jobDao.exists(name);
    }

    public FilterSeq getFilters(ShowInterface show) {
        return whiteboardDao.getFilters(show);
    }

    public LayerSeq getLayers(JobInterface job) {
        return whiteboardDao.getLayers(job);
    }

    public List<String> getJobNames(JobSearchInterface r) {
        return whiteboardDao.getJobNames(r);
    }

    public Job findJob(String name) {
        return whiteboardDao.findJob(name);
    }

    public Job getJob(String id) {
        return whiteboardDao.getJob(id);
    }

    public FrameSeq getFrames(FrameSearchInterface r) {
        return this.whiteboardDao.getFrames(r);
    }

    public NestedHostSeq getHostWhiteboard() {
        return nestedWhiteboardDao.getHostWhiteboard();
    }

    public Show findShow(String name) {
        return whiteboardDao.findShow(name);
    }

    public Show getShow(String id) {
        return  whiteboardDao.getShow(id);
    }

    public ShowSeq getShows() {
        return whiteboardDao.getShows();
    }

    public Subscription getSubscription(String id) {
        return this.whiteboardDao.getSubscription(id);
    }

    public SubscriptionSeq getSubscriptions(ShowInterface show) {
        return this.whiteboardDao.getSubscriptions(show);
    }

    public Allocation findAllocation(String name) {
        return this.whiteboardDao.findAllocation(name);
    }

    public Allocation getAllocation(String id) {
        return this.whiteboardDao.getAllocation(id);
    }

    public AllocationSeq getAllocations() {
        return this.whiteboardDao.getAllocations();
    }

    public GroupSeq getGroups(ShowInterface show) {
        return this.whiteboardDao.getGroups(show);
    }

    public GroupSeq getGroups(GroupInterface group) {
        return this.whiteboardDao.getGroups(group);
    }

    public Group getGroup(String id) {
        return this.whiteboardDao.getGroup(id);
    }

    public WhiteboardDao getWhiteboardDao() {
        return whiteboardDao;
    }

    public void setWhiteboardDao(WhiteboardDao whiteboardDao) {
        this.whiteboardDao = whiteboardDao;
    }

    public Action getAction(ActionInterface action) {
        return whiteboardDao.getAction(action);
    }

    public ActionSeq getActions(FilterInterface filter) {
        return whiteboardDao.getActions(filter);
    }

    public Matcher getMatcher(MatcherInterface matcher) {
        return whiteboardDao.getMatcher(matcher);
    }

    public MatcherSeq getMatchers(FilterInterface filter) {
        return whiteboardDao.getMatchers(filter);
    }

    public Filter getFilter(FilterInterface filter) {
        return whiteboardDao.getFilter(filter);
    }

    public Filter findFilter(ShowInterface show, String name) {
        return whiteboardDao.findFilter(show, name);
    }

    public Group getRootGroup(ShowInterface show) {
        return whiteboardDao.getRootGroup(show);
    }

    public NestedGroup getJobWhiteboard(ShowInterface show) {
        return nestedWhiteboardDao.getJobWhiteboard(show);
    }

    public JobSeq getJobs(GroupInterface group) {
        return whiteboardDao.getJobs(group);
    }

    public NestedWhiteboardDao getNestedWhiteboardDao() {
        return nestedWhiteboardDao;
    }

    public void setNestedWhiteboardDao(NestedWhiteboardDao nestedWhiteboardDao) {
        this.nestedWhiteboardDao = nestedWhiteboardDao;
    }

    public Depend getDepend(DependInterface depend) {
        return whiteboardDao.getDepend(depend);
    }

    public DependSeq getWhatDependsOnThis(JobInterface job) {

        return whiteboardDao.getWhatDependsOnThis(job);
    }

    public DependSeq getWhatDependsOnThis(LayerInterface layer) {
        return whiteboardDao.getWhatDependsOnThis(layer);
    }

    public DependSeq getWhatDependsOnThis(FrameInterface frame) {
        return whiteboardDao.getWhatDependsOnThis(frame);
    }

    public DependSeq getWhatThisDependsOn(JobInterface job) {
        return whiteboardDao.getWhatThisDependsOn(job);
    }

    public DependSeq getWhatThisDependsOn(LayerInterface layer) {
        return whiteboardDao.getWhatThisDependsOn(layer);
    }

    public DependSeq getWhatThisDependsOn(FrameInterface frame) {
        return whiteboardDao.getWhatThisDependsOn(frame);
    }

    public DependSeq getDepends(JobInterface job) {
        return whiteboardDao.getDepends(job);
    }

    public Frame findFrame(String job, String layer, int frame) {
        return whiteboardDao.findFrame(job, layer, frame);
    }

    public Layer findLayer(String job, String layer) {
        return whiteboardDao.findLayer(job, layer);
    }

    public Host findHost(String name) { return whiteboardDao.findHost(name);
    }

    public Depend getDepend(String id) {
        return whiteboardDao.getDepend(id);
    }

    public Group findGroup(String show, String group) {
        return whiteboardDao.findGroup(show, group);
    }

    public Filter findFilter(String show, String name) {
        return whiteboardDao.findFilter(show, name);
    }

    public UpdatedFrameCheckResult getUpdatedFrames(JobInterface job,
                                                    List<LayerInterface> layers, int epochTime) {
        return whiteboardDao.getUpdatedFrames(job, layers, epochTime);
    }

    public CommentSeq getComments(JobInterface j) {
        return whiteboardDao.getComments(j);
    }

    public CommentSeq getComments(HostInterface h) {
        return whiteboardDao.getComments(h);
    }

    public SubscriptionSeq getSubscriptions(
            AllocationInterface alloc) {
        return whiteboardDao.getSubscriptions(alloc);
    }

    public Subscription findSubscription(String show, String alloc) {
        return whiteboardDao.findSubscription(show, alloc);
    }

    @Override
    public JobSeq getJobs(JobSearchInterface r) {
        return whiteboardDao.getJobs(r);
    }

    @Override
    public Frame getFrame(String id) {
        return whiteboardDao.getFrame(id);
    }

    @Override
    public Host getHost(String id) {
        return whiteboardDao.getHost(id);
    }

    @Override
    public Layer getLayer(String id) {
        return whiteboardDao.getLayer(id);
    }

    @Override
    public HostSeq getHosts(HostSearchInterface r) {
        return whiteboardDao.getHosts(r);
    }

    @Override
    public ProcSeq getProcs(HostInterface h) {
        return whiteboardDao.getProcs(h);
    }

    @Override
    public ProcSeq getProcs(ProcSearchInterface p) {
        return whiteboardDao.getProcs(p);
    }

    @Override
    public Depend getDepend(AbstractDepend depend) {
        return whiteboardDao.getDepend(depend);
    }

    @Override
    public Host getHost(DeedEntity deed) {
        return whiteboardDao.getHost(deed);
    }

    @Override
    public Owner getOwner(DeedEntity deed) {
        return whiteboardDao.getOwner(deed);
    }

    @Override
    public DeedSeq getDeeds(
            OwnerEntity owner) {
        return whiteboardDao.getDeeds(owner);
    }

    @Override
    public DeedSeq getDeeds(
            ShowInterface show) {
        return whiteboardDao.getDeeds(show);
    }

    @Override
    public HostSeq getHosts(OwnerEntity owner) {
        return whiteboardDao.getHosts(owner);
    }

    @Override
    public Owner getOwner(HostInterface host) {
        return whiteboardDao.getOwner(host);
    }

    @Override
    public List<Owner> getOwners(ShowInterface show) {
        return whiteboardDao.getOwners(show);
    }

    @Override
    public Owner getOwner(String name) {
        return whiteboardDao.getOwner(name);
    }

    @Override
    public Deed getDeed(HostInterface host) {
        return whiteboardDao.getDeed(host);
    }

    @Override
    public RenderPartition getRenderPartition(LocalHostAssignment l) {
        return whiteboardDao.getRenderPartition(l);
    }

    @Override
    public RenderPartitionSeq getRenderPartitions(
            HostInterface host) {
        return whiteboardDao.getRenderPartitions(host);
    }

    @Override
    public FacilitySeq getFacilities() {
        return whiteboardDao.getFacilities();
    }

    @Override
    public Facility getFacility(String name) {
        return whiteboardDao.getFacility(name);
    }

    @Override
    public AllocationSeq getAllocations(
            com.imageworks.spcue.FacilityInterface facility) {
        return whiteboardDao.getAllocations(facility);
    }

    @Override
    public ShowSeq getActiveShows() {
        return whiteboardDao.getActiveShows();
    }

    @Override
    public Service getService(String id) {
        return whiteboardDao.getService(id);
    }

    @Override
    public ServiceSeq getDefaultServices() {
        return whiteboardDao.getDefaultServices();
    }

    @Override
    public Service findService(String name) {
        return whiteboardDao.findService(name);
    }

    @Override
    public ServiceOverrideSeq getServiceOverrides(
            ShowInterface show) {
        return whiteboardDao.getServiceOverrides(show);
    }

    @Override
    public ServiceOverride getServiceOverride(ShowInterface show,
            String name) {
        return whiteboardDao.getServiceOverride(show, name);
    }
}

