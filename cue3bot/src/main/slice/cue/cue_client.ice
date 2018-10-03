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

#ifndef WB_ICE
#define WB_ICE

#include <spi_exceptions.ice>
#include <spi_search_criteria.ice>
#include <spi_types.ice>
#include <cue_types.ice>

[["java:package:com.imageworks.spcue"]]
[["python:package:cue"]]

/*
* CueClientIce contains the entire Cue3 server side API.
*
* Units:
* Memory is measured in KB unless otherwise named.
* Time is measured in epoch seconds.
* Cores are measured in decimal cores.
*
* Other Vocabulary.
* MCP - temporary partition on all SPI machines.
* Swap - swap partition.
*
*/
module CueClientIce {

    /*
    * Interface Definitions
    */
    interface MatcherInterface;
    interface FilterInterface;
    interface ActionInterface;
    interface JobInterface;
    interface LayerInterface;
    interface FrameInterface;
    interface HostInterface;
    interface AllocationInterface;
    interface SubscriptionInterface;
    interface ShowInterface;
    interface GroupInterface;
    interface DependInterface;
    interface ProcInterface;
    interface CommentInterface;
    interface TaskInterface;
    interface OwnerInterface;
    interface DeedInterface;
    interface FacilityInterface;
    interface ServiceInterface;
    interface ServiceOverrideInterface;
    /*
    * Interface Sequences
    */

    ["java:type:java.util.ArrayList<GroupInterfacePrx>:java.util.List<GroupInterfacePrx>"]
    sequence<GroupInterface*> GroupProxySeq;

    ["java:type:java.util.ArrayList<JobInterfacePrx>:java.util.List<JobInterfacePrx>"]
    sequence<JobInterface*> JobProxySeq;

    ["java:type:java.util.ArrayList<LayerInterfacePrx>:java.util.List<LayerInterfacePrx>"]
    sequence<LayerInterface*> LayerProxySeq;

    ["java:type:java.util.ArrayList<AllocationInterfacePrx>:java.util.List<AllocationInterfacePrx>"]
    sequence<AllocationInterface*> AllocationProxySeq;

    ["java:type:java.util.ArrayList<SubscriptionInterfacePrx>:java.util.List<SubscriptionInterfacePrx>"]
    sequence<SubscriptionInterface*> SubscriptionProxySeq;

    ["java:type:java.util.ArrayList<HostInterfacePrx>:java.util.List<HostInterfacePrx>"]
    sequence<HostInterface*> HostProxySeq;

    ["java:type:java.util.ArrayList<ProcInterfacePrx>:java.util.List<ProcInterfacePrx>"]
    sequence<ProcInterface*> ProcProxySeq;

    ["java:type:java.util.ArrayList<DependInterfacePrx>:java.util.List<DependInterfacePrx>"]
    sequence<DependInterface*> DependProxySeq;

    ["java:type:java.util.ArrayList<ShowInterfacePrx>:java.util.List<ShowInterfacePrx>"]
    sequence<ShowInterface*> ShowProxySeq;

    /*
    * Class Definitions and sequences
    */

    class Group;
    ["java:type:java.util.ArrayList<Group>:java.util.List<Group>"]
    sequence<Group> GroupSeq;

    class NestedGroup;
    ["java:type:java.util.ArrayList<NestedGroup>:java.util.List<NestedGroup>"]
    sequence<NestedGroup> NestedGroupSeq;

    class Job;
    ["java:type:java.util.ArrayList<Job>:java.util.List<Job>"]
    sequence<Job> JobSeq;

    class NestedJob;
    ["java:type:java.util.ArrayList<NestedJob>:java.util.List<NestedJob>"]
    sequence<NestedJob> NestedJobSeq;

    class Allocation;
    ["java:type:java.util.ArrayList<Allocation>:java.util.List<Allocation>"]
    sequence<Allocation> AllocationSeq;

    class Subscription;
    ["java:type:java.util.ArrayList<Subscription>:java.util.List<Subscription>"]
    sequence<Subscription> SubscriptionSeq;

    class Show;
    ["java:type:java.util.ArrayList<Show>:java.util.List<Show>"]
    sequence<Show> ShowSeq;

    class Layer;
    ["java:type:java.util.ArrayList<Layer>:java.util.List<Layer>"]
    sequence<Layer> LayerSeq;

    class Frame;
    ["java:type:java.util.ArrayList<Frame>:java.util.List<Frame>"]
    sequence<Frame> FrameSeq;

    class Host;
    ["java:type:java.util.ArrayList<Host>:java.util.List<Host>"]
    sequence<Host> HostSeq;

    class NestedHost;
    ["java:type:java.util.ArrayList<NestedHost>:java.util.List<NestedHost>"]
    sequence<NestedHost> NestedHostSeq;

    class Proc;
    ["java:type:java.util.ArrayList<Proc>:java.util.List<Proc>"]
    sequence<Proc> ProcSeq;

    class NestedProc;
    ["java:type:java.util.ArrayList<NestedProc>:java.util.List<NestedProc>"]
    sequence<NestedProc> NestedProcSeq;

    class Filter;
    ["java:type:java.util.ArrayList<Filter>:java.util.List<Filter>"]
    sequence<Filter> FilterSeq;

    class Matcher;
    ["java:type:java.util.ArrayList<Matcher>:java.util.List<Matcher>"]
    sequence<Matcher> MatcherSeq;

    class Action;
    ["java:type:java.util.ArrayList<Action>:java.util.List<Action>"]
    sequence<Action> ActionSeq;

    class Depend;
    ["java:type:java.util.ArrayList<Depend>:java.util.List<Depend>"]
    sequence<Depend> DependSeq;

    class Comment;
    ["java:type:java.util.ArrayList<Comment>:java.util.List<Comment>"]
    sequence<Comment> CommentSeq;

    class Task;
    ["java:type:java.util.ArrayList<Task>:java.util.List<Task>"]
    sequence<Task> TaskSeq;

    class Department;
    ["java:type:java.util.ArrayList<Department>:java.util.List<Department>"]
    sequence<Department> DepartmentSeq;

    class Service;
    ["java:type:java.util.ArrayList<Service>:java.util.List<Service>"]
    sequence<Service> ServiceSeq;

    class ServiceOverride;
    ["java:type:java.util.ArrayList<ServiceOverride>:java.util.List<ServiceOverride>"]
    sequence<ServiceOverride> ServiceOverrideSeq;

    /**
    * A structure for storing service data.
    **/
    struct ServiceData {

        /**
        * The name of the service.
        **/
        string name;

        /**
        * Whether or not the service is threadable.
        **/
        bool threadable;

        /**
        * The default minimum core value for the given service measured in
        * core units.
        **/
        int minCores;

        /**
        * The default maximum value for the given service measured in
        * core units.
        */ 
        int maxCores;

        /**
        * The default minimum memory value for the given service.
        **/
        int minMemory;

        /**
        * The default minimum gpu memory value for the given service.
        **/
        int minGpu;

        /**
        * The default tag sets for the given service.
        **/
        CueIce::StringSeq tags;
    };

    /**
    * Interface for modifying services.
    **/
    interface ServiceInterface {

        idempotent void delete()
          throws ::SpiIce::SpiIceException;

        idempotent void update(ServiceData data)
          throws ::SpiIce::SpiIceException;
    };

    /**
    * Interface for modifying services.
    **/
    interface ServiceOverrideInterface {

        idempotent void delete()
          throws ::SpiIce::SpiIceException;

        idempotent void update(ServiceData data)
          throws ::SpiIce::SpiIceException;
    };

    /**
    * Class for storing service info.
    **/
    class Service {
        ServiceData data;
        ServiceInterface *proxy;
    };

    /**
    * Class for storing service info.
    **/
    class ServiceOverride {
        ServiceData data;
        ServiceOverrideInterface *proxy;
    };

    /**
    * A base class for search criteria
    **/
    class SearchCriteria {

        /**
        * The offset of the first result.  This
        * defaults to 1.
        **/
        int firstResult;

        /**
        * The maximum number of results.  An empty
        * option indicates no result limit.
        **/
        SpiIce::IntOpt maxResults;
    };


    /**
    * Structure for holding comment data.
    **/
    struct CommentData {
        /**
        * The time the comment was created, epoch seconds.
        **/
        int timestamp;

        /**
        * Name of the user who made the comment.
        **/
        string user;

        /**
        * The subject of the comment.
        **/
        string subject;

        /**
        * The body of the comment.
        **/
        string message;
    };

    /**
    * The comment server side interface.
    **/
    interface CommentInterface {
        /**
        * Delete specified comment
        **/
        idempotent void delete()
            throws ::SpiIce::SpiIceException;

        /**
        * Saves the current comment.
        **/
        idempotent void save(CommentData comment)
            throws ::SpiIce::SpiIceException;
    };

