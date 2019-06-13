
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

import com.imageworks.spcue.*;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.*;
import com.imageworks.spcue.grpc.filter.*;
import com.imageworks.spcue.grpc.job.Layer;
import com.imageworks.spcue.service.*;
import com.imageworks.spcue.util.Convert;
import com.imageworks.spcue.util.CueUtil;
import org.junit.Before;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import java.io.File;

import static org.hamcrest.Matchers.contains;
import static org.junit.Assert.*;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class FilterManagerTests extends AbstractTransactionalJUnit4SpringContextTests {

    @Autowired
    FilterDao filterDao;

    @Autowired
    ShowDao showDao;

    @Autowired
    GroupManager groupManager;

    @Autowired
    JobManager jobManager;

    @Autowired
    FilterManager filterManager;

    @Autowired
    JobLauncher jobLauncher;

    @Autowired
    JobDao jobDao;

    @Autowired
    LayerDao layerDao;

    @Autowired
    GroupDao groupDao;

    @Autowired
    Whiteboard whiteboard;

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

        assertTrue(jobDao.getJobDetail(job.getJobId()).isPaused);

        a1.booleanValue = false;
        filterManager.applyAction(a1, job);
        assertFalse(jobDao.getJobDetail(job.getJobId()).isPaused);
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

        assertTrue(
                whiteboard.getLayers(job)
                        .getLayersList()
                        .stream()
                        .noneMatch(Layer::getMemoryOptimizerEnabled));

        a1.booleanValue = true;
        filterManager.applyAction(a1, job);
        assertTrue(
                whiteboard.getLayers(job)
                        .getLayersList()
                        .stream()
                        .allMatch(Layer::getMemoryOptimizerEnabled));
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

        assertEquals(
                Convert.coresToCoreUnits(a1.floatValue),
                jobDao.getJobDetail(job.getJobId()).minCoreUnits,
                0);

        a1.floatValue = 100f;
        filterManager.applyAction(a1, job);
        assertEquals(
                Convert.coresToCoreUnits(a1.floatValue),
                jobDao.getJobDetail(job.getJobId()).minCoreUnits,
                0);
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

        assertEquals(
                Convert.coresToCoreUnits(a1.floatValue),
                jobDao.getJobDetail(job.getJobId()).maxCoreUnits,
                0);

        a1.intValue = 100;
        filterManager.applyAction(a1, job);
        assertEquals(
                Convert.coresToCoreUnits(a1.floatValue),
                jobDao.getJobDetail(job.getJobId()).maxCoreUnits,
                0);
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

        assertEquals(
                a1.intValue,
                jobDao.getJobDetail(job.getJobId()).priority);

        a1.intValue = 1001;
        filterManager.applyAction(a1, job);
        assertEquals(
                a1.intValue,
                jobDao.getJobDetail(job.getJobId()).priority);
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

        groupManager.createGroup(g, groupManager.getRootGroupDetail(job));

        ActionEntity a1 = new ActionEntity();
        a1.type = ActionType.MOVE_JOB_TO_GROUP;
        a1.filterId = f.getFilterId();
        a1.valueType = ActionValueType.GROUP_TYPE;
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

        FilterEntity f = buildFilter();
        filterDao.insertFilter(f);

        ActionEntity a1 = new ActionEntity();
        a1.type = ActionType.SET_ALL_RENDER_LAYER_CORES;
        a1.filterId = f.getFilterId();
        a1.valueType = ActionValueType.FLOAT_TYPE;
        a1.floatValue = 40f;

        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
        filterManager.applyAction(a1, job);

        assertEquals(
                Convert.coresToCoreUnits(a1.floatValue),
                layerDao.findLayerDetail(job, "pass_1").minimumCores,
                0);

        assertEquals(
                Convert.coresToCoreUnits(.25f),
                layerDao.findLayerDetail(job, "pass_1_preprocess").minimumCores,
                0);
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

        assertEquals(
                CueUtil.GB8,
                layerDao.findLayerDetail(job, "pass_1").minimumMemory);
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

        assertThat(layerDao.findLayerDetail(job, "pass_1").tags, contains("blah"));
        assertThat(layerDao.findLayerDetail(job, "pass_1_preprocess").tags, contains("general"));
    }
}

