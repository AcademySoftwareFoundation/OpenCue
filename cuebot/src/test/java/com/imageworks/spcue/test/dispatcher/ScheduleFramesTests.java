
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



package com.imageworks.spcue.test.dao.postgres;

import java.io.File;
import java.sql.Timestamp;
import javax.annotation.Resource;

import org.junit.Before;
import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dispatcher.DispatchSupport;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.ScheduledDispatchFrames;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class ScheduleFramesTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Resource
    HostDao hostDao;

    @Resource
    LayerDao layerDao;

    @Resource
    JobManager jobManager;

    @Resource
    DispatchSupport dispatchSupport;

    @Resource
    HostManager hostManager;

    @Resource
    AdminManager adminManager;

    @Resource
    Dispatcher dispatcher;

    @Resource
    JobLauncher jobLauncher;

    private static final String HOSTNAME="beta";

    public DispatchHost getHost() {
        return hostDao.findDispatchHost(HOSTNAME);
    }

    public JobDetail getJob1() {
        return jobManager.findJobDetail(
                "pipe-dev.cue-testuser_shell_dispatch_test_v1");
    }

    public JobDetail getJob2() {
        return jobManager.findJobDetail(
                "pipe-dev.cue-testuser_shell_dispatch_test_v2");
    }

    @Before
    public void launchJob() {
        dispatcher.setTestMode(true);
        jobLauncher.testMode = true;
        jobLauncher.launch(
                new File("src/test/resources/conf/jobspec/jobspec_dispatch_test.xml"));
    }

    @Before
    public void createHost() {
        RenderHost host = RenderHost.newBuilder()
                .setName(HOSTNAME)
                .setBootTime(1192369572)
                .setFreeMcp(76020)
                .setFreeMem(53500)
                .setFreeSwap(20760)
                .setLoad(1)
                .setTotalMcp(195430)
                .setTotalMem(8173264)
                .setTotalSwap(20960)
                .setNimbyEnabled(false)
                .setNumProcs(2)
                .setCoresPerProc(100)
                .addTags("test")
                .setState(HardwareState.UP)
                .setFacility("spi")
                .putAttributes("SP_OS", "Linux")
                .build();

        hostManager.createHost(host,
                adminManager.findAllocationDetail("spi", "general"));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testScheduleNextDispatchFrameByHost() {
        DispatchHost host = getHost();
        JobDetail job = getJob1();

        for (LayerDetail layer: layerDao.getLayerDetails(job)) {
            assertTrue(layer.tags.contains("general"));
        }

        assertTrue(jdbcTemplate.queryForObject(
                "SELECT str_tags FROM host WHERE pk_host=?",String.class,
                host.id).contains("general"));

        try (ScheduledDispatchFrames frames =
                dispatchSupport.scheduleNextDispatchFrames(job, host, 1)) {
            assertEquals(1, frames.size());
            assertEquals("0001-pass_1", frames.iterator().next().name);
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testScheduleNextDispatchFrameByProc() {
        DispatchHost host = getHost();
        JobDetail job = getJob1();
        VirtualProc proc = null;

        try (ScheduledDispatchFrames frames =
                dispatchSupport.scheduleNextDispatchFrames(job, host, 1)) {
            assertEquals(1, frames.size());
            DispatchFrame frame = frames.iterator().next();
            assertEquals("0001-pass_1", frame.name);

            proc = VirtualProc.build(host, frame);
            proc.coresReserved = 100;
            dispatcher.dispatch(frame, proc);
            frames.markFrameAsDispatched(frame);
        }

        try (ScheduledDispatchFrames frames =
                dispatchSupport.scheduleNextDispatchFrames(job, proc, 1)) {
            assertEquals(1, frames.size());
            DispatchFrame frame = frames.iterator().next();
            assertEquals("0001-pass_2", frame.name);
            dispatcher.dispatch(frame, proc);
            frames.markFrameAsDispatched(frame);
        }

        try (ScheduledDispatchFrames frames =
                dispatchSupport.scheduleNextDispatchFrames(job, proc, 1)) {
            assertEquals(1, frames.size());
            DispatchFrame frame = frames.iterator().next();
            assertEquals("0002-pass_1", frame.name);
            dispatcher.dispatch(frame, proc);
            frames.markFrameAsDispatched(frame);
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testScheduleNextDispatchFramesByProc() {
        DispatchHost host = getHost();
        JobDetail job = getJob1();
        VirtualProc proc = null;

        try (ScheduledDispatchFrames frames =
                dispatchSupport.scheduleNextDispatchFrames(job, host, 10)) {
            assertEquals(10, frames.size());
            DispatchFrame frame = frames.iterator().next();
            proc = VirtualProc.build(host, frame);
            proc.coresReserved = 100;
            dispatcher.dispatch(frame, proc);
            frames.markFrameAsDispatched(frame);
        }

        try (ScheduledDispatchFrames frames =
                dispatchSupport.scheduleNextDispatchFrames(job, proc, 1)) {
            assertEquals(1, frames.size());
            DispatchFrame frame = frames.iterator().next();
            assertEquals(frame.name, "0001-pass_2");
            dispatcher.dispatch(frame, proc);
            frames.markFrameAsDispatched(frame);
        }

        try (ScheduledDispatchFrames frames =
                dispatchSupport.scheduleNextDispatchFrames(job, proc, 1)) {
            assertEquals(1, frames.size());
            DispatchFrame frame = frames.iterator().next();
            assertEquals(frame.name,"0002-pass_1");
            dispatcher.dispatch(frame, proc);
            frames.markFrameAsDispatched(frame);
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testScheduleNextDispatchFramesByHostAndJobLocal() {
        DispatchHost host = getHost();
        JobDetail job = getJob1();
        host.isLocalDispatch = true;
        try (ScheduledDispatchFrames frames =
                dispatchSupport.scheduleNextDispatchFrames(job, host, 10)) {
            assertEquals(10, frames.size());
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testScheduleNextDispatchFramesByHostAndLayerLocal() {
        DispatchHost host = getHost();
        JobDetail job = getJob1();
        LayerInterface layer = jobManager.getLayers(job).get(0);
        host.isLocalDispatch = true;

        try (ScheduledDispatchFrames frames =
                dispatchSupport.scheduleNextDispatchFrames(layer, host, 10)) {
            assertEquals(10, frames.size());
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testScheduleNextDispatchFramesByProcAndJobLocal() {
        DispatchHost host = getHost();
        JobDetail job = getJob1();
        VirtualProc proc = null;
        host.isLocalDispatch = true;
        try (ScheduledDispatchFrames frames =
                dispatchSupport.scheduleNextDispatchFrames(job, host, 10)) {
            assertEquals(10, frames.size());

            DispatchFrame frame = frames.iterator().next();
            proc = VirtualProc.build(host, frame);
            proc.coresReserved = 100;
            proc.isLocalDispatch = true;
        }

        try (ScheduledDispatchFrames frames =
                dispatchSupport.scheduleNextDispatchFrames(job, proc, 10)) {
            assertEquals(10, frames.size());
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testScheduleNextDispatchFramesByProcAndLayerLocal() {
        DispatchHost host = getHost();
        JobDetail job = getJob1();
        LayerInterface layer = jobManager.getLayers(job).get(0);
        VirtualProc proc = null;
        host.isLocalDispatch = true;

        try (ScheduledDispatchFrames frames =
                dispatchSupport.scheduleNextDispatchFrames(layer, host, 10)) {
            assertEquals(10, frames.size());

            DispatchFrame frame = frames.iterator().next();
            proc = VirtualProc.build(host, frame);
            proc.coresReserved = 100;
            proc.isLocalDispatch = true;
        }

        try (ScheduledDispatchFrames frames =
                dispatchSupport.scheduleNextDispatchFrames(layer, proc, 10)) {
            assertEquals(10, frames.size());
        }
    }

    private void checkScheduledNextDispatchFrames(JobDetail job, DispatchHost host, int index,
            boolean doDispatch) {
        try (ScheduledDispatchFrames frames =
                dispatchSupport.scheduleNextDispatchFrames(job, host, 10)) {
            assertEquals(10, frames.size());

            VirtualProc proc = null;
            int pass = 1;
            for (DispatchFrame frame : frames) {
                String name = String.format("%04d-pass_%d", index, pass);
                assertEquals(name, frame.name);
                if (++pass > 2) {
                    pass = 1;
                    index++;
                }

                if (doDispatch) {
                    if (proc == null) {
                        proc = VirtualProc.build(host, frame);
                        proc.coresReserved = 100;
                    }
                    dispatcher.dispatch(frame, proc);
                    frames.markFrameAsDispatched(frame);
                }
            }
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testScheduleUnscheduleSchedule() {
        DispatchHost host = getHost();
        JobDetail job = getJob1();

        checkScheduledNextDispatchFrames(job, host, 1, false);

        /*
         * ScheduledDispatchFrames automatically unscheduled the all scheduled frames. 
         * scheduleNextDispatchFrames will return the exact same frames in the exact same order
         * again.
         */

        checkScheduledNextDispatchFrames(job, host, 1, false);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testScheduleDispatchSchedule() {
        DispatchHost host = getHost();
        JobDetail job = getJob1();

        checkScheduledNextDispatchFrames(job, host, 1, true);
        checkScheduledNextDispatchFrames(job, host, 6, true);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testScheduleParallel() {
        DispatchHost host = getHost();
        JobDetail job = getJob1();

        try (ScheduledDispatchFrames frames0 =
                dispatchSupport.scheduleNextDispatchFrames(job, host, 10)) {
            assertEquals(10, frames0.size());
            DispatchFrame frame0 = frames0.iterator().next();
            assertEquals("0001-pass_1", frame0.name);

            try (ScheduledDispatchFrames frames1 =
                    dispatchSupport.scheduleNextDispatchFrames(job, host, 10)) {
                assertEquals(10, frames1.size());
                DispatchFrame frame1 = frames1.iterator().next();
                assertEquals("0006-pass_1", frame1.name);
            }
        }

        /*
         * ScheduledDispatchFrames automatically unscheduled the all scheduled frames. 
         * scheduleNextDispatchFrames will return the exact same frames in the exact same order
         * again.
         */
        try (ScheduledDispatchFrames frames =
                dispatchSupport.scheduleNextDispatchFrames(job, host, 1)) {
            assertEquals(1, frames.size());
            DispatchFrame frame = frames.iterator().next();
            assertEquals(frame.name,"0001-pass_1");
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFailSafe() {
        DispatchHost host = getHost();
        JobDetail job = getJob1();

        try (ScheduledDispatchFrames frames =
                dispatchSupport.scheduleNextDispatchFrames(job, host, 10)) {
            assertEquals(10, frames.size());
            int pass = 1;
            int index = 1;
            for (DispatchFrame frame : frames) {
                String name = String.format("%04d-pass_%d", index, pass);
                assertEquals(name, frame.name);
                if (++pass > 2) {
                    pass = 1;
                    index++;
                }
                // Testing the situation that frames were marked as dispatched
                // but actually they were not dispatched for some reason.
                frames.markFrameAsDispatched(frame);
            }
        }

        // Verify the 10 frames are still scheduled.
        try (ScheduledDispatchFrames frames =
                dispatchSupport.scheduleNextDispatchFrames(job, host, 1)) {
            assertEquals(1, frames.size());
            DispatchFrame frame = frames.iterator().next();
            assertEquals(frame.name,"0006-pass_1");
        }

        // Override the scheduled 10 frames' ts_scheduled to mock the fail-safe timeout.
        jdbcTemplate.update(
            "UPDATE " +
                "frame " +
            "SET " +
                "ts_scheduled = ?" +
            "WHERE " +
                "b_scheduled = true", new Timestamp(System.currentTimeMillis() - 61 * 1000));

        // scheduleNextDispatchFrames will return the exact same frames in the exact same order
        // again because of the fail-safe logic.
        try (ScheduledDispatchFrames frames =
                dispatchSupport.scheduleNextDispatchFrames(job, host, 10)) {
            assertEquals(10, frames.size());
            int pass = 1;
            int index = 1;
            for (DispatchFrame frame : frames) {
                String name = String.format("%04d-pass_%d", index, pass);
                assertEquals(name, frame.name);
                if (++pass > 2) {
                    pass = 1;
                    index++;
                }
            }
        }
    }
}