    /**
    * The Comment class contains comment data afor any entity that supports
    * commenting.  Currently these are [Job] and [Host].
    * Contains a [CommentData] and [CommentInterface].
    **/
    class Comment {
        CommentData data;
        CommentInterface *proxy;
    };

    /**
    * The ActionData struct provides action information.
    **/
    struct ActionData {
        /**
        * The type of action.  See [CueIce::ActionType]
        **/
        CueIce::ActionType type;

        /**
        * The type of value associated with the action.
        * See [CueIce::ActionValueType]
        **/
        CueIce::ActionValueType valueType;

        /**
        * If the action involves a group type, this value must be set.
        **/
        GroupInterface *groupValue;

        /**
        * If the action involves a string type, this value must be set.
        **/
        string stringValue;

        /**
        * If the action involves a integer type, this value must be set.
        **/
        int integerValue;

        /**
        * If the action involves a float type, this value must be set.
        **/
        float floatValue;

        /**
        * If the action involves a boolean type, this value must be set.
        **/
        bool booleanValue;
    };

    /**
    * The MatcherData struct contains information about a matcher.  An example
    * of a matcher would be:
    * Subject: JobName Type: contains  Input: chambers
    * That can be read as "If a job's name contains 'chambers'"
    **/
    struct MatcherData {
        /**
        * The subject of the matcher, this is what the matcher is acting on.
        * See [CueIce::MatchSubject].
        **/
        CueIce::MatchSubject subject;

        /**
        * The type of matcher.  This describes the operation the matcher is
        * going to execute.  See [CueIce::MatchType].
        **/
        CueIce::MatchType type;

        /**
        * The input that is being passed into the matcher.
        **/
        string input;
    };

    /**
    * The FilterData struct contains data for a Cue filters.
    **/
    struct FilterData {
        /**
        * The name of the filter.
        **/
        string name;

        /**
        * The type of filter.  See [CueIce::FilterType]
        **/
        CueIce::FilterType type;

        /**
        * The order of execution for the filter.
        **/
        float order;

        /**
        * Is true if the filter is enabled.
        **/
        bool enabled;
    };

    /**
    * FilterInterface provides a server side interface to
    * a [Filter].
    **/
    interface FilterInterface {
        /**
        * Set the filter to enabled or disabled
        **/
        idempotent void setEnabled(bool enabled)
            throws ::SpiIce::SpiIceException;

        /**
        * Set the filter name.
        **/
        idempotent void setName(string name)
            throws ::SpiIce::SpiIceException;

        /**
        * Set the type of the filter. See [CueIce::FilterType]
        **/
        idempotent void setType(CueIce::FilterType type)
            throws ::SpiIce::SpiIceException;

        /**
        * Raises the order of the filter, this makes it run
        * before the previous filter.
        **/
        idempotent void raiseOrder()
            throws ::SpiIce::SpiIceException;

        /**
        * Lowers the order of the filter, this makes it run
        * after the next filter
        **/
        idempotent void lowerOrder()
            throws ::SpiIce::SpiIceException;

        /**
        * Moves the filter to first in the order list.
        **/
        idempotent void orderFirst()
            throws ::SpiIce::SpiIceException;

        /**
        * Moves the filter to last in the order list.
        **/
        idempotent void orderLast()
            throws ::SpiIce::SpiIceException;

        /**
        * Directly sets the order of the filter.
        **/
        idempotent void setOrder(int order)
            throws ::SpiIce::SpiIceException;

        /**
        * Executes the filter on a specified sequence
        * of job proxies.
        **/
        void runFilterOnJobs(JobProxySeq jobs)
            throws ::SpiIce::SpiIceException;

        /**
        * Executes the filter on a specified group
        * proxy.
        **/
        void runFilterOnGroup(GroupInterface *proxy)
            throws ::SpiIce::SpiIceException;

        /**
        * Returns a list of [Matcher]s configured for this filter.
        **/
        idempotent MatcherSeq getMatchers()
            throws ::SpiIce::SpiIceException;

        /**
        * Returns a list of [Action]s configured for this filter.
        **/
        idempotent ActionSeq getActions()
            throws ::SpiIce::SpiIceException;

        /**
        * Delete this fiter.
        **/
        void delete()
            throws ::SpiIce::SpiIceException;

        /**
        * Creates a new [Action] that will execute for this fiter.
        **/
        Action createAction(ActionData data)
            throws ::SpiIce::SpiIceException;

        /**
        * Creates a new [Matcher] for this filter.
        **/
        Matcher createMatcher(MatcherData data)
            throws ::SpiIce::SpiIceException;
    };

    /**
    * Filters are used to apply custom settings to a job
    * before it is launched.
    **/
    class Filter {
        FilterData data;
        FilterInterface *proxy;
    };

    /**
    * MatcherInterface provides a server side interface
    * to a [Matcher].
    **/
    interface MatcherInterface {

        /**
        * Returns the [Filter] this matcher is part of.
        **/
        idempotent Filter getParentFilter()
            throws ::SpiIce::SpiIceException;

        /**
        * Delete this matcher.
        **/
        void delete()
            throws ::SpiIce::SpiIceException;

        /**
        * Sets new properties for the [Matcher] on the
        * server side using a [MatcherData] object.
        **/
        void commit(MatcherData data)
            throws ::SpiIce::SpiIceException;

    };

    /**
    * A Matcher is used to match job information in a filter.
    **/
    class Matcher {
        /**
        * MatcherData provides a struct of [Matcher] information.
        **/
        MatcherData data;

        /**
        * MatcherInterface provides a server side interface
        * to a [Matcher].
        **/
        MatcherInterface *proxy;
    };

    /**
    * ActionInterface provides a server side interface
    * to an [Action].
    **/
    interface ActionInterface {

        /**
        * Returns the [Filter] this action is part of.
        **/
        idempotent Filter getParentFilter()
            throws ::SpiIce::SpiIceException;

        /**
        * Delete this [Action]
        **/
        void delete()
            throws ::SpiIce::SpiIceException;

        /**
        * Sets new properties for the [Action] on the
        * server side using a [ActionData] object.
        **/
        void commit(ActionData data)
            throws ::SpiIce::SpiIceException;
    };

    /**
    * Actions are taken on [Job]s if all [Matcher]s in a [Filter]
    * are successful.
    **/
    class Action {
        /**
        * ActionData provides a struct of [Action] information.
        **/
        ActionData data;

        /**
        * ActionInterface provides a server side interface
        * to a [Action].
        **/
        ActionInterface *proxy;
    };

    /**
    * ProcSearchCriteria provides a way to define an
    * arbitrary [Proc] search.
    **/
    class ProcSearchCriteria extends SearchCriteria {
        /**
        * An array of host names to match.
        **/
        CueIce::StringSet hosts;

        /**
        * An array of job names to match.
        **/
        CueIce::StringSet jobs;

        /**
        * An arra of layer names to match.
        **/
        CueIce::StringSet layers;

        /**
        * An array of show names to match.
        **/
        CueIce::StringSet shows;

        /**
        * An array of allocation names to match.
        **/
        CueIce::StringSet allocs;

        /**
        * A range of memory usage.  Ranges should
        * be in the format "x-y"  Values are in KB.
        **/
        SpiIce::IntegerSearchCriterionOpt memoryRange;

        /**
        * A duration range.  Ranges should be in
        * the format "x-y". Values are in seconds.
        **/
        SpiIce::IntegerSearchCriterionOpt durationRange;
    };

    /**
    * ProcInterface provides a server side implementation
    * for a proc.
    **/
    interface ProcInterface {

        /**
        * Sends a kill signal to the running process.
        **/
        void kill()
            throws ::SpiIce::SpiIceException;

        /**
        * Unbooks this [Proc].  Unbooking means the [Proc] will
        * automatically seek out a new [Job] when the current
        * [Frame] is complete.
        **/
        void unbook(bool kill)
            throws ::SpiIce::SpiIceException;

        /**
        * Returns the the [Host] this [Proc] was allocated from.
        **/
        idempotent Host getHost()
             throws ::SpiIce::SpiIceException;

        /**
        * Returns the [Frame] running on the [Proc]
        **/
        idempotent Frame getFrame()
             throws ::SpiIce::SpiIceException;

        /**
        * Returns the [Job] the [Proc] has been assigned to.
        */
        idempotent Job getJob()
             throws ::SpiIce::SpiIceException;

        /**
        * Returns the [Layer] the [Proc] has been assigned to.
        */
        idempotent Layer getLayer()
             throws ::SpiIce::SpiIceException;

        /**
        * Unbooks and redriects the proc to the specified job.  Optionally
        * kills the proc immediately.  Will overwrite an existing redirect.
        * Return true if the redirect was a success. The redirect would fail
        * in the event that the specified job does not have a suitable frame
        * for the proc.
        **/
        idempotent bool redirectToJob(JobInterface *proxy, bool kill)
             throws ::SpiIce::SpiIceException;

