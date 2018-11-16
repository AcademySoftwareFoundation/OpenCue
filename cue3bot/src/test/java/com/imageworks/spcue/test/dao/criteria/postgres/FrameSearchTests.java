
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

package com.imageworks.spcue.test.dao.criteria.postgres;

import java.io.File;
import java.util.List;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

import javax.annotation.Resource;

import com.google.common.collect.ImmutableList;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.test.context.transaction.TransactionConfiguration;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dao.criteria.FrameSearchFactory;
import com.imageworks.spcue.dao.criteria.FrameSearchInterface;
import com.imageworks.spcue.grpc.job.FrameSearchCriteria;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.test.AssumingPostgresEngine;
import com.imageworks.spcue.util.CueUtil;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotEquals;
import static org.junit.Assert.assertTrue;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
@TransactionConfiguration(transactionManager="transactionManager")
public class FrameSearchTests extends AbstractTransactionalJUnit4SpringContextTests {

    @Autowired
    @Rule
    public AssumingPostgresEngine assumingPostgresEngine;

    @Resource
    private JobLauncher jobLauncher;

    @Resource
    private JobDao jobDao;

    @Resource
    private FrameSearchFactory frameSearchFactory;

    @Resource
    private FrameDao frameDao;

    @Resource
    private LayerDao layerDao;

    @Before
    public void launchTestJobs() {
        ClassLoader classLoader = getClass().getClassLoader();
        File file = new File(
                classLoader.getResource("conf/jobspec/jobspec_depend_test.xml").getFile());

        jobLauncher.testMode = true;
        jobLauncher.launch(file);
    }

    @Test
    @Transactional
    @Rollback
    public void testGetCriteria() {
        JobInterface job = jobDao.findJob("pipe-dev.cue-testuser_depend_test_a");
        FrameSearchCriteria criteria = FrameSearchInterface.criteriaFactory();

        FrameSearchInterface frameSearch = frameSearchFactory.create(job, criteria);

        assertEquals(criteria, frameSearch.getCriteria());
    }

    @Test
    @Transactional
    @Rollback
    public void testSetCriteria() {
        FrameSearchCriteria criteria = FrameSearchInterface.criteriaFactory()
                .toBuilder()
                .setFrameRange("1-10")
                .build();
        FrameSearchInterface frameSearch = frameSearchFactory.create();

        // Ensure we can distinguish between the default and non-default criteria.
        assertNotEquals(criteria, frameSearch.getCriteria());

        frameSearch.setCriteria(criteria);

        assertEquals(criteria, frameSearch.getCriteria());
    }

    @Test
    @Transactional
    @Rollback
    public void testFilterByFrameIds() {
        JobInterface job = jobDao.findJob("pipe-dev.cue-testuser_depend_test_a");
        FrameSearchInterface frameSearch = frameSearchFactory.create();
        LayerInterface layer = layerDao.getLayers(job).get(0);
        FrameInterface frame1 = frameDao.findFrame(layer, 1);
        FrameInterface frame2 = frameDao.findFrame(layer, 2);
        frameSearch.filterByFrameIds(ImmutableList.of(frame1.getFrameId(), frame2.getFrameId()));

        List<FrameInterface> frames = frameDao.findFrames(frameSearch);

        assertThat(frames).containsExactlyInAnyOrder(frame1, frame2);
    }

    @Test
    @Transactional
    @Rollback
    public void testFilterByFrame() {
        JobInterface job = jobDao.findJob("pipe-dev.cue-testuser_depend_test_a");
        FrameSearchInterface frameSearch = frameSearchFactory.create();
        LayerInterface layer = layerDao.getLayers(job).get(0);
        FrameInterface frame1 = frameDao.findFrame(layer, 1);
        frameSearch.filterByFrame(frame1);

        List<FrameInterface> frames = frameDao.findFrames(frameSearch);

        assertThat(frames).containsExactly(frame1);
    }

    @Test
    @Transactional
    @Rollback
    public void testFilterByJob() {
        JobInterface job = jobDao.findJob("pipe-dev.cue-testuser_depend_test_a");
        String jobId = job.getJobId();
        FrameSearchInterface frameSearch = frameSearchFactory.create();
        frameSearch.filterByJob(job);

        List<FrameInterface> frames = frameDao.findFrames(frameSearch);

        assertEquals(20, frames.size());
        assertTrue(frames.stream().allMatch(frame -> frame.getJobId().equals(jobId)));
    }

