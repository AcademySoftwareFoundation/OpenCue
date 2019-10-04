
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

import com.imageworks.spcue.ActionInterface;
import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.DeedEntity;
import com.imageworks.spcue.DepartmentInterface;
import com.imageworks.spcue.DependInterface;
import com.imageworks.spcue.FacilityInterface;
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
import com.imageworks.spcue.dao.criteria.FrameSearchInterface;
import com.imageworks.spcue.dao.criteria.HostSearchInterface;
import com.imageworks.spcue.dao.criteria.JobSearchInterface;
import com.imageworks.spcue.dao.criteria.ProcSearchInterface;
import com.imageworks.spcue.depend.AbstractDepend;
import com.imageworks.spcue.grpc.comment.CommentSeq;
import com.imageworks.spcue.grpc.department.Department;
import com.imageworks.spcue.grpc.department.DepartmentSeq;
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
import com.imageworks.spcue.grpc.job.UpdatedFrameCheckResult;
import com.imageworks.spcue.grpc.limit.Limit;
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
 * @category DAO
 */
public interface WhiteboardDao {

    /**
     * Returns a list of hosts
     *
     * @param h HostInterface
     * @return ProcSeq
     */
    ProcSeq getProcs(HostInterface h);

    /**
     * Returns a list of hosts
     *
     * @param r HostSearchInterface
     * @return HostSeq
     */
    HostSeq getHosts(HostSearchInterface r);

    /**
     * Returns a list of jobs
     *
     * @param r JobSearchInterface
     * @return JobSeq
     */
    JobSeq getJobs(JobSearchInterface  r);

    /**
     * Returns a list of job names
     *
     * @param r JobSearchInterface
     * @return List of Strings
     */

    List<String> getJobNames(JobSearchInterface  r);

    /**
     * Returns the comments for the specified job
     *
     * @param j JobInterface
     * @return CommentSeq
     */
    CommentSeq getComments(JobInterface j);

    /**
     * Returns the comments for the specified host
     *
     * @param h HostInterface
     * @return CommentSeq
     */
    CommentSeq getComments(HostInterface h);

    /**
     * returns the host a proc is part of
     *
     * @param id String
     * @return Host
     */
    Host getHost(String id);

    /**
     * returns the host by name
     *
     * @param name String
     * @return Host
     */
    Host findHost(String name);

    /**
     * Return a dependency by its unique id
     *
     * @param id String
     * @return Depend
     */
    Depend getDepend(String id);

    /**
     * Returns a list of all dependencies this job is involved with.
     *
     * @param job JobInterface
     * @return DependSeq
     */
    DependSeq getDepends(JobInterface job);

    /**
     * Returns an array of depends that depend on the specified job.
     *
     * @param job JobInterface
     * @return DependSeq
     */
    DependSeq getWhatDependsOnThis(JobInterface job);

    /**
     * Returns an array of depends that depend on the specified layer.
     *
     * @param layer LayerInterface
     * @return DependSeq
     */
    DependSeq getWhatDependsOnThis(LayerInterface layer);

    /**
     * Returns an array of depends that depend on the specified job.
     *
     * @param frame FrameInterface
     * @return DependSeq
     */
    DependSeq getWhatDependsOnThis(FrameInterface frame);

    /**
     * Returns an array of depends that the specified job is waiting on.
     *
     * @param job JobInterface
     * @return DependSeq
     */
    DependSeq getWhatThisDependsOn(JobInterface job);

    /**
     * Returns an array of depends that the specified layer is waiting on.
     *
     * @param layer LayerInterface
     * @return DependSeq
     */
    DependSeq getWhatThisDependsOn(LayerInterface layer);

    /**
     * Returns an array of depends that the specified frame is waiting on.
     *
     * @param frame FrameInterface
     * @return DependSeq
     */
    DependSeq getWhatThisDependsOn(FrameInterface frame);

    /**
     * Returns the specified dependency
     *
     * @param depend DependInterface
     * @return Depend
     */
    Depend getDepend(DependInterface depend);

    Filter findFilter(String show, String name);

    Filter findFilter(ShowInterface show, String name);

    Filter getFilter(FilterInterface filter);

    MatcherSeq getMatchers(FilterInterface filter);

    Matcher getMatcher(MatcherInterface matcher);

    ActionSeq getActions(FilterInterface filter);

    Action getAction(ActionInterface action);