        /**
        * Unbooks and redriects the proc to the specified group.  Optionally
        * kills the proc immediately.  Will overwrite an existing redirect.
        * Return true if the redirect was a success. The redirect would fail
        * in the event that the specified group does not have a suitable frame
        * for the proc.
        **/
        idempotent bool redirectToGroup(GroupInterface *proxy, bool kill)
             throws ::SpiIce::SpiIceException;

        /**
        * Clears the redirect off of the proc so it dispatches naturally.
        **/
        idempotent bool clearRedirect()
             throws ::SpiIce::SpiIceException;
    };

    /**
    * The ProcData struct contains data for a [Proc]
    **/
    struct ProcData {
           /**
           * The name of the [Proc]. This is a concatenation of the
           * the [Host] name and the number of cores allocated by
           * the [Proc].  Ex: nest1012/2.0
           **/
        string name;

        /**
        * The name of the [Show] this [Proc] is being utilized on.
        **/
        string showName;

          /**
        * The name of the [Job] this [Proc] is being utilized on.
        **/
        string jobName;

        /**
        * The name of the [Frame] this [Proc] is running.
        **/
        string frameName;

        /**
        * The name of the [Group] the job is running in.
        **/
        string groupName;

        /**
        * The last time the [Host] confirmed it was running the
        * same [Frame] that the Cue thinks it should be running.
        **/
        int pingTime;

        /**
        * The time when this [Proc] was assigned to its current [Job]
        **/
        int bookedTime;

        /**
        * The time when this [Proc] started the current [Frame]
        **/
        int dispatchTime;

        /**
        * The amount of memory this [Proc] has resereved on the [Host].
        **/
        long reservedMemory;

        /**
        * The amount of memory this [Proc] has resereved on the [Host].
        **/
        long reservedGpu;

        /**
        * The amount of memory the [Proc] is actually using.
        **/
        long usedMemory;

        /**
        * The number of cores this [Proc] has reserved on the [Host].
        **/
        float reservedCores;

        /**
        * If the [Proc] is unbooked, it wil immediately seek out a new
        * [Job] after the current [Frame] is complete.
        **/
        bool unbooked;

        /**
        * The full path to the frame log.
        **/
        string logPath;

        /**
        * Redirect target.  This will be either the job name or the group
        * name the proc will be going to next.
        **/
        string redirectTarget;

        /**
        * An array of services running on the current proc.
        **/
        SpiIce::StringSeq services;

    };

    /**
    * The Proc class represents allocated resources from
    * a [Host] that are assigned to a [Job] and executing a [Frame].
    **/
    class Proc {
        /**
        * ProcData provides a struct of [Proc] information.
        **/
        ProcData data;

        /**
        * ProcInterface provides a server side interface
        * to a [Proc].
        **/
        ProcInterface *proxy;
    };

    class NestedProc extends Proc {
        NestedHost parent;
    };

    /**
    * The owner of a desktop host.
    **/
    struct Owner {

        /**
        * Username of the current user.
        **/
        string name;

        /**
        * The name of the show the user is assigned to.
        **/
        string show;

        /**
        * Number of hosts assigned to the owner.
        **/
        int hostCount;

        /**
        * A proxy to the owner interface.
        **/
        OwnerInterface *proxy;
    };

    struct Deed {

        /**
        * Name of the host.
        **/
        string host;

        /**
        * Name of the owner.
        **/
        string owner;

        /**
        * Name of the show.
        */
        string show;

        /**
        * Value will be true if the user has setup blackout times
        * on which he/she doesn't want the desktop to be used.
        **/
        bool blackout;

        /**
        * The time to not use the host anymore.
        **/
        SpiIce::IntOpt blackoutStartTime;

        /**
        * The time to start using the host again.
        **/
        SpiIce::IntOpt blackoutStopTime;

        /**
        * A proxy to the interface.
        **/

        DeedInterface *proxy;
    };

    /**
    * A sequence of owners.
    **/
    ["java:type:java.util.ArrayList<Owner>:java.util.List<Owner>"]
    sequence<Owner> OwnerSeq;

    /**
    * A sequence of deeds.
    **/
    ["java:type:java.util.ArrayList<Deed>:java.util.List<Deed>"]
    sequence<Deed> DeedSeq;

    interface OwnerInterface {

        /**
        * Get a list of all hosts this owner is
        * responsible for.
        **/
        HostSeq getHosts()
            throws ::SpiIce::SpiIceException;

        /**
        * Get a list of all deeds this owner has.
        **/
        DeedSeq getDeeds()
            throws ::SpiIce::SpiIceException;

        /**
        * Deletes the owner record.
        **/
        idempotent void delete()
            throws ::SpiIce::SpiIceException;

        /**
        * Sets the owners show.
        **/
        idempotent void setShow(string show)
            throws ::SpiIce::SpiIceException;

        /**
        * Set the hosts new owner settings.  Any host may have an owner, not
        * just desktops.  This allows direct control of the cores.  By
        * default hosts have no owner settings.
        **/
        idempotent void takeOwnership(string host)
            throws ::SpiIce::SpiIceException;
    };

    /**
    * A deed gives an owner controll over a particular host.
    **/
    interface DeedInterface {

        /**
        * Remove the deed
        **/
        void delete()
            throws ::SpiIce::SpiIceException;

        /**
        * Returns the full host for these settings.
        **/
        Host getHost()
            throws ::SpiIce::SpiIceException;

        /**
        * Returns the owner for these settings.
        **/
        Owner getOwner()
            throws ::SpiIce::SpiIceException;

        /**
        * Sets a blackout time for the host.
        **/
        void setBlackoutTime(int startTime, int stopTime)
            throws ::SpiIce::SpiIceException;

        /**
        * Enable/Disable blackout time without changing the times.
        **/
        void setBlackoutTimeEnabled(bool enabled)
            throws ::SpiIce::SpiIceException;
    };

    interface RenderPartitionInterface {

        /**
        * Deletes the host local setup.  Any proc that is running
        * from this should be killed or else the counts could
        * be off.
        **/
        void delete()
            throws ::SpiIce::SpiIceException;

        /**
        * Reset the maximum amount of cores and memory for this render partition.
        **/
        void setMaxResources(int cores, long memory, long gpu)
            throws ::SpiIce::SpiIceException;
    };

    /**
    * Using local booking objects a user can create per-host local
    * booking schemes that override NIMBY and threading behavior.
    **/
    struct RenderPartition {

        /**
        * The job the the host is assigned to.
        **/
        string job;

        /**
        * The job the the host is assigned to.
        **/
        SpiIce::StringOpt layer;

        /**
        * The job the the host is assigned to.
        **/
        SpiIce::StringOpt frame;

        /**
        * The type of request this is.
        **/
        CueIce::RenderPartitionType renderPartType;

        /**
        * The host that is running the job.
        **/
        string host;

        /**
        * The number of running cores.
        **/
        int cores;

        /**
        * The amount of memory in use.
        **/
        long memory;

        /**
        * The maximum number of cores to run off this host.
        **/
        int maxCores;

        /**
        * The amount of memory to use, even if the desktop says
        * the memory is not available.
        **/
        long maxMemory;

        /**
        * The amount of gpu memory to use, even if the desktop says
        * the gpu memory is not available.
        **/
        long maxGpu;

        /**
        * The number of threads per frame.
        **/
        int threads;

        RenderPartitionInterface *proxy;
    };

    /**
    * A sequence of RenderParitions
    **/
    ["java:type:java.util.ArrayList<RenderPartition>:java.util.List<RenderPartition>"]
    sequence<RenderPartition> RenderPartitionSeq;

    /**
    * HostSearchCriteria provides a way to define an
    * arbitrary [Host] search.
    **/
    struct HostSearchCriteria {
        /**
        * An array of [Host] names to match.
        **/
        CueIce::StringSet hosts;

        /**
        * An array of regular expressions that are
        * matched against the [Host] name.
        **/
        CueIce::StringSet regex;

        /**
        * An array of substring searches that are
        * matched against the [Host] name.
        **/
        CueIce::StringSet substr;

        /**
        * An array of unique Ids that are matched
        * against the [Host] unique id.
        **/
        CueIce::StringSet ids;

        /**
        * An array of [Allocation] names that are
        * matched against the [Host]'s [Allocation]
        **/
        CueIce::StringSet allocs;

        /**
        * An array of HardwareStates to match
        **/
        CueIce::HardwareStateSeq states;

    };

    interface HostInterface {

        /**
        * Locks the host.  Its possible we'll need to pass in a show
        * name here in the future.
        */
        idempotent void lock()
            throws ::SpiIce::SpiIceException;

        /**
        * Unlocks the host for booking if the proc is in the Locked
        * state. You cannot unlock a NimbyLocked proc.
        */
        idempotent void unlock()
            throws ::SpiIce::SpiIceException;