    @Test
    @Transactional
    @Rollback
    public void testFilterByLayer() {
        JobInterface job = jobDao.findJob("pipe-dev.cue-testuser_depend_test_a");
        LayerInterface layer = layerDao.getLayers(job).get(0);
        FrameSearchInterface frameSearch = frameSearchFactory.create();
        frameSearch.filterByLayer(layer);

        List<FrameInterface> frames = frameDao.findFrames(frameSearch);

        assertTrue(
                frames.stream().allMatch(frame -> frame.getLayerId().equals(layer.getLayerId())));
    }

    @Test
    @Transactional
    @Rollback
    public void testFilterByFrameStates() {
        JobInterface job = jobDao.findJob("pipe-dev.cue-testuser_depend_test_b");
        LayerInterface layer = layerDao.getLayers(job).get(1);
        IntStream.range(1, 11).forEach(
                i -> frameDao.updateFrameState(frameDao.findFrame(layer, i), FrameState.SUCCEEDED));
        FrameSearchInterface frameSearch = frameSearchFactory.create();
        frameSearch.filterByFrameStates(ImmutableList.of(FrameState.SUCCEEDED));

        List<FrameInterface> frames = frameDao.findFrames(frameSearch);

        assertEquals(10, frames.size());
        assertTrue(
                frames.stream().allMatch(
                        frame -> frameDao.getFrameDetail(
                                frame.getFrameId()).state.equals(FrameState.SUCCEEDED)));
    }

    @Test
    @Transactional
    @Rollback
    public void testFilterByFrameSet() {
        JobInterface job = jobDao.findJob("pipe-dev.cue-testuser_depend_test_a");
        LayerInterface layer = layerDao.getLayers(job).get(0);
        FrameSearchInterface frameSearch = frameSearchFactory.create();
        frameSearch.filterByFrameSet("5-6");

        List<FrameInterface> frames = frameDao.findFrames(frameSearch);

        assertEquals(8, frames.size());
        assertThat(
                frames.stream().map(
                        frame -> frameDao.getFrameDetail(frame.getFrameId()).number)
                        .collect(Collectors.toList()))
                .containsOnly(5, 6);
    }

    @Test
    @Transactional
    @Rollback
    public void filterByMemoryRange() {
        JobInterface job = jobDao.findJob("pipe-dev.cue-testuser_depend_test_a");
        LayerInterface layer = layerDao.getLayers(job).get(0);
        IntStream.range(1, 11).forEach(
                i -> {
                    FrameInterface frame = frameDao.findFrame(layer, i);
                    frameDao.updateFrameState(frame, FrameState.RUNNING);
                    frameDao.updateFrameMemoryUsage(frame, CueUtil.GB * 5, CueUtil.GB);
                });

        FrameSearchInterface frameSearch = frameSearchFactory.create();
        frameSearch.filterByMemoryRange("4.2-7.1");

        List<FrameDetail> frames = frameDao.findFrameDetails(frameSearch);

        assertEquals(10, frames.size());
        assertTrue(frames.stream().allMatch(frame -> frame.maxRss == CueUtil.GB * 5));
    }

    // filterByDurationRange
    @Test
    @Transactional
    @Rollback
    public void filterByDurationRange() {
        JobInterface job = jobDao.findJob("pipe-dev.cue-testuser_depend_test_a");
        LayerInterface layer = layerDao.getLayers(job).get(0);
        IntStream.range(4, 6).forEach(
                i -> {
                    frameDao.updateFrameStarted(new VirtualProc(), frameDao.findFrame(layer, i));
                    frameDao.updateFrameState(frameDao.findFrame(layer, i), FrameState.RUNNING);
                    try {
                        Thread.sleep(1000);
                    } catch (InterruptedException e) {
                        throw new RuntimeException("interrupted while letting frame run");
                    }
                    // frameDao.updateFrameCleared(frameDao.findFrame(layer, i));
                    // frameDao.updateFrameStopped(frameDao.findFrame(layer, i), FrameState.SUCCEEDED, 0);
                });

        /*try {
            Thread.sleep(2000);
        } catch (InterruptedException e) {
            throw new RuntimeException("interrupted while letting frame run");
        }*/

        FrameSearchInterface frameSearch = frameSearchFactory.create();
        frameSearch.filterByDurationRange("0");

        List<FrameDetail> frames = frameDao.findFrameDetails(frameSearch);

        frames.forEach(frameDetail -> {
            System.out.println(frameDetail.state);
            System.out.println(frameDetail.dateStarted);
            System.out.println(frameDetail.dateStopped);
            System.out.println(
                    jdbcTemplate.queryForObject(
                            "SELECT find_duration(?, ?)",
                            String.class,
                            frameDetail.dateStarted,
                            frameDetail.dateStopped));
            System.out.println("--------");
        });

        // assertEquals(10, frames.size());
        // assertTrue(frames.stream().allMatch(frame -> frame.maxRss == CueUtil.GB * 5));
    }

    // filterByChangeDate
}
