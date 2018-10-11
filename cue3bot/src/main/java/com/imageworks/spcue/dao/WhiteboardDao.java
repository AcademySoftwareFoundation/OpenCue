
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



package com.imageworks.spcue.dao;

import java.util.List;

import com.imageworks.spcue.*;

import com.imageworks.spcue.grpc.comment.CommentSeq;
import com.imageworks.spcue.grpc.department.Department;
import com.imageworks.spcue.grpc.department.DepartmentSeq;
import com.imageworks.spcue.grpc.depend.Depend;
import com.imageworks.spcue.grpc.depend.DependSeq;
import com.imageworks.spcue.grpc.facility.Allocation;
import com.imageworks.spcue.grpc.filter.Action;
import com.imageworks.spcue.grpc.facility.Facility;
import com.imageworks.spcue.grpc.filter.Filter;
import com.imageworks.spcue.grpc.filter.FilterSeq;
import com.imageworks.spcue.grpc.filter.Matcher;
import com.imageworks.spcue.grpc.host.Deed;
import com.imageworks.spcue.grpc.host.DeedSeq;
import com.imageworks.spcue.grpc.host.Host;
import com.imageworks.spcue.grpc.host.HostSeq;
import com.imageworks.spcue.grpc.host.Owner;
import com.imageworks.spcue.grpc.host.Proc;
import com.imageworks.spcue.grpc.host.ProcSeq;
import com.imageworks.spcue.grpc.job.Frame;
import com.imageworks.spcue.grpc.job.FrameSeq;
import com.imageworks.spcue.grpc.job.Group;
import com.imageworks.spcue.grpc.job.GroupSeq;
import com.imageworks.spcue.grpc.job.Job;
import com.imageworks.spcue.grpc.job.JobSeq;
import com.imageworks.spcue.grpc.job.Layer;
import com.imageworks.spcue.grpc.job.LayerSeq;
import com.imageworks.spcue.grpc.job.UpdatedFrameCheckResult;
import com.imageworks.spcue.grpc.renderpartition.RenderPartition;
import com.imageworks.spcue.grpc.renderpartition.RenderPartitionSeq;
import com.imageworks.spcue.grpc.service.Service;
import com.imageworks.spcue.grpc.service.ServiceOverride;
import com.imageworks.spcue.grpc.service.ServiceSeq;
import com.imageworks.spcue.grpc.show.Show;
import com.imageworks.spcue.grpc.show.ShowSeq;
import com.imageworks.spcue.grpc.subscription.SubscriptionSeq;
import com.imageworks.spcue.grpc.task.Task;

import com.imageworks.spcue.dao.criteria.FrameSearch;
import com.imageworks.spcue.dao.criteria.HostSearch;
import com.imageworks.spcue.dao.criteria.JobSearch;
import com.imageworks.spcue.dao.criteria.ProcSearch;
import com.imageworks.spcue.depend.AbstractDepend;
import com.imageworks.spcue.grpc.subscription.Subscription;

/**
 * @category DAO
 */
public interface WhiteboardDao {

    /**
     * Returns a list of hosts
     *
     * @param HostSearchCriteria r
     * @return
     */
    ProcSeq getProcs(HostInterface h);

    /**
     * Returns a list of hosts
     *
     * @param HostSearchCriteria r
     * @return
     */
    HostSeq getHosts(HostSearch  r);

    /**
     * Returns a list of jobs
     *
     * @param JobSearchCriteria r
     * @return
     */
    JobSeq getJobs(JobSearch  r);

    /**
     * Returns a list of job names
     *
     * @param JobSearchCriteria r
     * @return
     */

    List<String> getJobNames(JobSearch  r);

    /**
     * Returns the comments for the specified job
     *
     * @param job
     * @return
     */
    CommentSeq getComments(JobInterface j);

    /**
     * Returns the comments for the specified host
     *
     * @param job
     * @return
     */
    CommentSeq getComments(HostInterface h);

    /**
     * returns the host a proc is part of
     *
     * @param p
     * @return
     */
    Host getHost(String id);

    /**
     * returns the host by name
     *
     * @param name
     * @return
     */
    Host findHost(String name);

    /**
     * Return a dependency by its unique id
     *
     * @param id
     * @return
     */
    Depend getDepend(String id);

    /**
     * Returns a list of all dependencies this job is involved with.
     *
     * @param job
     * @return
     */
    DependSeq getDepends(JobInterface job);

