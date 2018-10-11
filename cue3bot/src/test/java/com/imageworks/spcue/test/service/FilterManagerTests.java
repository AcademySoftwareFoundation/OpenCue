
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



package com.imageworks.spcue.test.service;

import java.io.File;

import javax.annotation.Resource;

import static org.junit.Assert.*;
import org.junit.Before;
import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.transaction.TransactionConfiguration;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.support.AnnotationConfigContextLoader;

import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.ActionEntity;
import com.imageworks.spcue.FilterEntity;
import com.imageworks.spcue.GroupDetail;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.MatcherEntity;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.grpc.filter.ActionType;
import com.imageworks.spcue.grpc.filter.ActionValueType;
import com.imageworks.spcue.grpc.filter.FilterType;
import com.imageworks.spcue.grpc.filter.MatchSubject;
import com.imageworks.spcue.grpc.filter.MatchType;
import com.imageworks.spcue.dao.ActionDao;
import com.imageworks.spcue.dao.DepartmentDao;
import com.imageworks.spcue.dao.FilterDao;
import com.imageworks.spcue.dao.GroupDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.service.FilterManager;
import com.imageworks.spcue.service.GroupManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.util.Convert;
import com.imageworks.spcue.util.CueUtil;
import java.math.BigDecimal;
import static java.util.Collections.nCopies;
import static java.util.Collections.singletonMap;
import java.util.List;
import java.util.Map;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
@TransactionConfiguration(transactionManager="transactionManager")
public class FilterManagerTests extends AbstractTransactionalJUnit4SpringContextTests
{

    @Resource
    ActionDao actionDao;

    @Resource
    FilterDao filterDao;

    @Resource
    ShowDao showDao;

    @Resource
    DepartmentDao departmentDao;

    @Resource
    GroupDao groupDao;

    @Resource
    GroupManager groupManager;

    @Resource
    JobManager jobManager;

    @Resource
    FilterManager filterManager;

    @Resource
    JobLauncher jobLauncher;

    private static String FILTER_NAME = "test_filter";

    @Before
    public void setTestMode() {
        jobLauncher.testMode = true;
    }

    public ShowInterface getShow() {
        return showDao.getShowDetail("00000000-0000-0000-0000-000000000000");
    }

