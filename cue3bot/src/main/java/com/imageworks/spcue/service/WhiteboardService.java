
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

import com.imageworks.spcue.CueClientIce.Action;
import com.imageworks.spcue.CueClientIce.Allocation;
import com.imageworks.spcue.CueClientIce.Comment;
import com.imageworks.spcue.CueClientIce.Deed;
import com.imageworks.spcue.CueClientIce.Depend;
import com.imageworks.spcue.CueClientIce.Filter;
import com.imageworks.spcue.CueClientIce.Frame;
import com.imageworks.spcue.CueClientIce.Group;
import com.imageworks.spcue.CueClientIce.Host;
import com.imageworks.spcue.CueClientIce.Job;
import com.imageworks.spcue.CueClientIce.Layer;
import com.imageworks.spcue.CueClientIce.Matcher;
import com.imageworks.spcue.CueClientIce.NestedGroup;
import com.imageworks.spcue.CueClientIce.NestedHost;
import com.imageworks.spcue.CueClientIce.Owner;
import com.imageworks.spcue.CueClientIce.Proc;
import com.imageworks.spcue.CueClientIce.RenderPartition;
import com.imageworks.spcue.CueClientIce.Service;
import com.imageworks.spcue.CueClientIce.ServiceOverride;
import com.imageworks.spcue.CueClientIce.Show;
import com.imageworks.spcue.CueClientIce.Subscription;
import com.imageworks.spcue.CueClientIce.Task;
import com.imageworks.spcue.CueClientIce.UpdatedFrameCheckResult;
import com.imageworks.spcue.CueGrpc.Facility;
import org.apache.log4j.Logger;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.Department;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.NestedWhiteboardDao;
import com.imageworks.spcue.dao.WhiteboardDao;
import com.imageworks.spcue.dao.criteria.FrameSearch;
import com.imageworks.spcue.dao.criteria.HostSearch;
import com.imageworks.spcue.dao.criteria.JobSearch;
import com.imageworks.spcue.dao.criteria.ProcSearch;
import com.imageworks.spcue.depend.AbstractDepend;

/**
* Traditionally the "Whiteboard" was an actually whiteboard the PSTs used to
* use to track jobs.  Over time that term has come to mean an interface
* from which you can query cue data.  The WhiteboardService defines
* all the methods from which clients can obtain data.  All Ice servants
* that return something go through here.
*
* The whiteboard is a ready only transaction with a SERIALIZABLE transaction
* level.  Moving the SERIALIZABLE actually makes the requests run faster
* because the readers view of the DB is fixed throughout the transaction.
*
*/
@Transactional(readOnly = true, propagation = Propagation.REQUIRED)
public class WhiteboardService implements Whiteboard {

    @SuppressWarnings("unused")
    private static final Logger logger = Logger.getLogger(WhiteboardService.class);

    private WhiteboardDao whiteboardDao;

    private NestedWhiteboardDao nestedWhiteboardDao;

    private JobDao jobDao;

    public JobDao getJobDao() {
        return jobDao;
    }

    public void setJobDao(JobDao jobDao) {
        this.jobDao = jobDao;
    }

    public boolean isJobPending(String name) {
        return jobDao.exists(name);
    }

    public List<Filter> getFilters(com.imageworks.spcue.Show show) {
        return whiteboardDao.getFilters(show);
    }

    public List<Layer> getLayers(com.imageworks.spcue.Job job) {
        return whiteboardDao.getLayers(job);
    }

    public List<String> getJobNames(JobSearch r) {
        return whiteboardDao.getJobNames(r);
    }

    public Job findJob(String name) {
        return whiteboardDao.findJob(name);
    }

    public Job getJob(String id) {
        return whiteboardDao.getJob(id);
    }

    public List<Frame> getFrames(FrameSearch r) {
        return this.whiteboardDao.getFrames(r);
    }

    public List<NestedHost> getHostWhiteboard() {
        return nestedWhiteboardDao.getHostWhiteboard();
    }

    public Show findShow(String name) {
        return whiteboardDao.findShow(name);
    }

    public Show getShow(String id) {
        return  whiteboardDao.getShow(id);
    }

    public List<Show> getShows() {
        return whiteboardDao.getShows();
    }

    public Subscription getSubscription(String id) {
        return this.whiteboardDao.getSubscription(id);
    }