    /**
     * Returns the frame by unique ID
     *
     * @param id String
     * @return Frame
     */
    Frame getFrame(String id);

    /**
     * Returns a list of filters by show
     *
     * @param show ShowInterface
     * @return FilterSeq
     */

    FilterSeq getFilters(ShowInterface show);

    /**
     * Frame search
     *
     * @param r FrameSearchInterface
     * @return FrameSeq
     */
    FrameSeq getFrames(FrameSearchInterface r);

    /**
     * Returns a list of layers for the specified job.
     *
     * @param  job JobInterface
     * @return LayerSeq
     */
    LayerSeq getLayers(JobInterface job);

    /**
     * Returns a layer from its unique ID
     *
     * @param  id String
     * @return Layer
     */
    Layer getLayer(String id);

    /**
     * Returns a list of limits for the specified layer.
     *
     * @param  id String
     * @return Layer
     */
    List<Limit> getLimits(LayerInterface layer);

    /**
     *
     * @param group GroupInterface
     * @return JobSeq
     */
    JobSeq getJobs(GroupInterface group);

    /**
     * Finds an active job record based on the name
     *
     * @param name String
     * @return Job
     */
    Job findJob(String name);

    /**
     * Gets an active job based on the Id
     *
     * @param id String
     * @return Job
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
     * @param show String
     * @param alloc String
     * @return Subscription
     */
    Subscription findSubscription(String show, String alloc);

    /**
     * returns a list of subscriptions
     *
     * @param show ShowInterface
     * @return SubscriptionSeq
     */
    SubscriptionSeq getSubscriptions(ShowInterface show);

    /**
     * returns all subscriptions on the specified allocation
     *
     * @param alloc AllocationInterface
     * @return SubscriptionSeq
     */
    SubscriptionSeq getSubscriptions(AllocationInterface alloc);

    /**
     * returns a show by Id.
     *
     * @param id String
     * @return Show
     */
    Show getShow(String id);

    /**
     * returns a show by its name.
     *
     * @param name String
     * @return Show
     */
    Show findShow(String name);

    /**
     *
     * return a list of shows from a whiteboard request
     *
     * @return ShowSeq
     */
    ShowSeq getShows();

    /**
     * returns an allocation by Id.
     *
     * @param id String
     * @return Allocation
     */
    Allocation getAllocation(String id);

    /**
     * returns a show by its name.
     *
     * @param name String
     * @return Allocation
     */
    Allocation findAllocation(String name);

    /**
     *
     * return the current list of allocations
     *
     * @return List of Allocations
     */
    AllocationSeq getAllocations();

    /**
    *
    * return the current list of allocations
    *
    * @param facility FacilityInterface
    * @return List of Allocations
    */
   AllocationSeq getAllocations(FacilityInterface facility);


    /**
     *
     * @param show ShowInterface
     * @return Group
     */
    Group getRootGroup(ShowInterface show);

    /**
     *
     * @param id String
     * @return Group
     */
    Group getGroup(String id);

    /**
     * Finds a group by show name and group name
     *
     * @param show  String
     * @param group String
     * @return Group
     */
    Group findGroup(String show, String group);

    /**
     *
     *
     * @param show ShowInterface
     * @return GroupSeq
     */
    GroupSeq getGroups(ShowInterface show);

    /**
     *
     * @param group GroupInterface
     * @return GroupSeq
     */
    GroupSeq getGroups(GroupInterface group);


    /**
     *
     * @param job   String
     * @param layer String
     * @return Layer
     */
    Layer findLayer(String job, String layer);

    /**
     *
     * @param job   String
     * @param layer String
     * @param frame int
     * @return Frame
     */
    Frame findFrame(String job, String layer, int frame);


    /**
     * returns an UpdatedFrameCheckResult which contains an array of updated frames.
     *
     * @param job        JobInterface
     * @param layers     List of LayerInterfaces
     * @param lastUpdate int
     * @return UpdatedFrameCheckResult
     */
    UpdatedFrameCheckResult getUpdatedFrames(JobInterface job,
                                             List<LayerInterface> layers, int lastUpdate);

    /**
     *
     * @param show ShowInterface
     * @return DepartmentSeq
     */
    DepartmentSeq getDepartments (ShowInterface show);

    /**
     *
     * @param show ShowInterface
     * @param name String
     * @return Department
     */
    Department getDepartment(ShowInterface show, String name);