    public FilterEntity buildFilter() {
        FilterEntity filter = new FilterEntity();
        filter.name = FILTER_NAME;
        filter.showId = "00000000-0000-0000-0000-000000000000";
        filter.type = FilterType.MATCH_ANY;
        filter.enabled = true;

        return filter;
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testShotEndsWith() {

        FilterEntity f = buildFilter();
        filterDao.insertFilter(f);

        MatcherEntity m = new MatcherEntity();
        m.filterId = f.getFilterId();
        m.name = "match end of shot";
        m.subject = MatchSubject.SHOT;
        m.type = MatchType.ENDS_WITH;
        m.value = ".cue";

        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");

        assertTrue(filterManager.isMatch(m, job));
        m.value = "layout";
        assertFalse(filterManager.isMatch(m, job));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testLayerNameContains() {

        FilterEntity f = buildFilter();
        filterDao.insertFilter(f);

        MatcherEntity m = new MatcherEntity();
        m.filterId = f.getFilterId();
        m.name = "layer name contains";
        m.subject = MatchSubject.LAYER_NAME;
        m.type = MatchType.CONTAINS;
        m.value = "pass_1";

        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");

        assertTrue(filterManager.isMatch(m, job));
        m.value = "pass_11111";
        assertFalse(filterManager.isMatch(m, job));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testApplyActionPauseJob() {
        FilterEntity f = buildFilter();
        filterDao.insertFilter(f);

        ActionEntity a1 = new ActionEntity();
        a1.type = ActionType.PAUSE_JOB;
        a1.filterId = f.getFilterId();
        a1.valueType = ActionValueType.BOOLEAN_TYPE;
        a1.booleanValue = true;


        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
        filterManager.applyAction(a1, job);

        assertEquals(Integer.valueOf(1),jdbcTemplate.queryForObject(
                "SELECT b_paused FROM job WHERE pk_job=?",
                Integer.class, job.getJobId()));

        a1.booleanValue = false;
        filterManager.applyAction(a1, job);
        assertEquals(Integer.valueOf(0),jdbcTemplate.queryForObject(
                "SELECT b_paused FROM job WHERE pk_job=?",
                Integer.class, job.getJobId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testApplyActionSetMemoryOptimizer() {
        FilterEntity f = buildFilter();
        filterDao.insertFilter(f);

        ActionEntity a1 = new ActionEntity();
        a1.type = ActionType.SET_MEMORY_OPTIMIZER;
        a1.filterId = f.getFilterId();
        a1.valueType = ActionValueType.BOOLEAN_TYPE;
        a1.booleanValue = false;


        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
        filterManager.applyAction(a1, job);

        List<Map<String, Object>> expected;
        List<Map<String, Object>> actual;

        expected = nCopies(2, singletonMap("B_OPTIMIZE", (Object) new BigDecimal(0)));
        actual = jdbcTemplate.queryForList(
                "SELECT b_optimize FROM layer WHERE pk_job=?",
                job.getJobId());
        assertEquals(expected, actual);

        a1.booleanValue = true;
        filterManager.applyAction(a1, job);

        expected = nCopies(2, singletonMap("B_OPTIMIZE", (Object) new BigDecimal(1)));
        actual = jdbcTemplate.queryForList(
                "SELECT b_optimize FROM layer WHERE pk_job=?",
                job.getJobId());
        assertEquals(expected, actual);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testApplyActionSetMinCores() {
        FilterEntity f = buildFilter();
        filterDao.insertFilter(f);

        ActionEntity a1 = new ActionEntity();
        a1.type = ActionType.SET_JOB_MIN_CORES;
        a1.filterId = f.getFilterId();
        a1.valueType = ActionValueType.FLOAT_TYPE;
        a1.floatValue = 10f;

        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
        filterManager.applyAction(a1, job);

        assertEquals(Integer.valueOf(Convert.coresToCoreUnits(a1.floatValue)), jdbcTemplate.queryForObject(
                "SELECT int_min_cores FROM job_resource WHERE pk_job=?",
                Integer.class, job.getJobId()));

        a1.floatValue = 100f;
        filterManager.applyAction(a1, job);
        assertEquals(Integer.valueOf(Convert.coresToCoreUnits(a1.floatValue)), jdbcTemplate.queryForObject(
                "SELECT int_min_cores FROM job_resource WHERE pk_job=?",
                Integer.class, job.getJobId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testApplyActionSetMaxCores() {
        FilterEntity f = buildFilter();
        filterDao.insertFilter(f);

        ActionEntity a1 = new ActionEntity();
        a1.type = ActionType.SET_JOB_MAX_CORES;
        a1.filterId = f.getFilterId();
        a1.valueType = ActionValueType.FLOAT_TYPE;
        a1.floatValue = 10f;

        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
        filterManager.applyAction(a1, job);

        assertEquals(Integer.valueOf(Convert.coresToCoreUnits(a1.floatValue)), jdbcTemplate.queryForObject(
                "SELECT int_max_cores FROM job_resource WHERE pk_job=?",
                Integer.class, job.getJobId()));

        a1.intValue = 100;
        filterManager.applyAction(a1, job);
        assertEquals(Integer.valueOf(Convert.coresToCoreUnits(a1.floatValue)), jdbcTemplate.queryForObject(
                "SELECT int_max_cores FROM job_resource WHERE pk_job=?",
                Integer.class, job.getJobId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testApplyActionSetPriority() {
        FilterEntity f = buildFilter();
        filterDao.insertFilter(f);

        ActionEntity a1 = new ActionEntity();
        a1.type = ActionType.SET_JOB_PRIORITY;
        a1.filterId = f.getFilterId();
        a1.valueType = ActionValueType.INTEGER_TYPE;
        a1.intValue = 100;

        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
        filterManager.applyAction(a1, job);

        assertEquals(Long.valueOf(a1.intValue), jdbcTemplate.queryForObject(
                "SELECT int_priority FROM job_resource WHERE pk_job=?",
                Long.class, job.getJobId()));

        a1.intValue = 1001;
        filterManager.applyAction(a1, job);
        assertEquals(Long.valueOf(a1.intValue), jdbcTemplate.queryForObject(
                "SELECT int_priority FROM job_resource WHERE pk_job=?",
                Long.class, job.getJobId()));
    }


    @Test
    @Transactional
    @Rollback(true)
    public void testApplyActionMoveToGroup() {

        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");

        FilterEntity f = buildFilter();
        filterDao.insertFilter(f);

        GroupDetail g = new GroupDetail();
        g.name = "Testest";
        g.showId = job.getShowId();
        g.deptId = departmentDao.getDefaultDepartment().getId();

        groupManager.createGroup(g, groupManager.getRootGroupDetail(job));

        ActionEntity a1 = new ActionEntity();
        a1.type = ActionType.MOVE_JOB_TO_GROUP;
        a1.filterId = f.getFilterId();
        a1.valueType = ActionValueType.GROUP_TYPE;
        a1.groupValue = g.id;


        filterManager.applyAction(a1, job);

        assertEquals(g.id,
                jdbcTemplate.queryForObject("SELECT pk_folder FROM job WHERE pk_job=?",
                        String.class, job.id));

        assertEquals(
                jdbcTemplate.queryForObject("SELECT pk_dept FROM folder WHERE pk_folder=?",
                        String.class, a1.groupValue),
                jdbcTemplate.queryForObject("SELECT pk_dept FROM job WHERE pk_job=?",
                        String.class, job.id));
    }


    @Test
    @Transactional
    @Rollback(true)
    public void testApplyActionSetRenderCoreLayers() {

        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));

        FilterEntity f = buildFilter();
        filterDao.insertFilter(f);

        ActionEntity a1 = new ActionEntity();
        a1.type = ActionType.SET_ALL_RENDER_LAYER_CORES;
        a1.filterId = f.getFilterId();
        a1.valueType = ActionValueType.FLOAT_TYPE;
        a1.floatValue = 40f;

        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
        filterManager.applyAction(a1, job);

        assertEquals(Integer.valueOf(Convert.coresToCoreUnits(a1.floatValue)), jdbcTemplate.queryForObject(
                "SELECT int_cores_min FROM layer WHERE pk_job=? AND str_name=?",
                Integer.class, job.getJobId(), "pass_1"));

        assertEquals(Integer.valueOf(Convert.coresToCoreUnits(.25f)), jdbcTemplate.queryForObject(
                "SELECT int_cores_min FROM layer WHERE pk_job=? AND str_name=?",
                Integer.class, job.getJobId(), "pass_1_preprocess"));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testApplyActionSetRenderLayerMemory() {

        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));

        FilterEntity f = buildFilter();
        filterDao.insertFilter(f);

        ActionEntity a1 = new ActionEntity();
        a1.type = ActionType.SET_ALL_RENDER_LAYER_MEMORY;
        a1.filterId = f.getFilterId();
        a1.valueType = ActionValueType.INTEGER_TYPE;
        a1.intValue =  CueUtil.GB8;

        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
        filterManager.applyAction(a1, job);

        assertEquals(Long.valueOf(CueUtil.GB8), jdbcTemplate.queryForObject(
                "SELECT int_mem_min FROM layer WHERE pk_job=? AND str_name=?",
                Long.class, job.getJobId(), "pass_1"));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testApplyActionSetAllRenderLayerTags() {

        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));

        FilterEntity f = buildFilter();
        filterDao.insertFilter(f);

        ActionEntity a1 = new ActionEntity();
        a1.type = ActionType.SET_ALL_RENDER_LAYER_TAGS;
        a1.filterId = f.getFilterId();
        a1.valueType = ActionValueType.STRING_TYPE;
        a1.stringValue = "blah";

        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
        filterManager.applyAction(a1, job);

        assertEquals("blah",jdbcTemplate.queryForObject("SELECT str_tags FROM layer WHERE pk_job=? AND str_name=?",
                String.class,job.getJobId(), "pass_1"));

        assertEquals("general",jdbcTemplate.queryForObject("SELECT str_tags FROM layer WHERE pk_job=? AND str_name=?",
                String.class,job.getJobId(), "pass_1_preprocess"));
    }
}

