
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



package com.imageworks.spcue.service;

import java.io.File;
import java.util.HashSet;
import java.util.Set;

import org.apache.log4j.Logger;
import org.springframework.beans.BeansException;
import org.springframework.context.ApplicationContext;
import org.springframework.context.ApplicationContextAware;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import com.imageworks.spcue.BuildableJob;
import com.imageworks.spcue.EntityCreationError;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.ShowEntity;
import com.imageworks.spcue.dispatcher.commands.DispatchLaunchJob;
import com.imageworks.spcue.grpc.renderpartition.RenderPartitionType;

/**
 * Job launching functions.
 */
public class JobLauncher implements ApplicationContextAware {
    private static final Logger logger = Logger.getLogger(JobLauncher.class);
    private ApplicationContext context;

    private JobManager jobManager;
    private DepartmentManager departmentManager;
    private AdminManager adminManager;
    private ThreadPoolTaskExecutor launchQueue;
    private EmailSupport emailSupport;
    private JmsMover jmsMover;
    private LocalBookingSupport localBookingSupport;

    /**
     * When true, disables log path creation and
     * proc points sync.
     */
    public volatile boolean testMode = false;

    @Override
    public void setApplicationContext(ApplicationContext context)
            throws BeansException {
        this.context = context;
    }

    public JobSpec parse(String xml) {
        JobSpec spec = (JobSpec) this.context.getBean("jobSpec");
        spec.parse(xml);
        return spec;
    }

    public JobSpec parse(File file) {
        JobSpec spec = (JobSpec) this.context.getBean("jobSpec");
        spec.parse(file);
        return spec;
    }

    public void launch(String xml) {
        JobSpec spec = (JobSpec) this.context.getBean("jobSpec");
        spec.parse(xml);
        launch(spec);
    }

    public void launch(File file) {
        JobSpec spec = (JobSpec) this.context.getBean("jobSpec");
        spec.parse(file);
        launch(spec);
    }

    public void launch(final JobSpec spec) {

        verifyJobSpec(spec);

        try {
            jobManager.launchJobSpec(spec);

            for (BuildableJob job: spec.getJobs()) {
                /*
                 * If isLocal is set, need to create local host assignment.
                 */
                JobDetail d = job.detail;
                if (d.isLocal) {
                    logger.info(d.localHostName + " will do local dispatch. " + d.getJobId() + " " + d.localHostName);
                    LocalHostAssignment lha = new LocalHostAssignment();
                    lha.setJobId(d.getJobId());
                    lha.setThreads(d.localThreadNumber);
                    lha.setMaxCoreUnits(d.localMaxCores * 100);
                    lha.setMaxMemory(d.localMaxMemory);
                    lha.setMaxGpuUnits(d.localMaxGpus);
                    lha.setMaxGpuMemory(d.localMaxGpuMemory);
                    lha.setType(RenderPartitionType.JOB_PARTITION);

                    try {
                        localBookingSupport.bookLocal(d, d.localHostName, d.user, lha);
                    }
                    catch (DataIntegrityViolationException e) {
                        logger.info(d.name + " failed to create host local assignment.");
                    }
                }
            }

            /*
             * This has to happen outside of the job launching transaction
             * or else it can lock up booking because it updates the
             * job_resource table.  It can take quite some time to launch
             * a job with dependencies, so the transaction should not
             * touch any rows that are currently in the "live" data set.
             */
            if (!testMode) {
                Set<String> depts = new HashSet<String>();
                for (BuildableJob job: spec.getJobs()) {
                    JobDetail d = jobManager.getJobDetail(job.detail.id);
                    jmsMover.send(d);
                    if (departmentManager.isManaged(d)) {
                        if (!depts.contains(d.deptId)) {
                            departmentManager.syncJobsWithTask(d);
                            depts.add(d.deptId);
                        }
                    }
                }
            }
        } catch (Exception e) {
            // Catch anything and email the user a report as to
            // why the job launch failed.
            emailSupport.reportLaunchError(spec, e);
        }
    }

    public void verifyJobSpec(JobSpec spec) {

        for (BuildableJob job: spec.getJobs()) {
            if (jobManager.isJobPending(job.detail.name)) {
                throw new EntityCreationError("The job " + job.detail.name
                        + " is already pending");
            }
        }

        try {
            ShowEntity s = adminManager.findShowEntity(spec.getShow());
            if (!s.active) {
                throw new EntityCreationError("The " + spec.getShow() +
                        " show has been deactivated.  Please contact " +
                        "administrator of your OpenCue deployment to reactivate " +
                        "this show.");
            }
        }
        catch (EmptyResultDataAccessException e) {
            throw new EntityCreationError("The " + spec.getShow() +
                    " does not exist. Please contact " +
                    "administrator of your OpenCue deployment to have this show " +
                    "created.");
        }
    }

    public void queueAndLaunch(final JobSpec spec) {
        verifyJobSpec(spec);
        launchQueue.execute(new DispatchLaunchJob(spec, this));
    }

    public EmailSupport getEmailSupport() {
        return emailSupport;
    }

    public void setEmailSupport(EmailSupport emailSupport) {
        this.emailSupport = emailSupport;
    }

    public JobManager getJobManager() {
        return jobManager;
    }

    public void setJobManager(JobManager jobManager) {
        this.jobManager = jobManager;
    }

    public DepartmentManager getDepartmentManager() {
        return departmentManager;
    }

    public void setDepartmentManager(DepartmentManager departmentManager) {
        this.departmentManager = departmentManager;
    }

    public AdminManager getAdminManager() {
        return adminManager;
    }

    public void setAdminManager(AdminManager adminManager) {
        this.adminManager = adminManager;
    }

    public ThreadPoolTaskExecutor getLaunchQueue() {
        return launchQueue;
    }

    public void setLaunchQueue(ThreadPoolTaskExecutor launchQueue) {
        this.launchQueue = launchQueue;
    }

    public JmsMover getJmsMover() {
        return jmsMover;
    }

    public void setJmsMover(JmsMover jmsMover) {
        this.jmsMover = jmsMover;
    }

    public LocalBookingSupport getLocalBookingSupport() {
        return localBookingSupport;
    }

    public void setLocalBookingSupport(LocalBookingSupport localBookingSupport) {
        this.localBookingSupport = localBookingSupport;
    }
}

