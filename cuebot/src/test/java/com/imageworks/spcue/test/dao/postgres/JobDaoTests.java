
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

package com.imageworks.spcue.test.dao.postgres;

import java.io.File;
import java.util.HashMap;
import java.util.Map;
import javax.annotation.Resource;

import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.DispatchJob;
import com.imageworks.spcue.ExecutionSummary;
import com.imageworks.spcue.FacilityEntity;
import com.imageworks.spcue.GroupDetail;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.JobRunState;
import com.imageworks.spcue.PointInterface;
import com.imageworks.spcue.ResourceUsage;
import com.imageworks.spcue.ServiceEntity;
import com.imageworks.spcue.ServiceOverrideEntity;
import com.imageworks.spcue.TaskEntity;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.DepartmentDao;
import com.imageworks.spcue.dao.FacilityDao;
import com.imageworks.spcue.dao.GroupDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.PointDao;
import com.imageworks.spcue.dao.ServiceDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.dao.TaskDao;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.JobSpec;
import com.imageworks.spcue.test.AssumingPostgresEngine;
import com.imageworks.spcue.util.FrameRetryLimits;
import com.imageworks.spcue.util.JobLogUtil;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

@Transactional
@ContextConfiguration(classes = TestAppConfig.class, loader = AnnotationConfigContextLoader.class)
public class JobDaoTests extends AbstractTransactionalJUnit4SpringContextTests {

    @Autowired
    @Rule
    public AssumingPostgresEngine assumingPostgresEngine;

    @Resource
    JobManager jobManager;

    @Autowired
    Environment env;

    @Resource
    JobLauncher jobLauncher;

    @Resource
    JobDao jobDao;

    @Resource
    PointDao pointDao;

    @Resource
    ServiceDao serviceDao;

    @Resource
    ShowDao showDao;

    @Resource
    TaskDao taskDao;

    @Resource
    GroupDao groupDao;

    @Resource
    FacilityDao facilityDao;

    @Resource
    DepartmentDao departmentDao;

    @Resource
    JobLogUtil jobLogUtil;

    private static String ROOT_FOLDER = "A0000000-0000-0000-0000-000000000000";
    private static String ROOT_SHOW = "00000000-0000-0000-0000-000000000000";
    private static String JOB_NAME = "pipe-dev.cue-testuser_shell_v1";

    @Before
    public void testMode() {
        jobLauncher.testMode = true;
    }

    public JobDetail buildJobDetail() {
        JobSpec spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        return spec.getJobs().get(0).detail;
    }

    public JobDetail insertJob() {
        JobDetail job = this.buildJobDetail();
        job.groupId = ROOT_FOLDER;
        job.showId = ROOT_SHOW;
        job.showName = "pipe";
        job.logDir = jobLogUtil.getJobLogPath(job);
        job.deptId = departmentDao.getDefaultDepartment().getId();
        job.deptName = departmentDao.getDefaultDepartment().getName();
        job.facilityId = facilityDao.getDefaultFacility().getId();
        job.facilityName = facilityDao.getDefaultFacility().getName();
        job.state = JobState.PENDING;
        job.maxCoreUnits = 10000;
        jobDao.insertJob(job, jobLogUtil);
        return job;
    }