    public List<Subscription> getSubscriptions(com.imageworks.spcue.Show show) {
        return this.whiteboardDao.getSubscriptions(show);
    }

    public Allocation findAllocation(String name) {
        return this.whiteboardDao.findAllocation(name);
    }

    public Allocation getAllocation(String id) {
        return this.whiteboardDao.getAllocation(id);
    }

    public List<Allocation> getAllocations() {
        return this.whiteboardDao.getAllocations();
    }

    public List<Group> getGroups(com.imageworks.spcue.Show show) {
        return this.whiteboardDao.getGroups(show);
    }

    public List<Group> getGroups(com.imageworks.spcue.Group group) {
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

    public Action getAction(com.imageworks.spcue.Action action) {
        return whiteboardDao.getAction(action);
    }

    public List<Action> getActions(com.imageworks.spcue.Filter filter) {
        return whiteboardDao.getActions(filter);
    }

    public Matcher getMatcher(com.imageworks.spcue.Matcher matcher) {
        return whiteboardDao.getMatcher(matcher);
    }

    public List<Matcher> getMatchers(com.imageworks.spcue.Filter filter) {
        return whiteboardDao.getMatchers(filter);
    }

    public Filter getFilter(com.imageworks.spcue.Filter filter) {
        return whiteboardDao.getFilter(filter);
    }

    public Filter findFilter(com.imageworks.spcue.Show show, String name) {
        return whiteboardDao.findFilter(show, name);
    }

    public Group getRootGroup(com.imageworks.spcue.Show show) {
        return whiteboardDao.getRootGroup(show);
    }

    public NestedGroup getJobWhiteboard(com.imageworks.spcue.Show show) {
        return nestedWhiteboardDao.getJobWhiteboard(show);
    }

    public List<Job> getJobs(com.imageworks.spcue.Group group) {
        return whiteboardDao.getJobs(group);
    }

    public NestedWhiteboardDao getNestedWhiteboardDao() {
        return nestedWhiteboardDao;
    }

    public void setNestedWhiteboardDao(NestedWhiteboardDao nestedWhiteboardDao) {
        this.nestedWhiteboardDao = nestedWhiteboardDao;
    }

    public Depend getDepend(com.imageworks.spcue.Depend depend) {
        return whiteboardDao.getDepend(depend);
    }

    public List<Depend> getWhatDependsOnThis(com.imageworks.spcue.Job job) {

        return whiteboardDao.getWhatDependsOnThis(job);
    }

    public List<Depend> getWhatDependsOnThis(com.imageworks.spcue.Layer layer) {
        return whiteboardDao.getWhatDependsOnThis(layer);
    }

    public List<Depend> getWhatDependsOnThis(com.imageworks.spcue.Frame frame) {
        return whiteboardDao.getWhatDependsOnThis(frame);
    }

    public List<Depend> getWhatThisDependsOn(com.imageworks.spcue.Job job) {
        return whiteboardDao.getWhatThisDependsOn(job);
    }

    public List<Depend> getWhatThisDependsOn(com.imageworks.spcue.Layer layer) {
        return whiteboardDao.getWhatThisDependsOn(layer);
    }

    public List<Depend> getWhatThisDependsOn(com.imageworks.spcue.Frame frame) {
        return whiteboardDao.getWhatThisDependsOn(frame);
    }

    public List<Depend> getDepends(com.imageworks.spcue.Job job) {
        return whiteboardDao.getDepends(job);
    }

    public Frame findFrame(String job, String layer, int frame) {
        return whiteboardDao.findFrame(job, layer, frame);
    }

    public Layer findLayer(String job, String layer) {
        return whiteboardDao.findLayer(job, layer);
    }

    public Host findHost(String name) {
        return whiteboardDao.findHost(name);
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

    public UpdatedFrameCheckResult getUpdatedFrames(com.imageworks.spcue.Job job,
                                                    List<com.imageworks.spcue.Layer> layers, int epochTime) {
        return whiteboardDao.getUpdatedFrames(job, layers, epochTime);
    }

    public List<Comment> getComments(com.imageworks.spcue.Job j) {
        return whiteboardDao.getComments(j);
    }

    public List<Comment> getComments(com.imageworks.spcue.Host h) {
        return whiteboardDao.getComments(h);
    }

    public List<Subscription> getSubscriptions(
            com.imageworks.spcue.Allocation alloc) {
        return whiteboardDao.getSubscriptions(alloc);
    }

    public Subscription findSubscription(String show, String alloc) {
        return whiteboardDao.findSubscription(show, alloc);
    }

    @Override
    public Task getTask(com.imageworks.spcue.Show show, Department dept, String shot) {
        return whiteboardDao.getTask(show, dept, shot);
    }

    @Override
    public List<Task> getTasks(com.imageworks.spcue.Show show, Department dept) {
        return whiteboardDao.getTasks(show, dept);
    }

    @Override
    public List<String> getDepartmentNames() {
        return whiteboardDao.getDepartmentNames();
    }

    @Override
    public com.imageworks.spcue.CueClientIce.Department getDepartment(
            com.imageworks.spcue.Show show, String name) {
        return whiteboardDao.getDepartment(show, name);
    }

    @Override
    public List<com.imageworks.spcue.CueClientIce.Department> getDepartments(
            com.imageworks.spcue.Show show) {
        return whiteboardDao.getDepartments(show);
    }

    @Override
    public List<Job> getJobs(JobSearch r) {
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
    public List<Host> getHosts(HostSearch r) {
        return whiteboardDao.getHosts(r);
    }

    @Override
    public List<Proc> getProcs(com.imageworks.spcue.Host h) {
        return whiteboardDao.getProcs(h);
    }

    @Override
    public List<Proc> getProcs(ProcSearch p) {
        return whiteboardDao.getProcs(p);
    }

    @Override
    public Depend getDepend(AbstractDepend depend) {
        return whiteboardDao.getDepend(depend);
    }

    @Override
    public Host getHost(com.imageworks.spcue.Deed deed) {
        return whiteboardDao.getHost(deed);
    }

    @Override
    public Owner getOwner(com.imageworks.spcue.Deed deed) {
        return whiteboardDao.getOwner(deed);
    }

    @Override
    public List<Deed> getDeeds(
            com.imageworks.spcue.Owner owner) {
        return whiteboardDao.getDeeds(owner);
    }

    @Override
    public List<Deed> getDeeds(
            com.imageworks.spcue.Show show) {
        return whiteboardDao.getDeeds(show);
    }

    @Override
    public List<Host> getHosts(com.imageworks.spcue.Owner owner) {
        return whiteboardDao.getHosts(owner);
    }

    @Override
    public Owner getOwner(com.imageworks.spcue.Host host) {
        return whiteboardDao.getOwner(host);
    }

    @Override
    public List<Owner> getOwners(com.imageworks.spcue.Show show) {
        return whiteboardDao.getOwners(show);
    }

    @Override
    public Owner getOwner(String name) {
        return whiteboardDao.getOwner(name);
    }

    @Override
    public Deed getDeed(com.imageworks.spcue.Host host) {
        return whiteboardDao.getDeed(host);
    }

    @Override
    public RenderPartition getRenderPartition(LocalHostAssignment l) {
        return whiteboardDao.getRenderPartition(l);
    }

    @Override
    public List<RenderPartition> getRenderPartitions(
            com.imageworks.spcue.Host host) {
        return whiteboardDao.getRenderPartitions(host);
    }

    @Override
    public List<Facility> getFacilities() {
        return whiteboardDao.getFacilities();
    }

    @Override
    public Facility getFacility(String name) {
        return whiteboardDao.getFacility(name);
    }

    @Override
    public List<Allocation> getAllocations(
            com.imageworks.spcue.FacilityInterface facility) {
        return whiteboardDao.getAllocations(facility);
    }

    @Override
    public List<Show> getActiveShows() {
        return whiteboardDao.getActiveShows();
    }

    @Override
    public Service getService(String id) {
        return whiteboardDao.getService(id);
    }

    @Override
    public List<Service> getDefaultServices() {
        return whiteboardDao.getDefaultServices();
    }

    @Override
    public Service findService(String name) {
        return whiteboardDao.findService(name);
    }

    @Override
    public List<ServiceOverride> getServiceOverrides(
            com.imageworks.spcue.Show show) {
        return whiteboardDao.getServiceOverrides(show);
    }

    @Override
    public ServiceOverride getServiceOverride(com.imageworks.spcue.Show show,
            String name) {
        return whiteboardDao.getServiceOverride(show, name);
    }
}