        /**
        * Sets the reboot when idle state, nothing has to be locked to set this.
        * When the host pings in idle a reboot command is sent to the host
        * and the host will be put into the Rebooting state.  If any locks are
        * set they will be removed upon reboot.
        */
        idempotent void rebootWhenIdle()
            throws ::SpiIce::SpiIceException;

        /**
        * Issues an immedidate reboot.
        */
        void reboot()
            throws ::SpiIce::SpiIceException;

        /**
        * Delete host.
        */
        idempotent void delete()
            throws ::SpiIce::SpiIceException;

        /**
        * Assign a host to an allocation.
        **/
        idempotent void
            setAllocation(AllocationInterface *proxy)
            throws ::SpiIce::SpiIceException;

        /**
        * Set a tag on this host.
        **/
        idempotent void addTags(SpiIce::StringSeq tags)
            throws ::SpiIce::SpiIceException;

        /**
        * Remove a tag from this host.
        **/
        idempotent void removeTags(SpiIce::StringSeq tags)
            throws ::SpiIce::SpiIceException;

        /**
        * Rename tag.
        **/
        idempotent void renameTag(string oldTag, string newTag)
            throws ::SpiIce::SpiIceException;

        /**
        * Get the comments for this host.
        **/
        idempotent CommentSeq getComments()
            throws ::SpiIce::SpiIceException;

        /**
        * Add a comment on this host.
        **/
        void addComment(CommentData newComment)
            throws ::SpiIce::SpiIceException;

        /**
        * Returns the list of proc resources allocated from this host.
        **/
        idempotent ProcSeq getProcs()
            throws ::SpiIce::SpiIceException;

        /**
        * Changes the host's [CueIce::ThreadMode]
        **/
        idempotent void setThreadMode(CueIce::ThreadMode mode)
            throws ::SpiIce::SpiIceException;

        /**
        * Manually set the hardware state for the host.  The hardware
        * state may be changed automatically if the host pings in.  If
        * the hardware state is set to "Reimage", the state will not
        * automatically change with a host ping, and must be manually
        * set back to Up.
        **/
        idempotent void setHardwareState(CueIce::HardwareState state)
            throws ::SpiIce::SpiIceException;

        /**
        * Get the owner settings of this particular host.
        **/
        idempotent Owner getOwner()
            throws ::SpiIce::SpiIceException;

        /**
        * Return the deed for this host.
        **/
        idempotent Deed getDeed()
            throws ::SpiIce::SpiIceException;

        /**
        * Return any render partitions that are setup on this host.
        **/
        RenderPartitionSeq getRenderPartitions()
            throws ::SpiIce::SpiIceException;

        /**
        * Redirect the given procs to the specified job.
        **/
        bool redirectToJob(ProcProxySeq procs, JobInterface *job)
            throws ::SpiIce::SpiIceException;

        /**
        * Set the name of the host operating system.
        **/
        idempotent void setOs(string os)
            throws ::SpiIce::SpiIceException;

    };

    /**
    * The HostData struct provides vital information about the [Host]
    **/
    struct HostData {
        /**
        * The name of the [Host].
        **/
        string name;

        /**
        * The name of the [Allocation] the [Host] belongs to.
        **/
        string allocName;

        /**
        * nimbyEnabled is  True if a user is actively working
        * at the machine.
        **/
        bool nimbyEnabled;

        /**
        * hasComment is True if the [Host] has a comment.
        **/
        bool hasComment;

        /**
        * The total number of cores on the host.
        **/
        float cores;

        /**
        * The total number of idle cores on the host.
        **/
        float idleCores;

        /**
        * The total theoretical amount of memory on the [Host] in Kilobytes.
        **/
        long memory;

        /**
        * The total amount of unreserved memory on the [Host] in Kilobytes.
        **/
        long idleMemory;

        /**
        * The total theoretical amount of gpu memory on the [Host] in Kilobytes.
        **/
        long gpu;

        /**
        * The total amount of unreserved gpu memory on the [Host] in Kilobytes.
        **/
        long idleGpu;

        /**
        * The total amount of swap on the [Host] in Kilobytes.
        **/
        long totalSwap;

        /**
        * The total amount of memory on the [Host] in Kilobytes.
        **/
        long totalMemory;

        /**
        * The total amount of GPU memory on the [Host] in Kilobytes.
        **/
        long totalGpu;

        /**
        * The total amount of Mcp on the [Host] in Kilobytes.
        **/
        long totalMcp;

        /**
        * The total amount of free swap on the [Host] in Kilobytes.
        **/
        long freeSwap;

        /**
        * The total amount of free mempru on the [Host] in Kilobytes.
        **/
        long freeMemory;

        /**
        * The total amount of free Mcp on the [Host] in Kilobytes.
        **/
        long freeMcp;

        /**
        * The total amount of free GPU memory on the [Host] in Kilobytes.
        **/
        long freeGpu;

        /**
        * The 1 minute load factor for the [Host].
        **/
        int load;

        /**
        * The time the [Host] was last rebooted.
        **/
        int bootTime;

        /**
        * The last time the [Host] talked to the Cue3 server.
        **/
        int pingTime;

        /**
        * The operating system running on the host.  Set by
        * the SP_OS environement variable in RQD.
        **/
        string os;

        /**
        * The [Host]'s tags. Tags are used to determine that types of
        * [Frame]s a [Host] can run.
        **/
        SpiIce::StringSeq tags;

        /**
        * The current state of the Hardware.  See [CueIce::HardwareState].
        **/
        CueIce::HardwareState state;

        /**
        * The current LockState.  See [CueIce::LockState].
        **/
        CueIce::LockState lockState;

        /**
        * The current threading mode.  See [CueIce::ThreadMode]
        **/
        CueIce::ThreadMode threadMode;
    };

    /**
    * The Host class repesents a unique host that is pinging
    * into the Cue3 cluster.
    **/
    class Host {
        /**
        * The HostData struct provides vital information about the [Host]
        **/
        HostData data;

        /**
        * The HostInterface class provides a server side interface
        * to a [Host].
        **/
        HostInterface *proxy;
    };

    class NestedHost extends Host {
        NestedProcSeq procs;
    };

    /**
    * The DependData struct provides vital information about a
    * [Depend].
    **/
    struct DependData {

        /**
        * The type of depend.
        **/
        CueIce::DependType type;

        /**
        * The target of depend, either internal or external.
        **/
        CueIce::DependTarget target;

        /**
        * True if the depend is an any frame depend.
        **/
        bool anyFrame;

        /**
        * True if the depend is active.
        **/
        bool active;

        /**
        * Name of the job that is depending.
        **/
        string dependErJob;

        /**
        * Name of the layer that is depending.
        **/
        string dependErLayer;

        /**
        * Name of the frame that is depending
        **/
        string dependErFrame;

        /**
        * Name of the job to depend on
        **/
        string dependOnJob;

        /**
        * Name of the layer to depend on.
        **/
        string dependOnLayer;

        /**
        * Name of the name to depend on.
        **/
        string dependOnFrame;
    };

    /**
    * The DependInterface class provides a server side interface
    * to a [Depend].
    **/
    interface DependInterface {
         /**
         * Satisfies the dependency which sets any frames
         * waiting on this dependency to the WAITING state.
         **/
         void satisfy()
            throws ::SpiIce::SpiIceException;

         /**
         * Unsatisfies the dependency making it active again and
         * sets matching frames to DEPEND
         */
         void unsatisfy()
            throws ::SpiIce::SpiIceException;
    };

    /**
    * The Depend class repesents a unique dependency on the Cue3 server.
    **/
    class Depend {
        DependData data;
        DependInterface *proxy;
    };

    /*
    * Frames
    *
    * A frame represents a single command to be run on a render node.
    */

    /**
    * New struct for frame searching
    **/
    struct FrameSearchCriteria {
        CueIce::StringSet ids;
        CueIce::StringSet frames;
        CueIce::StringSet layers;
        CueIce::FrameStateSeq states;
        string frameRange;
        string memoryRange;
        string durationRange;
        int page;
        int limit;
        int changeDate;
    };

    interface FrameInterface {
        /* Eats the frame */
        void eat()
            throws ::SpiIce::SpiIceException;

        /* Kills the frame if it is running */
        void kill()
            throws ::SpiIce::SpiIceException;