    public JobDetail launchJob() {
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        return jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetDispatchJob() {
        JobDetail job = insertJob();
        DispatchJob djob = jobDao.getDispatchJob(job.id);
        assertEquals(djob.id, job.id);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testIsJobComplete() {
        JobDetail job = insertJob();
        // returns true because there are no dispatchable frames
        assertEquals(true, jobDao.isJobComplete(job));
    }

    /**
     * Launches the test job, a one frame pass_1_preprocess layer and a ten frame pass_1 layer, both
     * on the shell service, with every frame started and succeeded.
     */
    private JobDetail launchSucceededJob() {
        return succeedAllFrames(launchJob());
    }

    private JobDetail succeedAllFrames(JobDetail job) {
        // Drop the frame depends so the frame state triggers let the states below stick.
        jdbcTemplate.update("UPDATE frame SET int_depend_count=0 WHERE pk_job=?", job.getJobId());
        jdbcTemplate.update("UPDATE frame SET str_state='SUCCEEDED', ts_started=current_timestamp "
                + "WHERE pk_job=?", job.getJobId());
        return job;
    }

    private String[] getFrames(JobDetail job, String layer) {
        return jdbcTemplate.queryForList(
                "SELECT frame.pk_frame FROM frame JOIN layer ON layer.pk_layer = frame.pk_layer "
                        + "WHERE frame.pk_job=? AND layer.str_name=? ORDER BY frame.int_number",
                String.class, job.getJobId(), layer).toArray(new String[0]);
    }

    private void setFrameState(String frame, String state) {
        jdbcTemplate.update("UPDATE frame SET str_state=? WHERE pk_frame=?", state, frame);
    }

    private void setLayerServices(JobDetail job, String layer, String services) {
        jdbcTemplate.update("UPDATE layer SET str_services=? WHERE pk_job=? AND str_name=?",
                services, job.getJobId(), layer);
    }

    private ServiceEntity insertService(String name, boolean emailOnFailing) {
        ServiceEntity service = new ServiceEntity();
        service.name = name;
        service.tags.add("general");
        service.emailOnFailing = emailOnFailing;
        serviceDao.insert(service);
        return service;
    }

    private ServiceOverrideEntity insertServiceOverride(JobDetail job, String name,
            boolean emailOnFailing) {
        ServiceOverrideEntity override = new ServiceOverrideEntity();
        override.name = name;
        override.tags.add("general");
        override.showId = job.getShowId();
        override.emailOnFailing = emailOnFailing;
        serviceDao.insert(override);
        return override;
    }

    private void setShellEmailOnFailing(boolean emailOnFailing) {
        ServiceEntity shell = serviceDao.get("shell");
        shell.emailOnFailing = emailOnFailing;
        serviceDao.update(shell);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetJobRunState() {
        JobDetail job = launchJob();
        assertEquals(JobRunState.IN_PROGRESS, jobDao.getJobRunState(job));

        succeedAllFrames(job);
        assertEquals(JobRunState.COMPLETE, jobDao.getJobRunState(job));
        assertTrue(jobDao.isJobComplete(job));

        String[] frames = getFrames(job, "pass_1");
        setFrameState(frames[0], "DEAD");
        assertEquals(JobRunState.FAILING, jobDao.getJobRunState(job));
        assertFalse(jobDao.isJobComplete(job));

        // Depend frames may be waiting on the dead frame, so the job is still failing.
        setFrameState(frames[1], "DEPEND");
        assertEquals(JobRunState.FAILING, jobDao.getJobRunState(job));

        // A waiting or running frame means the job can still make progress.
        setFrameState(frames[2], "WAITING");
        assertEquals(JobRunState.IN_PROGRESS, jobDao.getJobRunState(job));
        setFrameState(frames[2], "RUNNING");
        assertEquals(JobRunState.IN_PROGRESS, jobDao.getJobRunState(job));

        // Only a pending job is failing: a launching one isn't yet, a killed one isn't any more.
        setFrameState(frames[2], "SUCCEEDED");
        jdbcTemplate.update("UPDATE job SET str_state='STARTUP' WHERE pk_job=?", job.getJobId());
        assertEquals(JobRunState.IN_PROGRESS, jobDao.getJobRunState(job));
        jdbcTemplate.update("UPDATE job SET str_state='FINISHED' WHERE pk_job=?", job.getJobId());
        assertEquals(JobRunState.IN_PROGRESS, jobDao.getJobRunState(job));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testClaimFailingEmailOncePerRun() {
        setShellEmailOnFailing(true);
        JobDetail job = launchSucceededJob();
        // Not failing.
        assertFalse(jobDao.claimFailingEmail(job));

        String[] frames = getFrames(job, "pass_1");
        setFrameState(frames[0], "DEAD");
        setFrameState(frames[1], "DEAD");
        assertTrue(jobDao.claimFailingEmail(job));
        // Other completions seeing the same run fail do not claim it again.
        assertFalse(jobDao.claimFailingEmail(job));

        // A retry starts a new run, which is claimed once it fails again.
        setFrameState(frames[0], "WAITING");
        jdbcTemplate.update("UPDATE frame SET ts_started=current_timestamp + interval '1' second "
                + "WHERE pk_frame=?", frames[0]);
        assertFalse(jobDao.claimFailingEmail(job));
        setFrameState(frames[0], "DEAD");
        assertTrue(jobDao.claimFailingEmail(job));
        assertFalse(jobDao.claimFailingEmail(job));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testClaimFailingEmailNeedsDeadFramesOnALayerWithTheEmail() {
        insertService("emailing", true);
        JobDetail job = launchSucceededJob();
        setLayerServices(job, "pass_1_preprocess", "emailing");

        // pass_1 uses shell, which has the email off.
        setFrameState(getFrames(job, "pass_1")[0], "DEAD");
        assertFalse(jobDao.claimFailingEmail(job));

        setFrameState(getFrames(job, "pass_1_preprocess")[0], "DEAD");
        assertTrue(jobDao.claimFailingEmail(job));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testClaimFailingEmailFollowsTheLayersPrimaryService() {
        insertService("emailing", true);
        JobDetail job = launchSucceededJob();
        setFrameState(getFrames(job, "pass_1")[0], "DEAD");

        // The first listed service decides, not any listed one.
        setLayerServices(job, "pass_1", "shell,emailing");
        assertFalse(jobDao.claimFailingEmail(job));

        // A listed service that doesn't exist is skipped, as at launch.
        setLayerServices(job, "pass_1", "nosuchservice,emailing,shell");
        assertTrue(jobDao.claimFailingEmail(job));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testClaimFailingEmailPrefersTheShowOverride() {
        setShellEmailOnFailing(true);
        JobDetail job = launchSucceededJob();
        setFrameState(getFrames(job, "pass_1")[0], "DEAD");

        ServiceOverrideEntity override = insertServiceOverride(job, "shell", false);
        assertFalse(jobDao.claimFailingEmail(job));

        setShellEmailOnFailing(false);
        override.emailOnFailing = true;
        serviceDao.update(override);
        assertTrue(jobDao.claimFailingEmail(job));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testClaimFailingEmailMatchesServicesById() {
        ServiceEntity emailing = insertService("emailing", true);
        JobDetail job = launchSucceededJob();
        setFrameState(getFrames(job, "pass_1")[0], "DEAD");

        // A service listed by id resolves, as at launch, so shell, which has the email off,
        // does not decide.
        setLayerServices(job, "pass_1", emailing.getId() + ",shell");
        assertTrue(jobDao.claimFailingEmail(job));

        // So does a show's override listed by id.
        jdbcTemplate.update("UPDATE job SET ts_failing_email=NULL WHERE pk_job=?", job.getJobId());
        ServiceOverrideEntity override = insertServiceOverride(job, "shell", true);
        setLayerServices(job, "pass_1", override.getId());
        assertTrue(jobDao.claimFailingEmail(job));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testClaimFailingEmailOnlyForPendingJobs() {
        setShellEmailOnFailing(true);
        JobDetail job = launchSucceededJob();
        setFrameState(getFrames(job, "pass_1")[0], "DEAD");

        jdbcTemplate.update("UPDATE job SET str_state='FINISHED' WHERE pk_job=?", job.getJobId());
        assertFalse(jobDao.claimFailingEmail(job));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertJob() {
        JobDetail job = this.buildJobDetail();
        job.groupId = ROOT_FOLDER;
        job.showId = ROOT_SHOW;
        job.logDir = jobLogUtil.getJobLogPath(job);
        job.deptId = departmentDao.getDefaultDepartment().getId();
        job.facilityId = facilityDao.getDefaultFacility().getId();
        jobDao.insertJob(job, jobLogUtil);
        assertNotNull(job.id);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindJob() {
        JobDetail job = insertJob();
        JobInterface j1 = jobDao.findJob(job.name);
        JobDetail j2 = jobDao.findJobDetail(job.name);
        assertEquals(job.name, j1.getName());
        assertEquals(job.name, j2.getName());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetJob() {
        JobDetail job = insertJob();
        jobDao.getJobDetail(job.id);
        jobDao.getJob(job.id);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetJobDetail() {
        JobDetail src = insertJob();
        JobDetail job = jobDao.getJobDetail(src.id);
        assertEquals(job.id, src.id);
        assertEquals(job.name, src.name);
        assertEquals(job.showId, src.showId);
        assertEquals(job.facilityId, src.facilityId);
        assertEquals(job.groupId, src.groupId);
        assertEquals(job.deptId, src.deptId);
        assertEquals(job.state, src.state);
        assertEquals(job.shot, src.shot);
        assertEquals(job.user, src.user);
        assertEquals(job.email, src.email);
        assertEquals(job.uid, src.uid);
        assertEquals(job.logDir, src.logDir);
        assertEquals(job.isPaused, src.isPaused);
        assertEquals(job.isAutoEat, src.isAutoEat);
        assertEquals(job.totalFrames, src.totalFrames);
        assertEquals(job.totalLayers, src.totalLayers);
        assertEquals(job.startTime, src.startTime);
        assertEquals(job.stopTime, src.stopTime);
        assertEquals(job.maxRetries, src.maxRetries);
        assertEquals(job.os, src.os);
        assertEquals(job.facilityName, src.facilityName);
        assertEquals(job.deptName, src.deptName);
        assertEquals(job.showName, src.showName);
        assertEquals(job.priority, src.priority);
        assertEquals(job.minCoreUnits, src.minCoreUnits);
        assertEquals(job.maxCoreUnits, src.maxCoreUnits);
        assertEquals(job.isLocal, src.isLocal);
        assertEquals(job.localHostName, src.localHostName);
        assertEquals(job.localMaxCores, src.localMaxCores);
        assertEquals(job.localMaxMemory, src.localMaxMemory);
        assertEquals(job.localThreadNumber, src.localThreadNumber);
        assertEquals(job.localMaxGpus, src.localMaxGpus);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetJobsByTask() {

        PointInterface p = pointDao.getPointConfigDetail(showDao.findShowDetail("pipe"),
                departmentDao.getDefaultDepartment());

        TaskEntity t = new TaskEntity(p, "dev.cue");
        taskDao.insertTask(t);
        jobDao.getJobs(t);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testJobExists() {
        assertFalse(jobDao.exists(JOB_NAME));
        JobDetail job = insertJob();
        jdbcTemplate.update("UPDATE job SET str_state='PENDING' WHERE pk_job=?", job.id);
        assertTrue(jobDao.exists(JOB_NAME));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDeleteJob() {
        jobDao.deleteJob(insertJob());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testActivateJob() {
        jobDao.activateJob(insertJob(), JobState.PENDING);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateJobState() {
        JobDetail job = insertJob();
        assertEquals(JobState.PENDING, job.state);
        jobDao.updateState(job, JobState.FINISHED);
        assertEquals(JobState.FINISHED.toString(), jdbcTemplate.queryForObject(
                "SELECT str_state FROM job WHERE pk_job=?", String.class, job.getJobId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateJobFinished() {
        jobDao.updateJobFinished(insertJob());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testIsJobOverMinProc() {
        JobDetail job = insertJob();
        assertFalse(jobDao.isOverMinCores(job));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testHasPendingFrames() {
        assertFalse(jobDao.hasPendingFrames(insertJob()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testIsJobOverMaxProc() {
        JobDetail job = insertJob();
        assertFalse(jobDao.isOverMaxCores(job));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testIsJobAtMaxCores() {
        JobDetail job = insertJob();
        assertFalse(jobDao.isAtMaxCores(job));

        jdbcTemplate.update("UPDATE job_resource SET int_cores = int_max_cores WHERE pk_job=?",
                job.getJobId());

        assertTrue(jobDao.isAtMaxCores(job));

    }

    @Test
    @Transactional
    @Rollback(true)
    public void testIsOverMaxCores() {
        JobDetail job = insertJob();
        jobDao.updateMaxCores(job, 500);
        jdbcTemplate.update("UPDATE job_resource SET int_cores = 450 WHERE pk_job=?",
                job.getJobId());

        assertFalse(jobDao.isOverMaxCores(job));
        assertFalse(jobDao.isOverMaxCores(job, 50));
        assertTrue(jobDao.isOverMaxCores(job, 100));

        jdbcTemplate.update("UPDATE job_resource SET int_max_cores = 200 WHERE pk_job=?",
                job.getJobId());
        assertTrue(jobDao.isOverMaxCores(job));
    }

    @Test(expected = org.springframework.jdbc.UncategorizedSQLException.class)
    @Transactional
    @Rollback(true)
    public void testMaxCoreTrigger() {
        JobDetail job = insertJob();
        int maxCores =
                jdbcTemplate.queryForObject("SELECT int_max_cores FROM job_resource WHERE pk_job=?",
                        Integer.class, job.getJobId());

        jdbcTemplate.update("UPDATE job_resource SET int_cores = ? WHERE pk_job=?", maxCores + 1,
                job.getJobId());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateJobPriority() {
        JobDetail job = insertJob();
        jobDao.updatePriority(job, 199);
        assertEquals(Integer.valueOf(199),
                jdbcTemplate.queryForObject("SELECT int_priority FROM job_resource WHERE pk_job=?",
                        Integer.class, job.getJobId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateJobMinCores() {
        JobDetail job = insertJob();
        jobDao.updateMinCores(job, 100);
        assertEquals(Integer.valueOf(100),
                jdbcTemplate.queryForObject("SELECT int_min_cores FROM job_resource WHERE pk_job=?",
                        Integer.class, job.getJobId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateJobMaxCores() {
        JobDetail job = insertJob();
        jobDao.updateMaxCores(job, 100);
        assertEquals(Integer.valueOf(100),
                jdbcTemplate.queryForObject("SELECT int_max_cores FROM job_resource WHERE pk_job=?",
                        Integer.class, job.getJobId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateJobMinCoresByGroup() {
        JobDetail job = insertJob();
        GroupInterface g = groupDao.getGroup(job.groupId);
        jobDao.updateMinCores(g, 100);
        assertEquals(Integer.valueOf(100),
                jdbcTemplate.queryForObject("SELECT int_min_cores FROM job_resource WHERE pk_job=?",
                        Integer.class, job.getJobId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateJobMaxCoresByGroup() {
        JobDetail job = insertJob();
        GroupInterface g = groupDao.getGroup(job.groupId);
        jobDao.updateMaxCores(g, 100);
        assertEquals(Integer.valueOf(100),
                jdbcTemplate.queryForObject("SELECT int_max_cores FROM job_resource WHERE pk_job=?",
                        Integer.class, job.getJobId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateJobPriorityByGroup() {
        JobDetail job = insertJob();
        GroupInterface g = groupDao.getGroup(job.groupId);
        jobDao.updatePriority(g, 100);
        assertEquals(Integer.valueOf(100),
                jdbcTemplate.queryForObject("SELECT int_priority FROM job_resource WHERE pk_job=?",
                        Integer.class, job.getJobId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateJobMaxRss() {
        long maxRss = 100000;
        JobDetail job = insertJob();
        jobDao.updateMaxRSS(job, maxRss);
        assertEquals(Long.valueOf(maxRss), jdbcTemplate.queryForObject(
                "SELECT int_max_rss FROM job_mem WHERE pk_job=?", Long.class, job.getJobId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateJobPaused() {
        JobDetail job = insertJob();

        assertTrue(jdbcTemplate.queryForObject("SELECT b_paused FROM job WHERE pk_job=?",
                Boolean.class, job.getJobId()));

        jobDao.updatePaused(job, false);

        assertFalse(jdbcTemplate.queryForObject("SELECT b_paused FROM job WHERE pk_job=?",
                Boolean.class, job.getJobId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateJobAutoEat() {
        JobDetail job = insertJob();

        assertFalse(jdbcTemplate.queryForObject("SELECT b_autoeat FROM job WHERE pk_job=?",
                Boolean.class, job.getJobId()));

        jobDao.updateAutoEat(job, true);

        assertTrue(jdbcTemplate.queryForObject("SELECT b_autoeat FROM job WHERE pk_job=?",
                Boolean.class, job.getJobId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateJobAutoEatSetsMaxRetries() {
        JobDetail job = insertJob();

        jobDao.updateAutoEat(job, true);
        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT int_max_retries FROM job WHERE pk_job=?", Integer.class, job.getJobId()));

        jobDao.updateAutoEat(job, false);
        assertEquals(Integer.valueOf(FrameRetryLimits.from(env).getDefault()),
                jdbcTemplate.queryForObject("SELECT int_max_retries FROM job WHERE pk_job=?",
                        Integer.class, job.getJobId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateJobMaxRetries() {
        JobDetail job = insertJob();
        jobDao.updateMaxFrameRetries(job, 10);
        assertEquals(Integer.valueOf(10), jdbcTemplate.queryForObject(
                "SELECT int_max_retries FROM job WHERE pk_job=?", Integer.class, job.getJobId()));
    }

    @Test(expected = IllegalArgumentException.class)
    @Transactional
    @Rollback(true)
    public void testUpdateJobMaxRetriesTooLow() {
        JobDetail job = insertJob();
        jobDao.updateMaxFrameRetries(job, -1);
    }

    @Test(expected = IllegalArgumentException.class)
    @Transactional
    @Rollback(true)
    public void testUpdateJobMaxRetriesTooHigh() {
        JobDetail job = insertJob();
        jobDao.updateMaxFrameRetries(job, 100000);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateJobMaxRetriesAtBounds() {
        JobDetail job = insertJob();
        FrameRetryLimits limits = FrameRetryLimits.from(env);

        jobDao.updateMaxFrameRetries(job, limits.getMax());
        assertEquals(Integer.valueOf(limits.getMax()), jdbcTemplate.queryForObject(
                "SELECT int_max_retries FROM job WHERE pk_job=?", Integer.class, job.getJobId()));

        jobDao.updateMaxFrameRetries(job, limits.getMin());
        assertEquals(Integer.valueOf(limits.getMin()), jdbcTemplate.queryForObject(
                "SELECT int_max_retries FROM job WHERE pk_job=?", Integer.class, job.getJobId()));
    }

    @Test(expected = IllegalArgumentException.class)
    @Transactional
    @Rollback(true)
    public void testUpdateJobMaxRetriesJustAboveMax() {
        JobDetail job = insertJob();
        jobDao.updateMaxFrameRetries(job, FrameRetryLimits.from(env).getMax() + 1);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetFrameStateTotals() {
        JobSpec spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        jobLauncher.launch(spec);
        jobDao.getFrameStateTotals(spec.getJobs().get(0).detail);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetExecutionSummary() {
        JobDetail job = launchJob();
        ExecutionSummary summary = jobDao.getExecutionSummary(job);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetJobEnvironment() {
        JobDetail job = launchJob();
        Map<String, String> map = jobDao.getEnvironment(job);
        for (Map.Entry<String, String> e : map.entrySet()) {
            assertEquals("VNP_VCR_SESSION", e.getKey());
            assertEquals("9000", e.getValue());
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertJobEnvironment() {
        JobDetail job = launchJob();
        jobDao.insertEnvironment(job, "CHAMBERS", "123");
        Map<String, String> map = jobDao.getEnvironment(job);
        assertEquals(2, map.size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertJobEnvironmentMap() {
        JobDetail job = launchJob();
        Map<String, String> map = new HashMap<String, String>();
        map.put("CHAMBERS", "123");
        map.put("OVER9000", "123");

        jobDao.insertEnvironment(job, map);
        Map<String, String> env = jobDao.getEnvironment(job);
        assertEquals(3, env.size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindLastJob() {
        JobSpec spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        jobLauncher.launch(spec);

        JobInterface job = spec.getJobs().get(0).detail;
        jobDao.getFrameStateTotals(job);
        jobManager.shutdownJob(job);
        // this might fail
        JobDetail oldJob = jobDao.findLastJob(job.getName());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateJobLogPath() {
        JobDetail job = launchJob();
        String newLogDir = "/path/to/nowhere";
        jobDao.updateLogPath(job, newLogDir);
        assertEquals(newLogDir, jdbcTemplate.queryForObject(
                "SELECT str_log_dir FROM job WHERE pk_job=?", String.class, job.id));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateJobParent() {
        JobDetail job = launchJob();

        // Make a new test group.
        GroupDetail root = groupDao.getRootGroupDetail(job);

        GroupDetail testGroup = new GroupDetail();
        testGroup.name = "testGroup";
        testGroup.deptId = departmentDao.getDefaultDepartment().getId();
        testGroup.showId = root.getShowId();

        groupDao.insertGroup(testGroup, root);

        jdbcTemplate.update(
                "UPDATE folder SET int_job_max_cores=-1, int_job_min_cores=-1, int_job_priority=-1 WHERE pk_folder=?",
                testGroup.getId());

        GroupDetail group = groupDao.getGroupDetail(testGroup.getId());
        jobDao.updateParent(job, group);

        assertEquals(-1, group.jobMaxCores);
        assertEquals(-1, group.jobMinCores);
        assertEquals(-1, group.jobPriority);

        assertEquals(group.getGroupId(), jdbcTemplate
                .queryForObject("SELECT pk_folder FROM job WHERE pk_job=?", String.class, job.id));

        assertEquals(group.getDepartmentId(), jdbcTemplate
                .queryForObject("SELECT pk_dept FROM job WHERE pk_job=?", String.class, job.id));

        group.jobMaxCores = 100;
        group.jobMinCores = 100;
        group.jobPriority = 100;

        jobDao.updateParent(job, group);

        assertEquals(Integer.valueOf(group.jobMaxCores), jdbcTemplate.queryForObject(
                "SELECT int_max_cores FROM job_resource WHERE pk_job=?", Integer.class, job.id));

        assertEquals(Integer.valueOf(group.jobMinCores), jdbcTemplate.queryForObject(
                "SELECT int_min_cores FROM job_resource WHERE pk_job=?", Integer.class, job.id));

        assertEquals(Integer.valueOf(group.jobPriority), jdbcTemplate.queryForObject(
                "SELECT int_priority FROM job_resource WHERE pk_job=?", Integer.class, job.id));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testCueHasPendingJobs() {
        jobDao.cueHasPendingJobs(new FacilityEntity("0"));

    }

    @Test
    @Transactional
    @Rollback(true)
    public void mapPostJob() {
        JobSpec spec = jobLauncher
                .parse(new File("src/test/resources/conf/jobspec/jobspec_postframes.xml"));
        jobLauncher.launch(spec);

        final String pk_job = spec.getJobs().get(0).detail.id;

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM job_post WHERE pk_job=?", Integer.class, pk_job));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void activatePostJob() {
        JobSpec spec = jobLauncher
                .parse(new File("src/test/resources/conf/jobspec/jobspec_postframes.xml"));
        jobLauncher.launch(spec);

        jobDao.activatePostJob(spec.getJobs().get(0).detail);

        assertEquals(JobState.PENDING.toString(),
                jdbcTemplate.queryForObject("SELECT str_state FROM job WHERE pk_job=?",
                        String.class, spec.getJobs().get(0).getPostJob().detail.id));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateUsage() {

        JobSpec spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        jobLauncher.launch(spec);

        JobInterface job = jobDao.findJob(spec.getJobs().get(0).detail.name);

        /** 60 seconds of 100 core units **/
        ResourceUsage usage = new ResourceUsage(60, 33, 0);

        assertTrue(usage.getClockTimeSeconds() > 0);
        assertTrue(usage.getCoreTimeSeconds() > 0);

        /**
         * Successful frame
         */
        jobDao.updateUsage(job, usage, 0);
        assertEquals(Long.valueOf(usage.getClockTimeSeconds()),
                jdbcTemplate.queryForObject(
                        "SELECT int_clock_time_success FROM job_usage WHERE pk_job=?", Long.class,
                        job.getId()));

        assertEquals(Long.valueOf(usage.getCoreTimeSeconds()),
                jdbcTemplate.queryForObject(
                        "SELECT int_core_time_success FROM job_usage WHERE pk_job=?", Long.class,
                        job.getId()));

        assertEquals(Integer.valueOf(1),
                jdbcTemplate.queryForObject(
                        "SELECT int_frame_success_count FROM job_usage WHERE pk_job=?",
                        Integer.class, job.getId()));

        /**
         * Failed frame
         */
        jobDao.updateUsage(job, usage, 1);
        assertEquals(Long.valueOf(usage.getClockTimeSeconds()),
                jdbcTemplate.queryForObject(
                        "SELECT int_clock_time_fail FROM job_usage WHERE pk_job=?", Long.class,
                        job.getId()));

        assertEquals(Long.valueOf(usage.getCoreTimeSeconds()),
                jdbcTemplate.queryForObject(
                        "SELECT int_core_time_fail FROM job_usage WHERE pk_job=?", Long.class,
                        job.getId()));

        assertEquals(Integer.valueOf(1),
                jdbcTemplate.queryForObject(
                        "SELECT int_frame_fail_count FROM job_usage WHERE pk_job=?", Integer.class,
                        job.getId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testOverrideMaxCoresAndGpus() {
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/override_max_cores_gpus.xml"));
        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_test");
        assertEquals(job.maxCoreUnits, 42000);
        assertEquals(job.maxGpuUnits, 42);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateUsageBatchEachColumnByItsOwnValue() {
        // One row per job, every value distinct, so a swapped parameter changes
        // exactly one column; a second row without successes leaves the high.
        JobSpec spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        jobLauncher.launch(spec);
        JobInterface job = jobDao.findJob(spec.getJobs().get(0).detail.name);
        jobDao.updateUsageBatch(java.util.Collections
                .singletonList(new Object[] {11L, 13L, 17L, 3L, 19L, 29L, 2L, 23L, job.getId()}));
        jobDao.updateUsageBatch(java.util.Collections
                .singletonList(new Object[] {0L, 0L, 0L, 0L, 0L, 0L, 0L, 0L, job.getId()}));
        String[] columns = {"int_core_time_success", "int_gpu_time_success",
                "int_clock_time_success", "int_frame_success_count", "int_clock_time_high",
                "int_core_time_fail", "int_clock_time_fail", "int_frame_fail_count"};
        long[] expected = {11, 13, 17, 3, 23, 19, 29, 2};
        for (int i = 0; i < columns.length; i++) {
            assertEquals(columns[i], Long.valueOf(expected[i]),
                    jdbcTemplate.queryForObject(
                            "SELECT " + columns[i] + " FROM job_usage WHERE pk_job=?", Long.class,
                            job.getId()));
        }
    }
}
