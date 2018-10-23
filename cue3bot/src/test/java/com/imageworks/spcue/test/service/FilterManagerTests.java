
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
import com.imageworks.spcue.ActionDetail;
import com.imageworks.spcue.FilterDetail;
import com.imageworks.spcue.GroupDetail;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.MatcherDetail;
import com.imageworks.spcue.Show;
import com.imageworks.spcue.CueIce.ActionType;
import com.imageworks.spcue.CueIce.ActionValueType;
import com.imageworks.spcue.CueIce.FilterType;
import com.imageworks.spcue.CueIce.MatchSubject;
import com.imageworks.spcue.CueIce.MatchType;
import com.imageworks.spcue.dao.ActionDao;
import com.imageworks.spcue.dao.DepartmentDao;
import com.imageworks.spcue.dao.FilterDao;
import com.imageworks.spcue.dao.GroupDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.LayerDao;
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
    FilterDao filterDao;

    @Resource
    ShowDao showDao;

    @Resource
    DepartmentDao departmentDao;

    @Resource
    GroupManager groupManager;

    @Resource
    JobManager jobManager;

    @Resource
    FilterManager filterManager;

    @Resource
    JobLauncher jobLauncher;

    @Resource
    JobDao jobDao;

    @Resource
    LayerDao layerDao;

    @Resource
    GroupDao groupDao;

    private static String FILTER_NAME = "test_filter";

    @Before
    public void setTestMode() {
        jobLauncher.testMode = true;
    }

    public Show getShow() {
        return showDao.getShowDetail("00000000-0000-0000-0000-000000000000");
    }

    public FilterDetail buildFilter() {
        FilterDetail filter = new FilterDetail();
        filter.name = FILTER_NAME;
        filter.showId = "00000000-0000-0000-0000-000000000000";
        filter.type = FilterType.MatchAny;
        filter.enabled = true;

        return filter;
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testShotEndsWith() {

        FilterDetail f = buildFilter();
        filterDao.insertFilter(f);

        MatcherDetail m = new MatcherDetail();
        m.filterId = f.getFilterId();
        m.name = "match end of shot";
        m.subject = MatchSubject.Shot;
        m.type = MatchType.EndsWith;
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

        FilterDetail f = buildFilter();
        filterDao.insertFilter(f);

        MatcherDetail m = new MatcherDetail();
        m.filterId = f.getFilterId();
        m.name = "layer name contains";
        m.subject = MatchSubject.LayerName;
        m.type = MatchType.Contains;
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
        FilterDetail f = buildFilter();
        filterDao.insertFilter(f);

        ActionDetail a1 = new ActionDetail();
        a1.type = ActionType.PauseJob;
        a1.filterId = f.getFilterId();
        a1.valueType = ActionValueType.BooleanType;
        a1.booleanValue = true;


        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
        filterManager.applyAction(a1, job);

        assertTrue(jobDao.getJobDetail(job.getJobId()).isPaused);

        a1.booleanValue = false;
        filterManager.applyAction(a1, job);
        assertFalse(jobDao.getJobDetail(job.getJobId()).isPaused);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testApplyActionSetMemoryOptimizer() {
        FilterDetail f = buildFilter();
        filterDao.insertFilter(f);

        ActionDetail a1 = new ActionDetail();
        a1.type = ActionType.SetMemoryOptimizer;
        a1.filterId = f.getFilterId();
        a1.valueType = ActionValueType.BooleanType;
        a1.booleanValue = false;


        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
        filterManager.applyAction(a1, job);

        assertTrue(layerDao.getLayerDetails(job).stream().noneMatch(
                layerDetail -> layerDetail.memoryOptimizerEnabled));

        a1.booleanValue = true;
        filterManager.applyAction(a1, job);
        assertTrue(layerDao.getLayerDetails(job).stream().allMatch(
                layerDetail -> layerDetail.memoryOptimizerEnabled));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testApplyActionSetMinCores() {
        FilterDetail f = buildFilter();
        filterDao.insertFilter(f);

        ActionDetail a1 = new ActionDetail();
        a1.type = ActionType.SetJobMinCores;
        a1.filterId = f.getFilterId();
        a1.valueType = ActionValueType.FloatType;
        a1.floatValue = 10f;

        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
        filterManager.applyAction(a1, job);

        assertEquals(
                Integer.valueOf(Convert.coresToCoreUnits(a1.floatValue)),
                (Integer) jobDao.getJobDetail(job.getJobId()).minCoreUnits);

        a1.floatValue = 100f;
        filterManager.applyAction(a1, job);
        assertEquals(
                Integer.valueOf(Convert.coresToCoreUnits(a1.floatValue)),
                (Integer) jobDao.getJobDetail(job.getJobId()).minCoreUnits);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testApplyActionSetMaxCores() {
        FilterDetail f = buildFilter();
        filterDao.insertFilter(f);

        ActionDetail a1 = new ActionDetail();
        a1.type = ActionType.SetJobMaxCores;
        a1.filterId = f.getFilterId();
        a1.valueType = ActionValueType.FloatType;
        a1.floatValue = 10f;

        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
        filterManager.applyAction(a1, job);

        assertEquals(
                Integer.valueOf(Convert.coresToCoreUnits(a1.floatValue)),
                (Integer) jobDao.getJobDetail(job.getJobId()).maxCoreUnits);

        a1.intValue = 100;
        filterManager.applyAction(a1, job);
        assertEquals(
                Integer.valueOf(Convert.coresToCoreUnits(a1.floatValue)),
                (Integer) jobDao.getJobDetail(job.getJobId()).maxCoreUnits);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testApplyActionSetPriority() {
        FilterDetail f = buildFilter();
        filterDao.insertFilter(f);

        ActionDetail a1 = new ActionDetail();
        a1.type = ActionType.SetJobPriority;
        a1.filterId = f.getFilterId();
        a1.valueType = ActionValueType.IntegerType;
        a1.intValue = 100;

        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
        filterManager.applyAction(a1, job);

        assertEquals(
                Long.valueOf(a1.intValue),
                Long.valueOf(jobDao.getJobDetail(job.getJobId()).priority));

        a1.intValue = 1001;
        filterManager.applyAction(a1, job);
        assertEquals(
                Long.valueOf(a1.intValue),
                Long.valueOf(jobDao.getJobDetail(job.getJobId()).priority));
    }


    @Test
    @Transactional
    @Rollback(true)
    public void testApplyActionMoveToGroup() {

        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");

        FilterDetail f = buildFilter();
        filterDao.insertFilter(f);

        GroupDetail g = new GroupDetail();
        g.name = "Testest";
        g.showId = job.getShowId();
        g.deptId = departmentDao.getDefaultDepartment().getId();

        groupManager.createGroup(g, groupManager.getRootGroupDetail(job));

        ActionDetail a1 = new ActionDetail();
        a1.type = ActionType.MoveJobToGroup;
        a1.filterId = f.getFilterId();
        a1.valueType = ActionValueType.GroupType;
        a1.groupValue = g.id;


        filterManager.applyAction(a1, job);

        assertEquals(g.id, jobDao.getJobDetail(job.getJobId()).groupId);

        assertEquals(
                groupDao.getGroupDetail(a1.groupValue).deptId,
                jobDao.getJobDetail(job.getJobId()).deptId);
    }


    @Test
    @Transactional
    @Rollback(true)
    public void testApplyActionSetRenderCoreLayers() {

        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));

        FilterDetail f = buildFilter();
        filterDao.insertFilter(f);

        ActionDetail a1 = new ActionDetail();
        a1.type = ActionType.SetAllRenderLayerCores;
        a1.filterId = f.getFilterId();
        a1.valueType = ActionValueType.FloatType;
        a1.floatValue = 40f;

        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
        filterManager.applyAction(a1, job);

        assertEquals(
                Integer.valueOf(Convert.coresToCoreUnits(a1.floatValue)),
                (Integer) layerDao.findLayerDetail(job, "pass_1").minimumCores);

        assertEquals(
                Integer.valueOf(Convert.coresToCoreUnits(.25f)),
                (Integer) layerDao.findLayerDetail(job, "pass_1_preprocess").minimumCores);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testApplyActionSetRenderLayerMemory() {

        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));

        FilterDetail f = buildFilter();
        filterDao.insertFilter(f);

        ActionDetail a1 = new ActionDetail();
        a1.type = ActionType.SetAllRenderLayerMemory;
        a1.filterId = f.getFilterId();
        a1.valueType = ActionValueType.IntegerType;
        a1.intValue =  CueUtil.GB8;

        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
        filterManager.applyAction(a1, job);

        assertEquals(
                Long.valueOf(CueUtil.GB8),
                Long.valueOf(layerDao.findLayerDetail(job, "pass_1").minimumMemory));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testApplyActionSetAllRenderLayerTags() {

        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));

        FilterDetail f = buildFilter();
        filterDao.insertFilter(f);

        ActionDetail a1 = new ActionDetail();
        a1.type = ActionType.SetAllRenderLayerTags;
        a1.filterId = f.getFilterId();
        a1.valueType = ActionValueType.StringType;
        a1.stringValue = "blah";

        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
        filterManager.applyAction(a1, job);

        assertEquals(
                "blah",
                String.join(" ", layerDao.findLayerDetail(job, "pass_1").tags));

        assertEquals(
                "general",
                String.join(" ", layerDao.findLayerDetail(job, "pass_1_preprocess").tags));
    }
}

