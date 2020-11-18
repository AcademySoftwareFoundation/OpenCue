
/*
 * Copyright Contributors to the OpenCue Project
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



package com.imageworks.spcue.dispatcher.commands;

import com.imageworks.spcue.dispatcher.HostReportHandler;
import com.imageworks.spcue.grpc.report.BootReport;
import com.imageworks.spcue.grpc.report.HostReport;

/**
 * A command for handling a host report.
 *
 * @category command
 */
public class DispatchHandleHostReport implements Runnable {

    private HostReport hostReport;
    private boolean isBootReport;
    private HostReportHandler hostReportHandler;

    public volatile long reportTime = System.currentTimeMillis();

    public DispatchHandleHostReport(HostReport report, HostReportHandler rqdReportManager) {
        this.hostReport = report;
        this.isBootReport = false;
        this.hostReportHandler = rqdReportManager;
    }

    public DispatchHandleHostReport(BootReport report, HostReportHandler rqdReportManager) {
        HostReport hostReport = HostReport.newBuilder()
                .setHost(report.getHost())
                .setCoreInfo(report.getCoreInfo())
                .build();

        this.hostReport = hostReport;
        this.isBootReport = true;
        this.hostReportHandler = rqdReportManager;
    }

    public void run() {
        new DispatchCommandTemplate() {
            public void wrapDispatchCommand() {
                HostReport report = hostReportHandler
                        .getReportQueue()
                        .removePendingHostReport(getKey());
                if (report != null) {
                    hostReportHandler.handleHostReport(report, isBootReport, reportTime);
                } else {
                    // Host report has already been handled by another thread
                }
            }
        }.execute();
    }

    public HostReport getHostReport() {
        return hostReport;
    }

    public String getHostName() {
        return hostReport.getHost().getName();
    }

    public String getKey(){
        return this.getHostName() + "/" + (this.isBootReport ? "1" : "0");
    }
}