        /* Retries the frame by setting it as waiting */
        void retry()
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Returns a list of dependencies setup to depend on
        * this frame.
        **/
        idempotent DependSeq getWhatDependsOnThis()
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Returns a list of dependencies that this frame
        * depends on.
        **/
        idempotent DependSeq getWhatThisDependsOn()
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Sets up and returns a FrameOnJob dependency.
        **/
        Depend createDependencyOnJob(JobInterface *proxy)
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Sets up and returns a FrameOnLayer dependency.
        **/
        Depend createDependencyOnLayer(LayerInterface *proxy)
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Sets up and returns a FrameOnFrame dependency.
        **/
        Depend createDependencyOnFrame(FrameInterface *proxy)
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Changes the frame's dependency count to 0, which will
        * put the frame into the waiting state.  Retrying the frame
        * will put it back into the waiting state.  This won't affect
        *
        **/
        void markAsWaiting()
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Will recount the number of active dependencies on the
        * frame and put it back into the Depend state if that
        * count is greater than 0.
        *
        **/
        void markAsDepend()
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Drops every dependendy that is causing this frame not to run.
        **/
        void dropDepends(CueIce::DependTarget target)
            throws ::SpiIce::SpiIceException;

        /**
        *
        **/
        RenderPartition addRenderPartition(string host,
            int threads, int maxCores, long maxMemory, long maxGpu)
            throws ::SpiIce::SpiIceException;

        /**
        * Updates the state of the frame's checkpoint status.  If
        * the checkpoint status is compelte, then the frame's
        * checkpointCoreSeconds is updated with the amount of render
        * time that was checkpointed.
        **/
        idempotent void setCheckpointState(CueIce::CheckpointState state)
            throws ::SpiIce::SpiIceException;

    };

    struct FrameData {
        string name;
        string layerName;
        int number;
        CueIce::FrameState state;
        int retryCount;
        int exitStatus;
        int dispatchOrder;
        int startTime;
        int stopTime;
        long maxRss;
        long usedMemory;
        long reservedMemory;
        long reservedGpu;
        string lastResource;
        CueIce::CheckpointState checkpointState;
        int checkpointCount;
        int totalCoreTime;
    };

    /*
    * Frame repesents a single frame from a layer.
    */
    class Frame {
        FrameData data;
        FrameInterface *proxy;
    };

    /**
    * A struct containing properties for all the elements of a frame that
    * can change except for the ID which is there for indexing purposes.
    **/
    struct UpdatedFrame {
        string id;
        CueIce::FrameState state;
        int retryCount;
        int exitStatus;
        int startTime;
        int stopTime;
        long maxRss;
        long usedMemory;
        string lastResource;
    };

    ["java:type:java.util.ArrayList<UpdatedFrame>:java.util.List<UpdatedFrame>"]
    sequence<UpdatedFrame> UpdatedFrameSeq;

    /**
    * The result of an updated frame check.  The job state is included
    * so tools that are just monitoring frames can stop monitoring them
    * once the job state changes to Finished.
    **/
    struct UpdatedFrameCheckResult {
        CueIce::JobState state;
        int serverTime;
        UpdatedFrameSeq updatedFrames;
    };

    /*
    * Layers
    *
    * A Layer represents a range of identical shell commands,
    * save that the frame number changes on each frame.
    */

    interface LayerInterface
    {
        void killFrames()
            throws ::SpiIce::SpiIceException;

        void eatFrames()
            throws ::SpiIce::SpiIceException;

        void retryFrames()
            throws ::SpiIce::SpiIceException;

        void markdoneFrames()
            throws ::SpiIce::SpiIceException;

        idempotent FrameSeq getFrames(FrameSearchCriteria s)
            throws ::SpiIce::SpiIceException;

        idempotent void setTags(CueIce::StringSet tags)
            throws ::SpiIce::SpiIceException;

        idempotent void setMinCores(float cores)
            throws ::SpiIce::SpiIceException;

        /**
        * The maximum number of cores to run on a given
        * frame within this layer.  Fractional core
        * values are not allowed with this setting.
        */
        idempotent void setMaxCores(float cores)
            throws ::SpiIce::SpiIceException;

        idempotent void setThreadable(bool threadable)
            throws ::SpiIce::SpiIceException;

        idempotent void setMinMemory(long memory)
            throws ::SpiIce::SpiIceException;

        idempotent void setMinGpu(long gpu)
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Returns a list of dependencies setup to depend on
        * this layer.  This includes all types of depends, not just
        * OnLayer dependencies.  This will not return any frame on frame
        * dependencies that are part of a FrameByFrame depend.  It will
        * return a single element that represents the entire dependency.
        **/
        idempotent DependSeq getWhatDependsOnThis()
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Returns a list of dependencies that this frame
        * depends on.
        **/
        idempotent DependSeq getWhatThisDependsOn()
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Setup and return a LayerOnJob dependency
        **/
        Depend createDependencyOnJob(JobInterface *proxy)
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Setup and return a LayerOnLayer dependency
        **/
        Depend createDependencyOnLayer(LayerInterface *proxy)
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Setup and return a LayerOnJob dependency
        **/
        Depend createDependencyOnFrame(FrameInterface *proxy)
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Setup and return a FrameByFrame dependency
        **/
        Depend createFrameByFrameDependency(
            LayerInterface *proxy, bool anyFrame)
                throws ::SpiIce::SpiIceException;

        /**
        *
        * Drops every dependency that is causing this layer not to run.
        **/
        void dropDepends(CueIce::DependTarget target)
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Reorders the specified frame range on this job.
        **/
        void reorderFrames(string range, CueIce::Order order)
             throws ::SpiIce::SpiIceException;

        /**
        *
        * Staggers the specified frame range.
        **/
        void staggerFrames(string range, int stagger)
             throws ::SpiIce::SpiIceException;


        RenderPartition addRenderPartition(string host,
             int threads, int maxCores, long maxMemory, long maxGpu)
             throws ::SpiIce::SpiIceException;

        /**
        * When disabled, This will stop Cue3 from lowering the
        * amount of memory required for a given layer.
        **/
        idempotent void enableMemoryOptimizer(bool value)
            throws ::SpiIce::SpiIceException;

        /**
        * Register an output with the given layer.  The output paths
        * are sent in the Cue3 email.
        **/
        void registerOutputPath(string spec)
          throws ::SpiIce::SpiIceException;

        /**
        * Return a list of all registered output paths.
        **/
        CueIce::StringSeq getOutputPaths()
          throws ::SpiIce::SpiIceException;

    };

    struct LayerStats {
        int totalFrames;
        int waitingFrames;
        int runningFrames;
        int deadFrames;
        int eatenFrames;
        int dependFrames;
        int succeededFrames;
        int pendingFrames;
        int avgFrameSec;
        int lowFrameSec;
        int highFrameSec;
        int avgCoreSec;
        long renderedFrameCount;
        long failedFrameCount;
        long remainingCoreSec;
        long totalCoreSec;
        long renderedCoreSec;
        long failedCoreSec;
        long maxRss;
        float reservedCores;
    };

    struct LayerData {
        string name;
        string range;
        CueIce::StringSet tags;
        float minCores;
        float maxCores;
        bool isThreadable;
        long minMemory;
        long minGpu;
        int chunkSize;
        int dispatchOrder;
        CueIce::LayerType type;

        /**
        * An array of services that are being run on all frames
        * within this layer.
        **/
        SpiIce::StringSeq services;

        /**
        * True if the memory optimizer is enabled.  Disabling the
        * optimizer will stop Cue3 from lowering memory.
        */
        bool memoryOptimzerEnabled;
    };

    /*
    * Layer repesents a single layer from a job.
    */
    class Layer
    {
        LayerData data;
        LayerStats stats;
        LayerInterface *proxy;
        JobInterface *parent;
    };

    /*
    * Cue Jobs
    * A Cue Job contains a list of layers, which in turn contain a
    * list of frames.
    * Any job not in the "Finished" state is considered visible.
    * A job is update to the "Finished" state right before its deleted.
    * Jobs that are in the "Pending or Shutdown" state can be booked.
    * Jobs that are in the "Startup" state cannot be booked.
    *
    * It is impossible to have 2 jobs with the same name so job names
    * will be versioned up.
    */

    /**
    * Use to filter the job search.  Please note that by searching
    * for non-pending jobs, the output is limited to 200 jobs;
    **/
    struct JobSearchCriteria {
        CueIce::StringSet jobs;
        CueIce::StringSet regex;
        CueIce::StringSet substr;
        CueIce::StringSet ids;
        CueIce::StringSet users;
        CueIce::StringSet shots;
        CueIce::StringSet shows;
        bool includeFinished;
    };

    /*
    * The cuejob interface is for managing jobs.  All of these methods will
    * throw a SpiIceException if the job does not exist or is not in an
    * active state.
    */
    interface JobInterface {
        /*
        * Kill the job.  This puts the job into the Finished State
        * All running frames are killed, all depends satisfied.
        */
        void kill()
            throws ::SpiIce::SpiIceException;

        /* Pauses the job, which means it no longer gets procs */
        idempotent void pause()
            throws ::SpiIce::SpiIceException;

        /* Resumes a paused job */
        idempotent void resume()
            throws ::SpiIce::SpiIceException;

        /* Kills all frames that match the FrameSearchCriteria */
        void killFrames(FrameSearchCriteria req)
            throws ::SpiIce::SpiIceException;