    /**
     * Returns an array of depends that depend on the specified job.
     *
     * @param job
     * @return
     */
    DependSeq getWhatDependsOnThis(JobInterface job);

    /**
     * Returns an array of depends that depend on the specified layer.
     *
     * @param layer
     * @return
     */
    DependSeq getWhatDependsOnThis(LayerInterface layer);

    /**
     * Returns an array of depends that depend on the specified job.
     *
     * @param frame
     * @return
     */
    DependSeq getWhatDependsOnThis(FrameInterface frame);

    /**
     * Returns an array of depends that the specified job is waiting on.
     *
     * @param job
     * @return
     */
    DependSeq getWhatThisDependsOn(JobInterface job);

    /**
     * Returns an array of depends that the specified layer is waiting on.
     *
     * @param layer
     * @return
     */
    DependSeq getWhatThisDependsOn(LayerInterface layer);

    /**
     * Returns an array of depends that the specified frame is waiting on.
     *
     * @param frame
     * @return
     */
    DependSeq getWhatThisDependsOn(FrameInterface frame);

    /**
     * Returns the specified dependency
     *
     * @param depend
     * @return
     */
    Depend getDepend(DependInterface depend);

    Filter findFilter(String show, String name);

    Filter findFilter(ShowInterface show, String name);

    Filter getFilter(FilterInterface filter);

    List<Matcher> getMatchers(FilterInterface filter);

    Matcher getMatcher(MatcherInterface matcher);

    List<Action> getActions(FilterInterface filter);

    Action getAction(ActionInterface action);

    /**
     * Returns the frame by unique ID
     *
     * @param p
     * @return
     */
    Frame getFrame(String id);

    /**
     * Returns a list of filters by show
     *
     * @param show
     * @return
     */

    FilterSeq getFilters(ShowInterface show);

    /**
     * Frame search
     *
     * @param r
     * @return
     */
    FrameSeq getFrames(FrameSearch r);

    /**
     * Returns a list of layers for the specified job.
     *
     * @param  job
     * @return LayerSeq
     */
    LayerSeq getLayers(JobInterface job);

    /**
     * Returns a layer from its unique ID
     *
     * @param  id
     * @return Layer
     */
    Layer getLayer(String id);

    /**
     *
     * @param group
     * @return
     */
    JobSeq getJobs(GroupInterface group);

    /**
     * Finds an active job record based on the name
     *
     * @param name
     * @return
     */
    Job findJob(String name);

    /**
     * Gets an active job based on the Id
     *
     * @param id
     * @return
     */
    Job getJob(String id);

    /**
     * returns a subscription by its id
     *
     * @return Subscription
     */
    Subscription getSubscription(String id);

    /**
     * Find subscription using the show, facility, and alloc name.
     *
     * @param show
     * @param facility
     * @param alloc
     * @return
     */
    Subscription findSubscription(String show, String alloc);

    /**
     * returns a list of subscriptions
     *
     * @param req
     * @return List<Subscription>
     */
    SubscriptionSeq getSubscriptions(ShowInterface show);

    /**
     * returns all subscriptions on the specified allocation
     *
     * @param alloc
     * @return
     */
    SubscriptionSeq getSubscriptions(AllocationInterface alloc);

    /**
     * returns a show by Id.
     *
     * @param req
     * @return Show
     */
    Show getShow(String id);

    /**
     * returns a show by its name.
     *
     * @param name
     * @return
     */
    Show findShow(String name);

    /**
     *
     * return a list of shows rom a whiteboard request
     *
     * @param req
     * @return
     */
    ShowSeq getShows();

    /**
     * returns a show by Id.
     *
     * @param req
     * @return Show
     */
    Allocation getAllocation(String id);

    /**
     * returns a show by its name.
     *
     * @param name
     * @return
     */
    Allocation findAllocation(String name);

    /**
     *
     * return the current list of allocations
     *
     * @param req
     * @return
     */
    List<Allocation> getAllocations();

    /**
    *
    * return the current list of allocations
    *
    * @param req
    * @return
    */
   List<Allocation> getAllocations(com.imageworks.spcue.FacilityInterface facility);


    /**
     *
     * @param show
     * @return
     */
    Group getRootGroup(ShowInterface show);

    /**
     *
     * @param id
     * @return Group
     */
    Group getGroup(String id);

    /**
     * Finds a group by show name and group name
     *
     * @param show
     * @param group
     * @return
     */
    Group findGroup(String show, String group);

