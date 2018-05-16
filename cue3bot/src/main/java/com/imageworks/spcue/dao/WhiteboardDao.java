
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

import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.CueClientIce.*;
import com.imageworks.spcue.dao.criteria.FrameSearch;
import com.imageworks.spcue.dao.criteria.HostSearch;
import com.imageworks.spcue.dao.criteria.JobSearch;
import com.imageworks.spcue.dao.criteria.ProcSearch;
import com.imageworks.spcue.depend.AbstractDepend;

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
    List<Proc> getProcs(com.imageworks.spcue.Host h);

    /**
     * Returns a list of hosts
     *
     * @param HostSearchCriteria r
     * @return
     */
    List<Host> getHosts(HostSearch  r);

    /**
     * Returns a list of jobs
     *
     * @param JobSearchCriteria r
     * @return
     */
    List<Job> getJobs(JobSearch  r);

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
    List<Comment> getComments(com.imageworks.spcue.Job j);

    /**
     * Returns the comments for the specified host
     *
     * @param job
     * @return
     */
    List<Comment> getComments(com.imageworks.spcue.Host h);

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
    List<Depend> getDepends(com.imageworks.spcue.Job job);

    /**
     * Returns an array of depends that depend on the specified job.
     *
     * @param job
     * @return
     */
    List<Depend> getWhatDependsOnThis(com.imageworks.spcue.Job job);

    /**
     * Returns an array of depends that depend on the specified layer.
     *
     * @param layer
     * @return
     */
    List<Depend> getWhatDependsOnThis(com.imageworks.spcue.Layer layer);

    /**
     * Returns an array of depends that depend on the specified job.
     *
     * @param frame
     * @return
     */
    List<Depend> getWhatDependsOnThis(com.imageworks.spcue.Frame frame);

    /**
     * Returns an array of depends that the specified job is waiting on.
     *
     * @param job
     * @return
     */
    List<Depend> getWhatThisDependsOn(com.imageworks.spcue.Job job);

    /**
     * Returns an array of depends that the specified layer is waiting on.
     *
     * @param layer
     * @return
     */
    List<Depend> getWhatThisDependsOn(com.imageworks.spcue.Layer layer);

    /**
     * Returns an array of depends that the specified frame is waiting on.
     *
     * @param frame
     * @return
     */
    List<Depend> getWhatThisDependsOn(com.imageworks.spcue.Frame frame);

    /**
     * Returns the specified dependency
     *
     * @param depend
     * @return
     */
    Depend getDepend(com.imageworks.spcue.Depend depend);

    Filter findFilter(String show, String name);

    Filter findFilter(com.imageworks.spcue.Show show, String name);

    Filter getFilter(com.imageworks.spcue.Filter filter);

    List<Matcher> getMatchers(com.imageworks.spcue.Filter filter);

    Matcher getMatcher(com.imageworks.spcue.Matcher matcher);

    List<Action> getActions(com.imageworks.spcue.Filter filter);

    Action getAction(com.imageworks.spcue.Action action);

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

    List<Filter> getFilters(com.imageworks.spcue.Show show);

    /**
     * Frame search
     *
     * @param job
     * @param r
     * @return
     */
    List<Frame> getFrames(FrameSearch r);

    /**
     * Returns a list of layers for the specified job.
     *
     * @param JobDetail job
     * @return List<Layer>
     */
    List<Layer> getLayers(com.imageworks.spcue.Job job);

    /**
     * Returns a layer from its unique ID
     *
     * @param JobDetail job
     * @return List<Layer>
     */
    Layer getLayer(String id);

    /**
     *
     * @param group
     * @return
     */
    List<Job> getJobs(com.imageworks.spcue.Group group);

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
    List<Subscription> getSubscriptions(com.imageworks.spcue.Show show);

    /**
     * returns all subscriptions on the specified allocation
     *
     * @param alloc
     * @return
     */
    List<Subscription> getSubscriptions(com.imageworks.spcue.Allocation alloc);

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
    List<Show> getShows();

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
   List<Allocation> getAllocations(com.imageworks.spcue.Facility facility);


    /**
     *
     * @param show
     * @return
     */
    Group getRootGroup(com.imageworks.spcue.Show show);

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
     * @param req
     * @return List<Group>
     */
    List<Group> getGroups(com.imageworks.spcue.Show show);

    /**
     *
     * @param group
     * @return
     */
    List<Group> getGroups(com.imageworks.spcue.Group group);


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
    UpdatedFrameCheckResult getUpdatedFrames(com.imageworks.spcue.Job job,
            List<com.imageworks.spcue.Layer> layers, int lastUpdate);

    /**
     *
     * @param show
     * @return
     */
    List<Department> getDepartments (com.imageworks.spcue.Show show);

    /**
     *
     * @param show
     * @param name
     * @return
     */
    Department getDepartment(com.imageworks.spcue.Show show, String name);

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
    Task getTask(com.imageworks.spcue.Show show, com.imageworks.spcue.Department dept, String shot);

    /**
     *
     * @param show
     * @param dept
     * @return
     */
    List<Task> getTasks(com.imageworks.spcue.Show show, com.imageworks.spcue.Department dept);

    /**
     * Returns procs from a ProcSearch criteria.
     *
     * @param p
     * @return
     */
    List<Proc> getProcs(ProcSearch p);

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
    Host getHost(com.imageworks.spcue.Deed deed);

    /**
     * Return the Owner of the given Deed.
     *
     * @param deed
     * @return
     */
    Owner getOwner(com.imageworks.spcue.Deed deed);

    /**
     * Return a list of all Deeds controlled by the given Owner.
     *
     * @param owner
     * @return
     */
    List<Deed> getDeeds(com.imageworks.spcue.Owner owner);

    /**
     * Return a list of all Hosts controlled by the given Owner.
     *
     * @param owner
     * @return
     */
    List<Host> getHosts(com.imageworks.spcue.Owner owner);

    /**
     * Return the Owner of the given host.
     *
     * @param host
     * @return
     */
    Owner getOwner(com.imageworks.spcue.Host host);

    /**
     * Return the Deed for the given Host.
     *
     * @param host
     * @return
     */
    Deed getDeed(com.imageworks.spcue.Host host);

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
    List<Owner> getOwners(com.imageworks.spcue.Show show);

    /**
     * Return a list of Deeds by show.
     *
     * @param show
     * @return
     */
    List<Deed> getDeeds(com.imageworks.spcue.Show show);

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
    List<RenderPartition> getRenderPartitions(com.imageworks.spcue.Host host);

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
    List<Show> getActiveShows();

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
    List<Service> getDefaultServices();

    /**
     * Return the list of service overrides for a particular show.
     *
     * @param show
     * @return
     */
    List<ServiceOverride> getServiceOverrides(com.imageworks.spcue.Show show);

    /**
     * Return the given show override.
     *
     * @param show
     * @param name
     * @return
     */
    ServiceOverride getServiceOverride(com.imageworks.spcue.Show show, String name);

    /**
     * Find a service by name.
     *
     * @param name
     * @return
     */
    Service findService(String name);
}