        /* Eats all frames that match the FrameSearchCriteria */
        void eatFrames(FrameSearchCriteria req)
            throws ::SpiIce::SpiIceException;

        /* Retries all frames that match the FrameSearchCriteria */
        void retryFrames(FrameSearchCriteria req)
            throws ::SpiIce::SpiIceException;

        /* Drops any dependency that requires any frame that matches the
         * FrameSearchCriteria */
        void markDoneFrames(FrameSearchCriteria req)
            throws ::SpiIce::SpiIceException;

        /* Sets the minimum number of procs to run on this job  */
        idempotent void setMinCores(float val)
            throws ::SpiIce::SpiIceException;

        /* Sets the maximum number of procs that can run on this job */
        idempotent void setMaxCores(float val)
            throws ::SpiIce::SpiIceException;

        /* Sets the job priority */
        idempotent void setPriority(int val)
            throws ::SpiIce::SpiIceException;

        /* Returns all layer objects */
        idempotent LayerSeq getLayers()
            throws ::SpiIce::SpiIceException;

        /* Returns all frame objects that match FrameSearchCriteria */
        idempotent FrameSeq getFrames(FrameSearchCriteria req)
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Move the job into the specified group
        **/
        idempotent void setGroup(GroupInterface *proxy)
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Sets the default maximum number of frame retries for the job. One
        * a frame has retried this many times it will automatically go
        * to the dead state. The default upper limit on this is 16 retries.
        *
        **/
        idempotent void  setMaxRetries(int maxRetries)
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Returns a UpdatedFrameCheckResult which contains
        * updated state information for frames that have changed since the
        * last update time as well as the current state of the job.
        *
        * If the user is filtering by layer, passing an array of layer
        * proxies will limit the updates to specific layers.
        *
        * At most, your going to get 1 update per running frame every minute
        * due to memory usage.
        *
        **/
        idempotent UpdatedFrameCheckResult
            getUpdatedFrames(int lastCheck, LayerProxySeq layerFilter)
            throws ::SpiIce::SpiIceException;

        /* If set to true, a frame that would have turned dead, will become
         * eaten */
        idempotent void setAutoEat(bool value)
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Returns a list of dependencies setup to depend on
        * this job.  This includes all types of depends, not just
        * OnJob dependencies.  This will not return any frame on frame
        * dependencies that are part of a FrameByFrame depend.  It will
        * return a single element that represents the entire dependency.
        **/
        idempotent DependSeq getWhatDependsOnThis()
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Returns a list of dependencies that this frame
        * depends on.
        **/
        idempotent DependSeq getWhatThisDependsOn()
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Returns a list of all dependencies that this job
        * is involved with.
        **/
        DependSeq getDepends()
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Setup and return a JobOnJob dependency
        **/
        idempotent Depend createDependencyOnJob(JobInterface *proxy)
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Setup and retunrn a JobOnLayer dependency
        **/
        Depend createDependencyOnLayer(LayerInterface *proxy)
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Setup and return a JobOnFrame dependency
        **/
        Depend createDependencyOnFrame(FrameInterface *proxy)
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Drops all external dependencies for the job.  This means that
        * the internal depend structure will be maintained, but everything
        * that depends on another job will be dropped.
        *
        **/
        void dropDepends(CueIce::DependTarget target)
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Updates the matching frames from the Depend state
        * to the waiting state.
        *
        **/
        void markAsWaiting(FrameSearchCriteria req)
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Get the comments for this job
        **/
        idempotent CommentSeq getComments()
            throws ::SpiIce::SpiIceException;

       /**
       *
       * Add a comment on this job
       **/
       void addComment(CommentData newComment)
            throws ::SpiIce::SpiIceException;

       /**
       *
       * Reorders the specified frame range on this job.
       **/
       void reorderFrames(string range, CueIce::Order order)
            throws ::SpiIce::SpiIceException;

       /**
       *
       * Staggers the specified frame range.
       **/
       void staggerFrames(string range, int stagger)
            throws ::SpiIce::SpiIceException;

        /**
        * Add a render partition to the local host.  This partition will
        * run frames on the specified job.
        **/
        RenderPartition addRenderPartition(string host,
            int threads, int maxCores, long maxMemory, long maxGpu)
            throws ::SpiIce::SpiIceException;

        /**
        *
        * Rerun filters for this job.
        **/
        void runFilters()
             throws ::SpiIce::SpiIceException;
    };

    struct JobStats {
        int totalLayers;
        int totalFrames;
        int waitingFrames;
        int runningFrames;
        int deadFrames;
        int eatenFrames;
        int dependFrames;
        int succeededFrames;
        int pendingFrames;
        int avgFrameSec;
        int highFrameSec;
        int avgCoreSec;
        long renderedFrameCount;
        long failedFrameCount;
        long remainingCoreSec;
        long totalCoreSec;
        long renderedCoreSec;
        long failedCoreSec;
        long maxRss;
        float reservedCores;
    };

    struct JobData {
        CueIce::JobState state;
        string name;
        string shot;
        string show;
        string user;
        string group;
        string facility;
        string os;
        int uid;
        int priority;
        float minCores;
        float maxCores;
        string logDir;
        bool isPaused;
        bool hasComment;
        bool autoEat;
        int startTime;
        int stopTime;
    };

    /*
    * Job repesents a single cue job.
    */
    class Job {
        JobData data;
        JobStats stats;
        JobInterface *proxy;
    };

    class NestedJob extends Job {
        NestedGroup parent;
    };

    /*
    * Groups
    *
    * A group may contain other groups or cue jobs.
    */
    interface GroupInterface  {

     void delete()
        throws ::SpiIce::SpiIceException;

     idempotent void setName(string name)
        throws ::SpiIce::SpiIceException;

     /**
     * Sets the group's parent group.  This call is ignored if you try to
     * reparent the root group.
     **/
     idempotent void setGroup(GroupInterface *group)
        throws ::SpiIce::SpiIceException;

     Group createSubGroup(string name)
        throws ::SpiIce::SpiIceException;

     idempotent void setDefaultJobMaxCores(float maxCores)
        throws ::SpiIce::SpiIceException;

     idempotent void setDefaultJobMinCores(float minCores)
        throws ::SpiIce::SpiIceException;

     idempotent void setDefaultJobPriority(int priority)
        throws ::SpiIce::SpiIceException;

     idempotent void setMaxCores(float maxCores)
        throws ::SpiIce::SpiIceException;

     idempotent void setMinCores(float minCores)
        throws ::SpiIce::SpiIceException;

     idempotent void setDepartment(string dept)
        throws ::SpiIce::SpiIceException;

     idempotent GroupSeq getGroups()
         throws ::SpiIce::SpiIceException;

     idempotent JobSeq getJobs()
         throws ::SpiIce::SpiIceException;

     idempotent void reparentJobs(JobProxySeq jobs)
         throws ::SpiIce::SpiIceException;

     idempotent void reparentGroups(GroupProxySeq groups)
         throws ::SpiIce::SpiIceException;

    };

    struct GroupData {
        string name;
        string department;
        int defaultJobPriority;
        float defaultJobMinCores;
        float defaultJobMaxCores;
        float minCores;
        float maxCores;
        int level;
    };

    struct GroupStats {
        int runningFrames;
        int deadFrames;
        int dependFrames;
        int waitingFrames;
        int pendingJobs;
        float reservedCores;
    };

    class Group {
        GroupData data;
        GroupStats stats;
        GroupInterface *proxy;
    };

    class NestedGroup extends Group {
        NestedGroup parent;
        NestedGroupSeq groups;
        NestedJobSeq jobs;
    };

    /**
    * Allocation
    * An Allocation is the top level resource object.  All hosts are assigned
    * to an allocation.
    */
    struct AllocationData {
        string name;
        string tag;
        string facility;
        bool billable;
    };

    /**
    * Statistics relevant to an allocation
    */
    struct AllocationStats {
        float cores;
        float availableCores;
        float idleCores;
        float runningCores;
        float lockedCores;
        int hosts;
        int lockedHosts;
        int downHosts;
    };

    interface AllocationInterface {
        /**
        * Returns all subscriptions for this allocation
        **/
        idempotent SubscriptionSeq getSubscriptions()
            throws ::SpiIce::SpiIceException;

        /**
        * Assigns a list of hosts to this allocation.
        **/
        idempotent void reparentHosts(HostProxySeq hosts)
            throws ::SpiIce::SpiIceException;

        /**
        * Set the allocation name
        **/
        idempotent void setName(string name)
            throws ::SpiIce::SpiIceException;

        /**
        * Set an allocation billable or not billable.
        **/
        idempotent void setBillable(bool value)
            throws ::SpiIce::SpiIceException;

        /**
        * Delete this allocation
        */
        void delete()
            throws ::SpiIce::SpiIceException;

