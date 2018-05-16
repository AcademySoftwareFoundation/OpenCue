
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



package com.imageworks.spcue.servant;

import org.apache.log4j.Logger;

import Ice.Current;

import com.imageworks.common.SpiIce.SpiIceException;
import com.imageworks.common.spring.remoting.SpiIceExceptionMinimalTemplate;
import com.imageworks.spcue.CueIce._RqdReportStaticDisp;
import com.imageworks.spcue.RqdIce.BootReport;
import com.imageworks.spcue.RqdIce.FrameCompleteReport;
import com.imageworks.spcue.RqdIce.HostReport;
import com.imageworks.spcue.dispatcher.FrameCompleteHandler;
import com.imageworks.spcue.dispatcher.HostReportHandler;

public class RqdReportStaticI extends _RqdReportStaticDisp {

    private FrameCompleteHandler frameCompleteHandler;
    private HostReportHandler hostReportHandler;

    @SuppressWarnings("unused")
    private static final Logger logger = Logger.getLogger(RqdReportStaticI.class);

    public RqdReportStaticI() {  }

    public void reportRqdStartup(final BootReport report, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                hostReportHandler.queueBootReport(report);
            }
        }.execute();
    }

    public void reportRunningFrameCompletion(final FrameCompleteReport report, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                frameCompleteHandler.handleFrameCompleteReport(report);
            }
        }.execute();
    }

    public void reportStatus(final HostReport report, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                hostReportHandler.queueHostReport(report);
            }
        }.execute();
    }

    public FrameCompleteHandler getFrameCompleteHandler() {
        return frameCompleteHandler;
    }

    public void setFrameCompleteHandler(FrameCompleteHandler frameCompleteHandler) {
        this.frameCompleteHandler = frameCompleteHandler;
    }

    public HostReportHandler getHostReportHandler() {
        return hostReportHandler;
    }

    public void setHostReportHandler(HostReportHandler hostReportHandler) {
        this.hostReportHandler = hostReportHandler;
    }
}

