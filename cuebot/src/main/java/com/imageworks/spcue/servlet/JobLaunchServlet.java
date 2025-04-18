
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

import java.io.IOException;
import java.util.Objects;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.LogManager;
import org.springframework.web.servlet.FrameworkServlet;

import com.imageworks.spcue.BuildableJob;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobSpec;

/**
 * JobLaunchServlet accepts the Job spec XML via POST method and queues it for launch.
 */
@SuppressWarnings("serial")
public class JobLaunchServlet extends FrameworkServlet {

    private static final Logger logger = LogManager.getLogger(JobLaunchServlet.class);

    private JobLauncher jobLauncher;

    @Override
    public void initFrameworkServlet() throws ServletException {
        jobLauncher = (JobLauncher) Objects.requireNonNull(this.getWebApplicationContext())
                .getBean("jobLauncher");
    }

    @Override
    protected void doService(HttpServletRequest request, HttpServletResponse response)
            throws Exception {

        try {
            JobSpec spec = jobLauncher.parse(request.getParameter("payload"));
            jobLauncher.queueAndLaunch(spec);

            StringBuilder sb = new StringBuilder(4096);
            for (BuildableJob job : spec.getJobs()) {
                sb.append(job.detail.name);
                sb.append(",");
            }
            sendResponse(response, "SUCCESS " + sb.toString());
        } catch (Exception e) {
            logger.debug("Misc error", e);
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
