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


#ifndef CUE_TYPES_ICE
#define CUE_TYPES_ICE

#include <spi_exceptions.ice>
#include <spi_types.ice>

[["java:package:com.imageworks.spcue"]]
[["python:package:cue"]]

module CueIce {

    /*
    * Exceptions
    */

    /*
    * Base exception for exceptions throw from RQD to the cuebot.
    */
    exception CueIceException extends
        ::SpiIce::SpiIceException {
    };

    /*
    * Thrown when the RQD report fails and must be retried.
    */
    exception RqdReportFailureException
        extends CueIceException {
    };

    /**
    * Thrown back to client when a entity cannot be found
    */
    exception EntityNotFoundException
        extends CueIceException {
    };

    /**
    * Entity creation error is thrown when there is
    * an error creating a new entity.
    */
    exception EntityCreationErrorException
        extends CueIceException {
    };

    /*
    * Basic Sequences
    */

    ["java:type:java.util.ArrayList<Integer>:java.util.List<Integer>"]
    sequence<int> IntSeq;

    ["java:type:java.util.ArrayList<String>:java.util.List<String>"]
    sequence<string> StringSeq;

    ["java:type:java.util.HashSet<String>:java.util.Set<String>"]
    sequence<string> StringSet;

    ["java:type:java.util.HashMap<String,String>:java.util.Map<String,String>"]
    dictionary<string,string> StringMap;

     /*
    * Enumerations
    */

    /*
    * Defines the type of dependency.  The names are pretty much self
    * explanatory except for FrameByFrame, which is basically a hard
    * depend.
    */
    enum DependType {
        JobOnJob,
        JobOnLayer,
        JobOnFrame,
        LayerOnJob,
        LayerOnLayer,
        LayerOnFrame,
        FrameOnJob,
        FrameOnLayer,
        FrameOnFrame,
        FrameByFrame,
        PreviousFrame,
        LayerOnSimFrame
    };

    /**
    *
    * The depend visibility.  If the depend-er-job and the depend-on-job is
    * the same, the depend is Internal, if not, its External.
    **/
    enum DependTarget {
        Internal,
        External,
        AnyTarget
    };

    /*
    * The LayerType determines the type of the layer. A proc will not run
    * frames from different layers UNLESS the layer type is PreProcess or
    * PostProcess.  This gives us the ability to run all the preprocesses
    * on one proc and all the post processes on one proc.
    *
    * There is no specific dispatch ordef for layer types.  You will need
    * to setup dependencies.
    */
    enum LayerType {
        Pre,
        Post,
        Render,
        Util
    };

    /*
    * Defines the possible states of a frame.
    */
    enum FrameState {
        /* Ok to be dispatched */
        Waiting,
        /* Reserved to be dispatched */
        Setup,
        /* Running on a render proc */
        Running,
        /* Frame completed successfully */
        Succeeded,
        /* Frame is waiting on a dependency */
        Depend,
        /* Frame is dead,which means it has died N times */
        Dead,
        /* Frame is eaten, acts like the frame has succeeded */
        Eaten,
        /* Frame is checkpointing */
        Checkpoint
    };

    // A sequence of frame states
    ["java:type:java.util.ArrayList<com.imageworks.spcue.CueIce.FrameState>:java.util.List<com.imageworks.spcue.CueIce.FrameState>"]
    sequence<FrameState> FrameStateSeq;


    /*
    * Defines the possible states of a job.
    */
    enum JobState {
        /* job is running */
        Pending,
        /* the job has completed */
        Finished,
        /* the job is in the process of starting up */
        Startup,
        /* the job is in the process of shutting down */
        Shutdown,
        /* the job is a post job and is waiting to go pending */
        Posted
    };

    // A sequence of job states
    ["java:type:java.util.ArrayList<com.imageworks.spcue.CueIce.JobState>:java.util.List<com.imageworks.spcue.CueIce.JobState>"]
    sequence<JobState> JobStateSeq;

