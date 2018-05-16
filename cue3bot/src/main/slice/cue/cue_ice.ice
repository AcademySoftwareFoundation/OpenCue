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

#ifndef CUE_ICE
#define CUE_ICE

#include <spi_exceptions.ice>
#include <spi_types.ice>
#include <cue_types.ice>
#include <rqd_ice.ice>

[["java:package:com.imageworks.spcue"]]
[["python:package:cue"]]

module CueIce {

    /*
    *  Interface to handle RQD pings.
    */
    interface RqdReportStatic
    {
        /*
        * send in when RQD starts up to announce new idle procs
        * to the cue.
        */
        void reportRqdStartup(RqdIce::BootReport report)
            throws ::SpiIce::SpiIceException;

        /*
        * An incremental status report sent by RQD
        */
        void reportStatus(RqdIce::HostReport report)
            throws ::SpiIce::SpiIceException;

        /*
        * reports in a running frame
        */
        void reportRunningFrameCompletion(RqdIce::FrameCompleteReport report)
            throws ::SpiIce::SpiIceException;
    };

    /*
    *  Interface to handle RQD pings.
    */
    interface RqdReportStaticAMI
    {
        /*
        * send in when RQD starts up to announce new idle procs
        * to the cue.
        */
        ["ami"]
        void reportRqdStartup(RqdIce::BootReport report)
            throws ::SpiIce::SpiIceException;

        /*
        * An incremental status report sent by RQD
        */
        ["ami"]
        void reportStatus(RqdIce::HostReport report)
            throws ::SpiIce::SpiIceException;

        /*
        * reports in a running frame
        */
        ["ami"]
        void reportRunningFrameCompletion(RqdIce::FrameCompleteReport report)
            throws ::SpiIce::SpiIceException;
    };
};

#endif

/*
 * Local Variables:
 * mode: c++
 * End:
 */
