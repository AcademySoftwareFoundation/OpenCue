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


#ifndef RQD_ICE
#define RQD_ICE

#include <spi_exceptions.ice>
#include <spi_types.ice>
#include <cue_types.ice>

[["java:package:com.imageworks.spcue"]]
[["python:package:cue"]]

module RqdIce
{
    ["java:type:java.util.ArrayList<Integer>:java.util.List<Integer>"]
    sequence<int> IntSeq;

    ["java:type:java.util.ArrayList<String>:java.util.List<String>"]
    sequence<string> StringSeq;

    ["java:type:java.util.HashMap<String,String>:java.util.Map<String,String>"]
    dictionary<string,string> StringMap;

    /*
    * Exceptions
    */
    exception RqdIceException
        extends ::SpiIce::SpiIceException {
    };

    /*
    * Thrown when RQD cannot reserve cores for any reason, be it locked or
    * already in use.
    */
    exception CoreReservationFailureException
        extends RqdIceException {
    };

    /*
    * Thrown when RQD has a problem setting up the frame launch.
    * This may be due to a host configuration problem
    */
    exception FrameSetupFailureException
        extends RqdIceException {
    };

    /*
    * Thrown when RQD detects an invalid UID in a run frame request
    */
    exception InvalidUserException
        extends RqdIceException {
    };

    /*
    * Thrown when RQD cannot run a frame because its already running a frame with
    * the same ID.
    */
    exception DuplicateFrameViolationException
        extends RqdIceException {
    };

    /*---------------------------------------------------------------------------*/

    /*
    * RenderHost contains all the host-centric data sent in by RQD
    * This data is used to create/update a host entry on the cue side.
    */
    struct RenderHost {

        string name;
        /*
        * NIMBY is enabled when the machine is in run level 5. This is a good
        * indication that the machine is a desktop.
        */
        bool nimbyEnabled;

        /* if nimby has locked the host due to user activity*/
        bool nimbyLocked;

        /* The name of the facility that the host is in*/
        string facility;

        /* the number of physical procs on this machine */
        int numProcs;

        /* the number of cores per proc */
        int coresPerProc;

        /* the total size of the swap in kB*/
        int totalSwap;

        /* the total size of the main memory pool in kB*/
        int totalMem;

        /* the total size of MCP in kB*/
        int totalMcp;

        /* the current amount of free swap in kB*/
        int freeSwap;

        /* the current amount of free memory in kB*/
        int freeMem;

        /* the current amount of free MCP in kB*/
        int freeMcp;

        /* the current load on the proc */
        int load;

        /* the time the proc was booted*/
        int bootTime;

        /* an array of default tags that are added to the host record */
        StringSeq tags;

        /* hardare state for the host */
        CueIce::HardwareState state;

        /* additional data can be provided about the host */
        StringMap attributes;
    };

    /*
    * RenderHosts have CoreDetail.
    */
    struct CoreDetail {
        int totalCores;
        int idleCores;
        int lockedCores;
        int bookedCores;
    };

    /*
    * To run a frame, a client (cuebot) must create a RunFrame object and
    * call RqdStatic.launchFrame(frame).
    */
    struct RunFrame {
        string resourceId;
        string jobId;
        string jobName;
        string frameId;
        string frameName;
        string layerId;
        string command;
        string userName;
        string logDir;
        string show;
        string shot;
        long startTime;
        int uid;
        int numCores;
        bool ignoreNimby;
        StringMap environment;
        StringMap attributes;
    };

    /*
    * Contains what RQD currently has running.
    */
    struct RunningFrameInfo {
        string resourceId;
        string jobId;
        string jobName;
        string frameId;
        string frameName;
        string layerId;
        int numCores;
        long startTime;
        long maxRss; // kB
        long rss; // kB
        long maxVsize; // kB
        long vsize; // kB
        /* additional data can be provided about the running frame */
        StringMap attributes;
    };

    ["java:type:java.util.ArrayList<RunningFrameInfo>:java.util.List<RunningFrameInfo>"]
    sequence<RunningFrameInfo> RunningFrameInfoSeq;

    /*
    * Host Report
    * This report is sent every N seconds from RQD so we know the proc
    * is still alive and running what we think is running.
    */

    struct HostReport {
        RenderHost host;
        RunningFrameInfoSeq frames;
        CoreDetail coreInfo;
    };

    /*
    * Boot Report
    * The boot report is sent when RQD starts up.  RQD should not accept
    * any frames until it has successfully sent in a boot report.
    */
    struct BootReport {
        RenderHost host;
        CoreDetail coreInfo;
    };

    /*
    * FrameCompleteReport
    * This report is sent when a frame is completed.
    */
    struct FrameCompleteReport {
        RenderHost host;
        RunningFrameInfo frame;
        int exitStatus;
        int exitSignal;
        int runTime;
    };

    /*
    * Implemented by the Rqd server.
    * Called by cuebot and tools.
    */
    interface RunningFrame
    {
        idempotent RunningFrameInfo
        status()
            throws ::SpiIce::SpiIceException;

        idempotent void
        kill(string message)
            throws ::SpiIce::SpiIceException;
    };

    /*
    * Implemented by the Rqd server.
    * Called by cuebot and tools.
    */
    interface RqdStatic
    {
        void launchFrame(RunFrame frame)
            throws ::SpiIce::SpiIceException;

        HostReport reportStatus()
            throws ::SpiIce::SpiIceException;

        RunningFrame *
        getRunningFrame(string frameId)
            throws ::SpiIce::SpiIceException;

        idempotent void shutdownRqdNow()
            throws ::SpiIce::SpiIceException;

        idempotent void shutdownRqdIdle()
            throws ::SpiIce::SpiIceException;

        idempotent void restartRqdNow()
            throws ::SpiIce::SpiIceException;

        idempotent void restartRqdIdle()
            throws ::SpiIce::SpiIceException;

        idempotent void rebootNow()
            throws ::SpiIce::SpiIceException;

        idempotent void rebootIdle()
            throws ::SpiIce::SpiIceException;

        idempotent void nimbyOn()
            throws ::SpiIce::SpiIceException;

        idempotent void nimbyOff()
            throws ::SpiIce::SpiIceException;

        void lock(int cores)
            throws ::SpiIce::SpiIceException;

        idempotent void lockAll()
            throws ::SpiIce::SpiIceException;

        void unlock(int cores)
            throws ::SpiIce::SpiIceException;

        idempotent void unlockAll()
            throws ::SpiIce::SpiIceException;
    };
};

#endif

/*
* Local Variables:
* mode: c++
* End:
*/