       /**
       * Set the allocation tag.  Setting this will re-tag all
       * the hosts in this allocation.
       **/
       idempotent void setTag(string tag)
           throws ::SpiIce::SpiIceException;

       /**
       * Returns the list of hosts in this allocation
       **/
       idempotent HostSeq getHosts()
            throws ::SpiIce::SpiIceException;

       /**
       * Use HostSearchCriteria to find a list of hosts
       **/
       idempotent HostSeq findHosts(HostSearchCriteria r)
            throws ::SpiIce::SpiIceException;
    };

    class Allocation {
        AllocationData data;
        AllocationStats stats;
        AllocationInterface *proxy;
    };

    /**
    * Subscriptions
    * A subscription is what a show sets up when they want to use hosts in
    * an allocation.
    */
    struct SubscriptionData {
        string name;
        string showName;
        string facility;
        string allocationName;
        float size;
        float burst;
        float reservedCores;
    };

    interface SubscriptionInterface {

        idempotent void setSize(float cores)
            throws ::SpiIce::SpiIceException;

        idempotent void setBurst(float cores)
            throws ::SpiIce::SpiIceException;

        void delete()
            throws ::SpiIce::SpiIceException;
    };

    class Subscription {
        SubscriptionData data;
        SubscriptionInterface *proxy;
    };

    /**
    * Departments
    *
    * Each show usually has a few different departments.  Lighting,
    * Animation, FX, Hair, and Cloth are the most common. The default
    * department is generally the "Unknown" department. Department names
    * must be chosen from a list of allowed department names which are
    * setup with the AdminStatic interface. This makes the data much more
    * consistent when doing reports by department which is important because
    * department names are used for production reports.
    *
    * Departments get created automatically when the department name property
    * is set on a group.
    *
    * Using departments, its possible to add shot based cue priorities.  These
    * priorities, known as "tasks", can be Track-It managed, or manually
    * entered. Track-It managed tasks are added, updated, and removed
    * automatically by track it.  When using track-it managed tasks, you must
    * provide a minimum number of cores to split up amoung the active tasks.
    *
    */
    struct DepartmentData {
        string name;
        string dept;
        string tiTask;
        float minCores;
        bool tiManaged;
    };

    /**
    * Used for bulk task creation
    **/
    ["java:type:java.util.HashMap<String,Integer>:java.util.Map<String,Integer>"]
    dictionary<string,int> TaskMap;

    interface DepartmentInterface {

        /**
        * Sets the minumum number of cores for the department to manage
        * between its tasks.
        */
        idempotent void setManagedCores(float managedCores)
            throws ::SpiIce::SpiIceException;

        /**
        * Returns the list of tasks for this department.
        */
        idempotent TaskSeq getTasks()
            throws ::SpiIce::SpiIceException;

        /**
        * Adds a task to this department and return it
        */
        Task addTask(string shot, float minCores)
            throws ::SpiIce::SpiIceException;

        /**
        * Adds a map of tasks to this deparmtment and return them
        * as a list.  Offers a quick way to add many tasks with one
        * function.
        */
        TaskSeq addTasks(TaskMap tmap)
            throws ::SpiIce::SpiIceException;

        /**
        * Replaces a map of tasks.  If the task already exists its updated,
        * else its inserted.
        */
        TaskSeq replaceTasks(TaskMap tmap)
            throws ::SpiIce::SpiIceException;

        /**
        * Clears all tasks
        */
        idempotent void clearTasks()
            throws ::SpiIce::SpiIceException;

        /**
        * Enable Track-It management.  This will pull a task list from
        * Track-It and keep it synced.
        */
        void enableTiManaged(string tiTask, float managedCores)
            throws ::SpiIce::SpiIceException;

        /**
        * Disable Track-It management.  This will also clear all tasks.
        */
        void disableTiManaged()
            throws ::SpiIce::SpiIceException;

        /**
        * Clears all manual task adjustments to managed tasks.  This won't do
        * anything unless your using Ti Managed tasks.
        */
        idempotent void clearTaskAdjustments()
            throws ::SpiIce::SpiIceException;
    };

    class Department {
        DepartmentData data;
        DepartmentInterface *proxy;
    };

    /**
    * Tasks
    * Tasks are shot priorities for a specific dept
    **/
    struct TaskData {
        string shot;
        string dept;
        float minCores;
        float adjustCores;
    };

    interface TaskInterface {
        /**
        * Sets the minimum number of cores.  If the task is being managed,
        * then the min core value is adjusted but the original is not changed.
        */
        idempotent void setMinCores(float minCores)
            throws ::SpiIce::SpiIceException;

        /**
        * Clear any min core adjustments that have been made
        */
        idempotent void clearAdjustment()
            throws ::SpiIce::SpiIceException;

        /**
        * Removes the task.  If the department is managed the task is likely
        * to come back upon the next update.
        **/
        void delete()
            throws ::SpiIce::SpiIceException;
    };

    class Task {
        TaskData data;
        TaskInterface *proxy;
    };

    /**
    * Show
    * Shows are the top level object for work.
    */
    struct ShowData {
        string name;
        float defaultMinCores;
        float defaultMaxCores;
        string commentEmail;
        bool bookingEnabled;
        bool dispatchEnabled;
        bool active;
    };

    struct ShowStats {
        int runningFrames;
        int deadFrames;
        int pendingFrames;
        int pendingJobs;
        long createdJobCount;
        long createdFrameCount;
        long renderedFrameCount;
        long failedFrameCount;
        float reservedCores;
    };

    interface ShowInterface {
        /* creates a new subscription */
        Subscription createSubscription
            (AllocationInterface *alloc, float size, float burst)
            throws ::SpiIce::SpiIceException;

        /* returns a list of a shows subscriptions */
        idempotent SubscriptionSeq getSubscriptions()
            throws ::SpiIce::SpiIceException;

        /* returns a list of job groups */
        idempotent GroupSeq getGroups()
            throws ::SpiIce::SpiIceException;

        /* returns the root group */
        idempotent Group getRootGroup()
            throws ::SpiIce::SpiIceException;

        /* returns a flat list of jobs */
        idempotent JobSeq getJobs()
            throws ::SpiIce::SpiIceException;

        /* returns the show's job whiteboard */
        idempotent NestedGroup getJobWhiteboard()
            throws ::SpiIce::SpiIceException;

        /* sets a show's default min procs */
        idempotent void
            setDefaultMinCores(float minCores)
            throws ::SpiIce::SpiIceException;

         /* sets a show's default max procs */
        idempotent void
            setDefaultMaxCores(float maxCores)
            throws ::SpiIce::SpiIceException;

        /* Grabs a list of show filters */
        idempotent FilterSeq getFilters()
             throws ::SpiIce::SpiIceException;

        /* finds a filter by name */
        idempotent Filter findFilter(string name)
             throws ::SpiIce::SpiIceException;

        /**
        * Creates a new empty filter
        **/
        Filter createFilter(string name)
             throws ::SpiIce::SpiIceException;

        /**
        * Returns the department manager for the specified department
        **/
       idempotent Department getDepartment(string department)
            throws ::SpiIce::SpiIceException;

        /**
        * Returns a list of all active departments
        **/
        idempotent DepartmentSeq getDepartments()
            throws ::SpiIce::SpiIceException;

        /**
        * Enables/disables automated resource assignment.  If this
        * is disabled no new resources will be assigned but existing
        * resources will continue to dispatch.
        **/
        idempotent void enableBooking(bool enabled)
            throws ::SpiIce::SpiIceException;

        /**
        * Enables/disables job dispatching.  If this is disabled
        * then new resources are assigned but existing resources
        * are always unbooked after each completed frame.
        **/
        idempotent void enableDispatching(bool enabled)
            throws ::SpiIce::SpiIceException;

        /**
        * Deletes a show if no jobs were ever launched for the show
        **/
        void delete()
            throws ::SpiIce::SpiIceException;

        /**
        * Return all the host deeds for the specified show.
        **/
        DeedSeq getDeeds()
            throws ::SpiIce::SpiIceException;

        /**
        * Create a new owner.
        **/
        Owner createOwner(string name)
            throws ::SpiIce::SpiIceException;

        /*
        * Set a show's active to enabled/disabled. Active shows
        * can be queried using the getActiveShows() method.
        */
        void setActive(bool value)
            throws ::SpiIce::SpiIceException;

        /**
        * Get a list of service overrides for this show.
        **/
        idempotent ServiceOverrideSeq getServiceOverrides()
            throws ::SpiIce::SpiIceException;

        /**
        * Get a service override based on its name or id.
        **/
        idempotent ServiceOverride getServiceOverride(string name)
            throws ::SpiIce::SpiIceException;

        /**
        * Add a new service overrides.
        **/
        ServiceOverride createServiceOverride(ServiceData service)
            throws ::SpiIce::SpiIceException;

        /**
        * If set, all comments on a show are echoed to the given
        * list of email addresses.
        **/
        idempotent void setCommentEmail(string email)
             throws ::SpiIce::SpiIceException;

    };

