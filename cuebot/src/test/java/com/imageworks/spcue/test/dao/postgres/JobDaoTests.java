
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



package com.imageworks.spcue.test.dao.postgres;

import com.imageworks.spcue.*;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.FacilityDao;
import com.imageworks.spcue.dao.GroupDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.JobSpec;
import com.imageworks.spcue.util.JobLogUtil;
import org.junit.Before;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import java.io.File;
import java.util.HashMap;
import java.util.Map;

import static org.junit.Assert.*;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class JobDaoTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Autowired
    JobManager jobManager;

    @Autowired
    JobLauncher jobLauncher;

    @Autowired
    JobDao jobDao;

    @Autowired
    GroupDao groupDao;

    @Autowired
    FacilityDao facilityDao;

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
        job.logDir = JobLogUtil.getJobLogPath(job);
        job.facilityId = facilityDao.getDefaultFacility().getId();
        job.state = JobState.PENDING;
        jobDao.insertJob(job);
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
        assertEquals(true,jobDao.isJobComplete(job));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertJob() {
        JobDetail job = this.buildJobDetail();
        job.groupId = ROOT_FOLDER;
        job.showId = ROOT_SHOW;
        job.logDir = JobLogUtil.getJobLogPath(job);
        job.facilityId= facilityDao.getDefaultFacility().getId();
        jobDao.insertJob(job);
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
    public void testJobExists() {
        assertFalse(jobDao.exists(JOB_NAME));
        JobDetail job = insertJob();
        jdbcTemplate.update("UPDATE job SET str_state='PENDING' WHERE pk_job=?",
                job.id);
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
        assertEquals(JobState.FINISHED.toString(),
                jdbcTemplate.queryForObject(
                        "SELECT str_state FROM job WHERE pk_job=?",
                        String.class, job.getJobId()));
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

        jdbcTemplate.update(
                "UPDATE job_resource SET int_cores = int_max_cores WHERE pk_job=?",
                job.getJobId());

        assertTrue(jobDao.isAtMaxCores(job));

    }

    @Test
    @Transactional
    @Rollback(true)
    public void testIsOverMaxCores() {
        JobDetail job = insertJob();
        jobDao.updateMaxCores(job, 500);
        jdbcTemplate.update(
                "UPDATE job_resource SET int_cores = 450 WHERE pk_job=?",
                job.getJobId());

        assertFalse(jobDao.isOverMaxCores(job));
        assertFalse(jobDao.isOverMaxCores(job, 50));
        assertTrue(jobDao.isOverMaxCores(job, 100));

        jdbcTemplate.update(
                "UPDATE job_resource SET int_max_cores = 200 WHERE pk_job=?",
                job.getJobId());
        assertTrue(jobDao.isOverMaxCores(job));
    }

    @Test(expected=org.springframework.jdbc.UncategorizedSQLException.class)
    @Transactional
    @Rollback(true)
    public void testMaxCoreTrigger() {
        JobDetail job = insertJob();
        int maxCores = jdbcTemplate.queryForObject(
                "SELECT int_max_cores FROM job_resource WHERE pk_job=?",
                Integer.class, job.getJobId());

        jdbcTemplate.update(
                "UPDATE job_resource SET int_cores = ? WHERE pk_job=?",
                maxCores + 1, job.getJobId());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateJobPriority() {
        JobDetail job = insertJob();
        jobDao.updatePriority(job, 199);
        assertEquals(Integer.valueOf(199), jdbcTemplate.queryForObject(
                "SELECT int_priority FROM job_resource WHERE pk_job=?",
                Integer.class, job.getJobId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateJobMinCores() {
        JobDetail job = insertJob();
        jobDao.updateMinCores(job, 100);
        assertEquals(Integer.valueOf(100), jdbcTemplate.queryForObject(
                "SELECT int_min_cores FROM job_resource WHERE pk_job=?",
                Integer.class, job.getJobId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateJobMaxCores() {
        JobDetail job = insertJob();
        jobDao.updateMaxCores(job, 100);
        assertEquals(Integer.valueOf(100), jdbcTemplate.queryForObject(
                "SELECT int_max_cores FROM job_resource WHERE pk_job=?",
                Integer.class, job.getJobId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateJobMinCoresByGroup() {
        JobDetail job = insertJob();
        GroupInterface g = groupDao.getGroup(job.groupId);
        jobDao.updateMinCores(g, 100);
        assertEquals(Integer.valueOf(100), jdbcTemplate.queryForObject(
                "SELECT int_min_cores FROM job_resource WHERE pk_job=?",
                Integer.class, job.getJobId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateJobMaxCoresByGroup() {
        JobDetail job = insertJob();
        GroupInterface g = groupDao.getGroup(job.groupId);
        jobDao.updateMaxCores(g, 100);
        assertEquals(Integer.valueOf(100), jdbcTemplate.queryForObject(
                "SELECT int_max_cores FROM job_resource WHERE pk_job=?",
                Integer.class, job.getJobId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateJobPriorityByGroup() {
        JobDetail job = insertJob();
        GroupInterface g = groupDao.getGroup(job.groupId);
        jobDao.updatePriority(g, 100);
        assertEquals(Integer.valueOf(100), jdbcTemplate.queryForObject(
                "SELECT int_priority FROM job_resource WHERE pk_job=?",
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
                "SELECT int_max_rss FROM job_mem WHERE pk_job=?",
                Long.class, job.getJobId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateJobPaused() {
        JobDetail job = insertJob();

        assertTrue(jdbcTemplate.queryForObject(
                "SELECT b_paused FROM job WHERE pk_job=?",
                Boolean.class, job.getJobId()));

        jobDao.updatePaused(job, false);

        assertFalse(jdbcTemplate.queryForObject(
                "SELECT b_paused FROM job WHERE pk_job=?",
                Boolean.class, job.getJobId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateJobAutoEat() {
        JobDetail job = insertJob();

        assertFalse(jdbcTemplate.queryForObject(
                "SELECT b_autoeat FROM job WHERE pk_job=?",
                Boolean.class, job.getJobId()));

        jobDao.updateAutoEat(job, true);

        assertTrue(jdbcTemplate.queryForObject(
                "SELECT b_autoeat FROM job WHERE pk_job=?",
                Boolean.class, job.getJobId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateJobMaxRetries() {
        JobDetail job = insertJob();
        jobDao.updateMaxFrameRetries(job,10);
        assertEquals(Integer.valueOf(10), jdbcTemplate.queryForObject(
                "SELECT int_max_retries FROM job WHERE pk_job=?",
                Integer.class, job.getJobId()));
    }

    @Test(expected=IllegalArgumentException.class)
    @Transactional
    @Rollback(true)
    public void testUpdateJobMaxRetriesTooLow() {
        JobDetail job = insertJob();
        jobDao.updateMaxFrameRetries(job,-1);
    }

    @Test(expected=IllegalArgumentException.class)
    @Transactional
    @Rollback(true)
    public void testUpdateJobMaxRetriesTooHigh() {
        JobDetail job = insertJob();
        jobDao.updateMaxFrameRetries(job,100000);
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
        Map<String,String> map = jobDao.getEnvironment(job);
        for (Map.Entry<String,String> e : map.entrySet()) {
            assertEquals("VNP_VCR_SESSION", e.getKey());
            assertEquals( "9000", e.getValue());
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertJobEnvironment() {
        JobDetail job = launchJob();
        jobDao.insertEnvironment(job, "CHAMBERS","123");
        Map<String,String> map = jobDao.getEnvironment(job);
        assertEquals(2,map.size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertJobEnvironmentMap() {
        JobDetail job = launchJob();
        Map<String,String> map = new HashMap<String,String>();
        map.put("CHAMBERS","123");
        map.put("OVER9000","123");

        jobDao.insertEnvironment(job, map);
        Map<String,String> env = jobDao.getEnvironment(job);
        assertEquals(3,env.size());
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
        String newLogDir =  "/path/to/nowhere";
        jobDao.updateLogPath(job,newLogDir);
        assertEquals(newLogDir,jdbcTemplate.queryForObject(
                "SELECT str_log_dir FROM job WHERE pk_job=?",String.class, job.id));
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
        testGroup.showId = root.getShowId();

        groupDao.insertGroup(testGroup, root);

        jdbcTemplate.update(
                "UPDATE folder SET int_job_max_cores=-1, int_job_min_cores=-1, int_job_priority=-1 WHERE pk_folder=?",
                testGroup.getId());

        GroupDetail group = groupDao.getGroupDetail(testGroup.getId());
        jobDao.updateParent(job, group);

        assertEquals(-1,group.jobMaxCores);
        assertEquals(-1,group.jobMinCores);
        assertEquals(-1,group.jobPriority);

        assertEquals(group.getGroupId(),jdbcTemplate.queryForObject(
                "SELECT pk_folder FROM job WHERE pk_job=?",String.class, job.id));

        group.jobMaxCores = 100;
        group.jobMinCores = 100;
        group.jobPriority = 100;

        jobDao.updateParent(job, group);

        assertEquals(Integer.valueOf(group.jobMaxCores) ,jdbcTemplate.queryForObject(
                "SELECT int_max_cores FROM job_resource WHERE pk_job=?",
                Integer.class, job.id));

        assertEquals(Integer.valueOf(group.jobMinCores) ,jdbcTemplate.queryForObject(
                "SELECT int_min_cores FROM job_resource WHERE pk_job=?",
                Integer.class, job.id));

        assertEquals(Integer.valueOf(group.jobPriority) ,jdbcTemplate.queryForObject(
                "SELECT int_priority FROM job_resource WHERE pk_job=?",
                Integer.class, job.id));
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
        JobSpec spec = jobLauncher.parse(
                new File("src/test/resources/conf/jobspec/jobspec_postframes.xml"));
        jobLauncher.launch(spec);

        final String pk_job = spec.getJobs().get(0).detail.id;

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM job_post WHERE pk_job=?",
                Integer.class, pk_job));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void activatePostJob() {
        JobSpec spec = jobLauncher.parse(
                new File("src/test/resources/conf/jobspec/jobspec_postframes.xml"));
        jobLauncher.launch(spec);

        jobDao.activatePostJob(spec.getJobs().get(0).detail);

        assertEquals(JobState.PENDING.toString(),jdbcTemplate.queryForObject(
                "SELECT str_state FROM job WHERE pk_job=?", String.class,
                spec.getJobs().get(0).getPostJob().detail.id));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateUsage() {

        JobSpec spec = jobLauncher.parse(
                new File("src/test/resources/conf/jobspec/jobspec.xml"));
        jobLauncher.launch(spec);

        JobInterface job = jobDao.findJob(spec.getJobs().get(0).detail.name);

        /** 60 seconds of 100 core units **/
        ResourceUsage usage = new ResourceUsage(60, 33);

        assertTrue(usage.getClockTimeSeconds() > 0);
        assertTrue(usage.getCoreTimeSeconds() > 0);

        /**
         * Successful frame
         */
        jobDao.updateUsage(job, usage, 0);
        assertEquals(Long.valueOf(usage.getClockTimeSeconds()), jdbcTemplate.queryForObject(
                "SELECT int_clock_time_success FROM job_usage WHERE pk_job=?",
                Long.class, job.getId()));

        assertEquals(Long.valueOf(usage.getCoreTimeSeconds()), jdbcTemplate.queryForObject(
                "SELECT int_core_time_success FROM job_usage WHERE pk_job=?",
                Long.class, job.getId()));

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT int_frame_success_count FROM job_usage WHERE pk_job=?",
                Integer.class, job.getId()));

        /**
         * Failed frame
         */
        jobDao.updateUsage(job, usage, 1);
        assertEquals(Long.valueOf(usage.getClockTimeSeconds()), jdbcTemplate.queryForObject(
                "SELECT int_clock_time_fail FROM job_usage WHERE pk_job=?",
                Long.class, job.getId()));

        assertEquals(Long.valueOf(usage.getCoreTimeSeconds()), jdbcTemplate.queryForObject(
                "SELECT int_core_time_fail FROM job_usage WHERE pk_job=?",
                Long.class, job.getId()));

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT int_frame_fail_count FROM job_usage WHERE pk_job=?",
                Integer.class, job.getId()));
    }
}