    /**
     *
     *
     * @param show
     * @return GroupSeq
     */
    GroupSeq getGroups(ShowInterface show);

    /**
     *
     * @param group
     * @return
     */
    GroupSeq getGroups(GroupInterface group);


    /**
     *
     * @param job
     * @param layer
     * @return
     */
    Layer findLayer(String job, String layer);

    /**
     *
     * @param job
     * @param layer
     * @param frame
     * @return
     */
    Frame findFrame(String job, String layer, int frame);


    /**
     * returns an UpdatedFrameCheckResult which contains an array of updated frames.
     *
     * @param job
     * @param layers
     * @param lastUpdate
     * @return
     */
    UpdatedFrameCheckResult getUpdatedFrames(JobInterface job,
                                             List<LayerInterface> layers, int lastUpdate);

    /**
     *
     * @param show
     * @return
     */
    DepartmentSeq getDepartments (ShowInterface show);

    /**
     *
     * @param show
     * @param name
     * @return
     */
    Department getDepartment(ShowInterface show, String name);

    /**
     * Returns a list of available department names
     *
     * @return
     */
    List<String> getDepartmentNames();

    /**
     *
     * @return
     */
    Task getTask(ShowInterface show, DepartmentInterface dept, String shot);

    /**
     *
     * @param show
     * @param dept
     * @return
     */
    List<Task> getTasks(ShowInterface show, DepartmentInterface dept);

    /**
     * Returns procs from a ProcSearch criteria.
     *
     * @param p
     * @return
     */
    ProcSeq getProcs(ProcSearch p);

    /**
     * Return the Ice representation of the given AbstractDepend.
     *
     * @param depend
     * @return
     */
    Depend getDepend(AbstractDepend depend);

    /**
     * Return the Host record for the given Deed.
     *
     * @param deed
     * @return
     */
    Host getHost(DeedEntity deed);

    /**
     * Return the Owner of the given Deed.
     *
     * @param deed
     * @return
     */
    Owner getOwner(DeedEntity deed);

    /**
     * Return a list of all Deeds controlled by the given Owner.
     *
     * @param owner
     * @return
     */
    DeedSeq getDeeds(OwnerEntity owner);

    /**
     * Return a list of all Hosts controlled by the given Owner.
     *
     * @param owner
     * @return
     */
    HostSeq getHosts(OwnerEntity owner);

    /**
     * Return the Owner of the given host.
     *
     * @param host
     * @return
     */
    Owner getOwner(HostInterface host);

    /**
     * Return the Deed for the given Host.
     *
     * @param host
     * @return
     */
    Deed getDeed(HostInterface host);

    /**
     * Return the owner by name.
     *
     * @param name
     * @return
     */
    Owner getOwner(String name);

    /**
     * Return a list of owners by show.
     *
     * @param show
     * @return
     */
    List<Owner> getOwners(ShowInterface show);

    /**
     * Return a list of Deeds by show.
     *
     * @param show
     * @return
     */
    DeedSeq getDeeds(ShowInterface show);

    /**
     * Return a RenderPartion from its associated LocalHostAssignment.
     *
     * @param l
     * @return
     */
    RenderPartition getRenderPartition(LocalHostAssignment l);

    /**
     * Return a list or RenderPartition for the given Host.
     *
     * @param host
     * @return
     */
    RenderPartitionSeq getRenderPartitions(HostInterface host);

    /**
     * Return a facility by name or id.
     *
     * @param name
     * @return
     */
    Facility getFacility(String name);

    /**
     * Return the full list of facilities.
     *
     * @return
     */
    List<Facility> getFacilities();

    /**
     * Return a list of all active shows.
     *
     * @return
     */
    ShowSeq getActiveShows();

    /**
     * Return the given service.
     *
     * @param id
     * @return
     */
    Service getService(String id);

    /**
     * Return the list of cluster wide service defaults.
     *
     * @return
     */
    ServiceSeq getDefaultServices();

    /**
     * Return the list of service overrides for a particular show.
     *
     * @param show
     * @return
     */
    List<ServiceOverride> getServiceOverrides(ShowInterface show);

    /**
     * Return the given show override.
     *
     * @param show
     * @param name
     * @return
     */
    ServiceOverride getServiceOverride(ShowInterface show, String name);

    /**
     * Find a service by name.
     *
     * @param name
     * @return
     */
    Service findService(String name);
}

