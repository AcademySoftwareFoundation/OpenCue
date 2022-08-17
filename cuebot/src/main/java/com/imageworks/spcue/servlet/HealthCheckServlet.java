
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



package com.imageworks.spcue.servlet;

import com.imageworks.spcue.servant.CueStatic;
import org.apache.log4j.Logger;
import org.springframework.web.servlet.FrameworkServlet;

import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Objects;

/**
 * HealthCheckServlet returns 200 if the app is healthy and 500 if not.
 */
@SuppressWarnings("serial")
public class HealthCheckServlet extends FrameworkServlet {

    private static final Logger logger = Logger.getLogger(HealthCheckServlet.class);

    private CueStatic cueStatic;

    private enum HealthStatus {
        SERVER_ERROR,
        DISPATCH_QUEUE_UNHEALTHY,
        MANAGE_QUEUE_UNHEALTHY,
        REPORT_QUEUE_UNHEALTHY,
        BOOKING_QUEUE_UNHEALTHY
    }

    @Override
    public void initFrameworkServlet() throws ServletException {
        this.cueStatic = (CueStatic)
            Objects.requireNonNull(this.getWebApplicationContext()).getBean("cueStaticServant");
    }

    private ArrayList<HealthStatus> getHealthStatus() {
        ArrayList<HealthStatus> statusList = new ArrayList<HealthStatus>();

        if (this.cueStatic == null) {
            statusList.add(HealthStatus.SERVER_ERROR);
        }
        else {
            // Check queue capacity
            if (!this.cueStatic.isDispatchQueueHealthy()) {
                statusList.add(HealthStatus.DISPATCH_QUEUE_UNHEALTHY);
            }
            if (!this.cueStatic.isManageQueueHealthy()) {
                statusList.add(HealthStatus.MANAGE_QUEUE_UNHEALTHY);
            }
            if (!this.cueStatic.isReportQueueHealthy()) {
                statusList.add(HealthStatus.REPORT_QUEUE_UNHEALTHY);
            }
            if (!this.cueStatic.isBookingQueueHealthy()) {
                statusList.add(HealthStatus.BOOKING_QUEUE_UNHEALTHY);
            }
        }

        return statusList;
    }

    @Override
    protected void doService(HttpServletRequest request,
            HttpServletResponse response) throws Exception {

        try {
            ArrayList<HealthStatus> statusList = getHealthStatus();
            if (!statusList.isEmpty()) {
                response.setStatus(500);
                StringBuilder out = new StringBuilder("FAILED: ");
                for(HealthStatus status : statusList) {
                    out.append(status.name());
                    out.append(" ");
                }

                sendResponse(response, out.toString());
            }
            else
            {
                sendResponse(response, "SUCCESS");
            }
        }
        catch (Exception e) {
            logger.debug("Misc error", e);
            response.setStatus(500);
            sendResponse(response, "FAILED " + e.getMessage());
        }
    }

    private void sendResponse(HttpServletResponse response, String message) {
        response.setContentLength(message.length());
        try {
            response.getOutputStream().println(message);
        } catch (IOException e) {
            // failed to send response, just eat it.
        }
    }
}

