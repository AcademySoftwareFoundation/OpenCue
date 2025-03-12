
/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */

package com.imageworks.spcue.servlet;

import com.imageworks.spcue.ShowEntity;
import com.imageworks.spcue.dao.criteria.JobSearchInterface;
import com.imageworks.spcue.dao.criteria.postgres.JobSearch;
import com.imageworks.spcue.grpc.job.JobSeq;
import com.imageworks.spcue.servant.CueStatic;
import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.LogManager;
import org.springframework.core.env.Environment;
import org.springframework.web.servlet.FrameworkServlet;

import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Objects;
import io.sentry.Sentry;

/**
 * HealthCheckServlet returns 200 if the app is healthy and 500 if not.
 */
@SuppressWarnings("serial")
public class HealthCheckServlet extends FrameworkServlet {

    private static final Logger logger = LogManager.getLogger(HealthCheckServlet.class);
    private CueStatic cueStatic;
    private Environment env;

    private enum HealthStatus {
        SERVER_ERROR, DISPATCH_QUEUE_UNHEALTHY, MANAGE_QUEUE_UNHEALTHY, REPORT_QUEUE_UNHEALTHY, BOOKING_QUEUE_UNHEALTHY, JOB_QUERY_ERROR
    }

    @Override
    public void initFrameworkServlet() throws ServletException {
        this.cueStatic = (CueStatic) Objects.requireNonNull(this.getWebApplicationContext())
                .getBean("cueStaticServant");
        this.env = (Environment) Objects.requireNonNull(this.getWebApplicationContext())
                .getBean("environment");
    }

    private ArrayList<HealthStatus> getHealthStatus() {
        ArrayList<HealthStatus> statusList = new ArrayList<HealthStatus>();

        if (this.cueStatic == null) {
            statusList.add(HealthStatus.SERVER_ERROR);
        } else {
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
            // Run get jobs, if it crashes, set error, if it takes longer than expected,
            // the caller (HEALTHCHECK) will timeout
            try {
                getJobs();
            } catch (RuntimeException re) {
                Sentry.captureException(re);
                statusList.add(HealthStatus.JOB_QUERY_ERROR);
            }
        }
        return statusList;
    }

    private void getJobs() {
        if (this.cueStatic != null && this.env != null) {
            // Defaults to testing show, which is added as part of the seeding data script
            String defaultShow =
                    env.getProperty("protected_shows", String.class, "testing").split(",")[0];
            ShowEntity s = new ShowEntity();
            s.name = defaultShow;
            JobSearchInterface js = new JobSearch();
            js.filterByShow(s);

            // GetJobs will throw an exception if there's a problem getting
            // data from the database
            JobSeq jobs = this.cueStatic.getWhiteboard().getJobs(js);
        }
    }

    @Override
    protected void doService(HttpServletRequest request, HttpServletResponse response)
            throws Exception {
        logger.info("HealthCheckServlet: Received request");
        try {
            ArrayList<HealthStatus> statusList = getHealthStatus();
            if (!statusList.isEmpty()) {
                response.setStatus(500);
                StringBuilder out = new StringBuilder("FAILED: ");
                for (HealthStatus status : statusList) {
                    out.append(status.name());
                    out.append(" ");
                }
                Sentry.captureMessage("Healthcheck failure: " + out);

                sendResponse(response, out.toString());
            } else {
                sendResponse(response, "SUCCESS");
            }
        } catch (Exception e) {
            logger.error("Unexpected error", e);
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