    /**
     * Returns a list of available department names
     *
     * @return List of Strings
     */
    List<String> getDepartmentNames();

    /**
     *
     * @param show ShowInterface
     * @param dept DepartmentInterface
     * @param shot String
     * @return Task
     */
    Task getTask(ShowInterface show, DepartmentInterface dept, String shot);

    /**
     *
     * @param show ShowInterface
     * @param dept DepartmentInterface
     * @return List of Tasks
     */
    TaskSeq getTasks(ShowInterface show, DepartmentInterface dept);

    /**
     * Returns procs from a ProcSearchInterface criteria.
     *
     * @param p ProcSearchInterface
     * @return ProcSeq
     */
    ProcSeq getProcs(ProcSearchInterface p);

    /**
     * Return the grpc representation of the given AbstractDepend.
     *
     * @param depend AbstractDepend
     * @return Depend
     */
    Depend getDepend(AbstractDepend depend);

    /**
     * Return the Host record for the given Deed.
     *
     * @param deed DeedEntity
     * @return Host
     */
    Host getHost(DeedEntity deed);

    /**
     * Return the Owner of the given Deed.
     *
     * @param deed DeedEntity
     * @return Owner
     */
    Owner getOwner(DeedEntity deed);

    /**
     * Return a list of all Deeds controlled by the given Owner.
     *
     * @param owner OwnerEntity
     * @return DeedSeq
     */
    DeedSeq getDeeds(OwnerEntity owner);

    /**
     * Return a list of all Hosts controlled by the given Owner.
     *
     * @param owner OwnerEntity
     * @return HostSeq
     */
    HostSeq getHosts(OwnerEntity owner);

    /**
     * Return the Owner of the given host.
     *
     * @param host HostInterface
     * @return Owner
     */
    Owner getOwner(HostInterface host);

    /**
     * Return the Deed for the given Host.
     *
     * @param host HostInterface
     * @return Deed
     */
    Deed getDeed(HostInterface host);

    /**
     * Return the owner by name.
     *
     * @param name String
     * @return Owner
     */
    Owner getOwner(String name);

    /**
     * Return a list of owners by show.
     *
     * @param show ShowInterface
     * @return List of Owners
     */
    List<Owner> getOwners(ShowInterface show);

    /**
     * Return a list of Deeds by show.
     *
     * @param show ShowInterface
     * @return DeedSeq
     */
    DeedSeq getDeeds(ShowInterface show);

    /**
     * Return a RenderPartion from its associated LocalHostAssignment.
     *
     * @param l LocalHostAssignment
     * @return RenderPartition
     */
    RenderPartition getRenderPartition(LocalHostAssignment l);

    /**
     * Return a list or RenderPartition for the given Host.
     *
     * @param host HostInterface
     * @return RenderPartitionSeq
     */
    RenderPartitionSeq getRenderPartitions(HostInterface host);

    /**
     * Return a facility by name or id.
     *
     * @param name String
     * @return Facility
     */
    Facility getFacility(String name);

    /**
     * Return the full list of facilities.
     *
     * @return List of Facilities
     */
    FacilitySeq getFacilities();

    /**
     * Return a list of all active shows.
     *
     * @return ShowSeq
     */
    ShowSeq getActiveShows();

    /**
     * Return the given service.
     *
     * @param id String
     * @return Service
     */
    Service getService(String id);

    /**
     * Return the list of cluster wide service defaults.
     *
     * @return ServiceSeq
     */
    ServiceSeq getDefaultServices();

    /**
     * Return the list of service overrides for a particular show.
     *
     * @param show ShowInterface
     * @return List of ServiceOverrides
     */
    ServiceOverrideSeq getServiceOverrides(ShowInterface show);

    /**
     * Return the given show override.
     *
     * @param show ShowInterface
     * @param name String
     * @return ServiceOverride
     */
    ServiceOverride getServiceOverride(ShowInterface show, String name);

    /**
     * Find a service by name.
     *
     * @param name String
     * @return Service
     */
    Service findService(String name);

    /**
     * Find a limit by name.
     *
     * @param name String
     * @return Service
     */
    Limit findLimit(String name);

    /**
     * Return a service by ID.
     *
     * @param id String
     * @return Limit
     */
    Limit getLimit(String id);

    /**
     * Returns a list of all limits.
     *
     * @param  id String
     * @return Layer
     */
    List<Limit> getLimits();
}