    class Show {
        ShowData data;
        ShowStats stats;
        ShowInterface *proxy;
    };

    /**
    *
    * A struct that contains server specific performance numbers
    **/
    struct SystemStats {

        int manageWaiting;
        int manageRemainingCapacity;
        int manageThreads;
        long manageExecuted;
        long manageRejected;

        int dispatchWaiting;
        int dispatchRemainingCapacity;
        int dispatchThreads;
        long dispatchExecuted;
        long dispatchRejected;

        int reportWaiting;
        int reportRemainingCapacity;
        int reportThreads;
        long reportExecuted;
        long reportRejected;

        int bookingWaiting;
        int bookingRemainingCapacity;
        int bookingThreads;
        int bookingSleepMillis;
        long bookingExecuted;
        long bookingRejected;

        long hostBalanceSuccess;
        long hostBalanceFailed;
        long killedOffenderProcs;
        long killedOomProcs;
        long clearedProcs;
        long bookingErrors;
        long bookingRetries;
        long bookedProcs;

        long reqForData;
        long reqForFunction;
        long reqErrors;

        long unbookedProcs;
        long pickedUpCores;
        long strandedCores;
    };

    /*
    * WhiteboardStatic allows you to easily jump to just about anywhere
    * in the cue entity heirarchy by supplying easy methods for finding
    * cue data.
    *
    */
    interface CueStatic
    {

        /**
        * Return a the list of default services.
        **/
        idempotent ServiceSeq getDefaultServices()
            throws ::SpiIce::SpiIceException;
        /**
        * Return the given service using its name or unique id.
        **/
        idempotent Service getService(string name)
            throws ::SpiIce::SpiIceException;

        /**
        * Create a new service.
        **/
        Service createService(ServiceData data)
            throws ::SpiIce::SpiIceException;

       /*******************************************************************/

        /**
        * returns the current server statistics
        **/
        idempotent SystemStats getSystemStats()
            throws ::SpiIce::SpiIceException;

       /*******************************************************************/

        /**
        * Creates a show with the specified name and returns it.
        **/
        Show createShow(string name)
            throws ::SpiIce::SpiIceException;

        /**
        * Returns a list of all shows
        **/
        idempotent ShowSeq getShows()
            throws ::SpiIce::SpiIceException;

        /**
        * Returns a list of all active shows.
        **/
        idempotent ShowSeq getActiveShows()
            throws ::SpiIce::SpiIceException;

        /**
        * Find a show with the specified name.
        **/
        Show findShow(string name)
            throws ::SpiIce::SpiIceException;

        /*******************************************************************/

        idempotent Filter findFilter(string show, string name)
             throws ::SpiIce::SpiIceException;

       /*******************************************************************/

        void addDepartmentName(string name)
            throws ::SpiIce::SpiIceException;


        void removeDepartmentName(string name)
            throws ::SpiIce::SpiIceException;


        idempotent CueIce::StringSeq getDepartmentNames()
            throws ::SpiIce::SpiIceException;

       /*******************************************************************/

        /**
        * Finds a group by show name and group
        **/
        idempotent Group findGroup(string show, string name)
            throws ::SpiIce::SpiIceException;

        /**
        * Gets a group by its id
        **/
        idempotent Group getGroup(string id)
            throws ::SpiIce::SpiIceException;

       /*******************************************************************/

        /**
        * Returns true if the job is in the pending state
        * the cue.
        **/
        idempotent bool isJobPending(string name)
            throws ::SpiIce::SpiIceException;

        /**
        * Finds a pending job using the job name
        **/
        idempotent Job findJob(string name)
            throws ::SpiIce::SpiIceException;

        /**
        * Finds a pending job using the job name
        **/
        idempotent Job getJob(string id)
            throws ::SpiIce::SpiIceException;

        /**
        * Returns a list of jobs based on specified criteria
        **/
        idempotent JobSeq getJobs(JobSearchCriteria r)
            throws ::SpiIce::SpiIceException;

        /**
        * Returns a sequence of job names using search criteria
        **/
        idempotent CueIce::StringSeq getJobNames(JobSearchCriteria criteria)
            throws ::SpiIce::SpiIceException;

        /**
        * Launches a job spec and returns an array of launched jobs.
        * Waits for jobs to be commited to DB.  This might time
        * out before jobs are launched.
        **/
        JobSeq launchSpecAndWait(string spec)
            throws ::SpiIce::SpiIceException;

        /**
        * Launches as a job spec and returns an array of job names that are
        * being launched. This method returns immediately after basic checks.
        * The job could fail to launch of a DB error occurs but that is
        * rare.
        **/
        CueIce::StringSeq launchSpec(string spec)
            throws ::SpiIce::SpiIceException;

       /*******************************************************************/

        /**
        * Finds a layer in a pending job from its unique ID
        **/
        idempotent Layer getLayer(string id)
            throws ::SpiIce::SpiIceException;

        /**
        * Finds a layer in a pending job based the job and layer name
        **/
        idempotent Layer findLayer(string job, string layer)
            throws ::SpiIce::SpiIceException;

       /*******************************************************************/

        /**
        * Get a frame from its unique id
        **/
        idempotent Frame getFrame(string id)
            throws ::SpiIce::SpiIceException;

        /**
        * Finds a frame in a pending job based on the job, layer,
        * and frame number.
        **/
        idempotent Frame findFrame(string job, string layer, int frame)
            throws ::SpiIce::SpiIceException;

        /**
        * Get frames using FrameSearchCritiera
        **/
        idempotent FrameSeq getFrames(string job, FrameSearchCriteria r)
            throws ::SpiIce::SpiIceException;

       /*******************************************************************/

        /**
        * Returns a dependency by its unqiue ID
        **/
        idempotent Depend getDepend(string id)
            throws ::SpiIce::SpiIceException;

       /*******************************************************************/

        idempotent AllocationSeq getAllocations()
            throws ::SpiIce::SpiIceException;

        idempotent Allocation findAllocation(string name)
            throws ::SpiIce::SpiIceException;

        idempotent Allocation getAllocation(string id)
            throws ::SpiIce::SpiIceException;

       /*******************************************************************/

        idempotent Subscription findSubscription(string name)
            throws ::SpiIce::SpiIceException;

        idempotent Subscription getSubscription(string id)
            throws ::SpiIce::SpiIceException;

       /*******************************************************************/

        idempotent NestedHostSeq getHostWhiteboard()
            throws ::SpiIce::SpiIceException;

        idempotent Host findHost(string name)
            throws ::SpiIce::SpiIceException;

        idempotent Host getHost(string id)
            throws ::SpiIce::SpiIceException;

        idempotent HostSeq getHosts(HostSearchCriteria r)
            throws ::SpiIce::SpiIceException;

        /*******************************************************************/

        idempotent ProcSeq getProcs(ProcSearchCriteria r)
            throws ::SpiIce::SpiIceException;

        /**
        * Unbooks procs that match the ProcSearchCriteria.  This request
        * can span jobs, shows, allocations, hosts etc. Set kill to true
        * if the running frames should immediately be killed.
        *
        * @param r - the search criteria
        *
        * @return - the number of procs unbooked
        *
        * @throws ::SpiIce::SpiIceException if an error occurs
        **/
        int unbookProcs(ProcSearchCriteria r, bool kill)
            throws ::SpiIce::SpiIceException;

        /**
        * Unbooks procs that match the ProcSearchCriteria and books them
        * on the specified list of jobs, assuming those jobs have layers
        * that can take the procs.
        *
        * If the kill boolean is set to true, the operation happens
        * immediately. If false, the proc will move after it finishes its
        * current frame.
        *
        * @param r - the search criteria
        * @param jobs - the target jobs
        * @param kill - if true, the transfer is done immediately.
        * @return - the number of procs that were unbooked
        *
        **/
        int unbookToJob(ProcSearchCriteria r, JobProxySeq jobs, bool kill)
            throws ::SpiIce::SpiIceException;

        /**
        * Unbooks procs that match the ProcSearchCriteria and books them
        * on the specified group, assuming the group has layers
        * that can take the procs.
        *
        * If the kill boolean is set to true, the operation happens
        * immediately. If false, the proc will move after it finishes its
        * current frame.
        *
        * @param r - the search criteria
        * @param group - the target group
        * @param kill - if true, the transfer is done immediately.
        * @return - the number of procs that were unbooked
        *
        **/
        int unbookToGroup
            (ProcSearchCriteria r, GroupInterface *proxy, bool kill)
            throws ::SpiIce::SpiIceException;

        /*******************************************************************/

        /**
        * Return an Owner record by name, id, or email.
        **/
        Owner getOwner(string identifier)
            throws ::SpiIce::SpiIceException;
    };
};

#endif

/*
 * Local Variables:
 * mode: c++
 * End:
 */