    /*
    * Defines the possible states for a core or proc
    */
    enum RunState {
        /* enity is idle, which means it can be booked */
        Idle,
        /* entity is booked, which means its in use on a render proc */
        Booked
    };

    /*
    * Defines the possible states of hardware
    */
    enum HardwareState {
        Up,
        Down,
        Rebooting,
        RebootWhenIdle,
        Repair
    };

    /**
    * Define the possible checkpoint states for a frame.
    **/
    enum CheckpointState {
        Disabled,
        Enabled,
        Copying,
        Complete
    };

    /**
    * A sequence of hardware states
    **/
    ["java:type:java.util.ArrayList<com.imageworks.spcue.CueIce.HardwareState>:java.util.List<com.imageworks.spcue.CueIce.HardwareState>"]
    sequence<HardwareState> HardwareStateSeq;

    /**
    * ThreadMode defines the available hardware threading modes.
    **/
    enum ThreadMode {
        /**
        * Auto determines the number of threads to use automatically
        * based on the amount of memory used by the frame.
        **/
        Auto,

        /**
        * All always uses all of the cores available on the proc.
        * These hosts are always booked on threadable layers.
        **/
        All,

        /**
        * All mode during the day, auto-mode at night.
        **/
        Variable
    };

    /*
    * A host level propert that defines the lock state of the host.
    */
    enum LockState {
        Open,
        Locked,
        NimbyLocked
    };

    /**
    * Job filters can be one of two types, match any or match all.  Match any
    * will return true if only 1 thing matches while match all requires all
    * matchers to return true.
    */
    enum FilterType {
        MatchAny,
        MatchAll
    };

    /**
    * The subject to match on.
    */
    enum MatchSubject {
        JobName,
        Show,
        Shot,
        User,
        ServiceName,
        Priority,
        Facility,
        LayerName
    };

    /**
    * Match type
    */
    enum MatchType {
        Contains,
        DoesNotContain,
        Is,
        IsNot,
        Regex,
        BeginsWith,
        EndsWith
    };

    /**
    * The actions that are taken after a filter match.
    * (Add new ActionTypes to the end of the list)
    */
    enum ActionType {
        MoveJobToGroup,
        PauseJob,
        SetJobMinCores,
        SetJobMaxCores,
        StopProcessing,
        SetJobPriority,

        /**
        * Sets all layer tags for any layer with the type "Render"
        **/
        SetAllRenderLayerTags,
        /**
        * Sets all layer minimum memory for any layer with the type "Render"
        **/
        SetAllRenderLayerMemory,
        /**
        * Sets all min cores for any layer with the type "Render"
        **/
        SetAllRenderLayerCores,

        /**
        * Set memory optimizer
        **/
        SetMemoryOptimizer
    };

    enum ActionValueType {
        GroupType,
        StringType,
        IntegerType,
        FloatType,
        BooleanType,
        NoneType
    };


    enum HostTagType {
        Manual,
        Hardware,
        Alloc,
        Hostname
    };

    /**
    * Proc redirects can have two different types
    * of destinations, jobs and groups.
    **/
    enum RedirectType {
        JobRedirect,
        GroupRedirect
    };

    /**
    * Used for reordering frames.
    **/
    enum Order {
        /* Moves frames to the lowest dispatch order */
        First,
        /* Moves frames to the last dispatch order */
        Last,
        /* Reverses the dispatch order */
        Reverse
    };

    /**
    * The type of render partition.
    **/
    enum RenderPartitionType {
        JobPartition,
        LayerPartition,
        FramePartition
    };

    /**
    * These frame exit status values are used to trigger
    * special dispatcher behavior.  They are greater than 255
    * so they don't collide with any real exit status values used
    * by applications running on the cue.
    **/
    // The frame was a success
    const int FrameExitStatusSuccess = 0;
    // The frame should not be retried
    const int FrameExitStatusNoRetry = 256;
    // Retries should not be incremented
    const int FrameExitStatusSkipRetry = 286;
};

#endif
/*
 * Local Variables:
 * mode: c++
 * End:
 */
