
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

package com.imageworks.spcue.test.dispatcher;

import java.io.File;
import java.sql.Timestamp;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.ThreadPoolExecutor;
import javax.annotation.Resource;

import com.imageworks.spcue.dispatcher.DispatchSupport;
import com.imageworks.spcue.dispatcher.HostReportQueue;
import com.imageworks.spcue.dispatcher.FrameCompleteHandler;
import com.imageworks.spcue.grpc.job.FrameState;
import org.junit.Before;
import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.AllocationEntity;
import com.imageworks.spcue.CommentDetail;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.HostReportHandler;
import com.imageworks.spcue.FacilityInterface;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.host.LockState;
import com.imageworks.spcue.grpc.report.CoreDetail;
import com.imageworks.spcue.grpc.report.HostReport;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.grpc.report.RunningFrameInfo;
import com.imageworks.spcue.grpc.report.FrameCompleteReport;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.CommentManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.test.TransactionalTest;
import com.imageworks.spcue.util.CueUtil;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.LayerDetail;

import java.util.UUID;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;

@ContextConfiguration
public class HostReportHandlerTests extends TransactionalTest {

    @Resource
    AdminManager adminManager;

    @Resource
    HostManager hostManager;

    @Resource
    HostReportHandler hostReportHandler;

    @Resource
    FrameCompleteHandler frameCompleteHandler;

    @Resource
    Dispatcher dispatcher;

    @Resource
    JobLauncher jobLauncher;

    @Resource
    JobManager jobManager;

    @Resource
    CommentManager commentManager;

    private static final String HOSTNAME = "beta";
    private static final String NEW_HOSTNAME = "gamma";
    private String hostname;
    private String hostname2;
    private static final String SUBJECT_COMMENT_FULL_TEMP_DIR =
            "Host set to REPAIR for not having enough storage "
                    + "space on the temporary directory (mcp)";
    private static final String CUEBOT_COMMENT_USER = "cuebot";

    @Before
    public void setTestMode() {
        dispatcher.setTestMode(true);
    }

    @Before
    public void createHost() {
        hostname = UUID.randomUUID().toString().substring(0, 8);
        hostname2 = UUID.randomUUID().toString().substring(0, 8);
        hostManager.createHost(getRenderHost(hostname),
                adminManager.findAllocationDetail("spi", "general"));
        hostManager.createHost(getRenderHost(hostname2),
                adminManager.findAllocationDetail("spi", "general"));
    }

    private static CoreDetail getCoreDetail(int total, int idle, int booked, int locked) {
        return CoreDetail.newBuilder().setTotalCores(total).setIdleCores(idle)
                .setBookedCores(booked).setLockedCores(locked).build();
    }

    private DispatchHost getHost(String hostname) {
        return hostManager.findDispatchHost(hostname);
    }

    private static RenderHost.Builder getRenderHostBuilder(String hostname) {
        return RenderHost.newBuilder().setName(hostname).setBootTime(1192369572)
                // The minimum amount of free space in the temporary directory to book a host.
                .setFreeMcp(CueUtil.GB).setFreeMem(CueUtil.GB8).setFreeSwap(CueUtil.GB2).setLoad(0)
                .setTotalMcp(CueUtil.GB4).setTotalMem(CueUtil.GB8).setTotalSwap(CueUtil.GB2)
                .setNimbyEnabled(false).setNumProcs(16).setCoresPerProc(100).addTags("test")
                .setState(HardwareState.UP).setFacility("spi").putAttributes("SP_OS", "Linux")
                .setNumGpus(0).setFreeGpuMem(0).setTotalGpuMem(0);
    }

    private static RenderHost getRenderHost(String hostname) {
        return getRenderHostBuilder(hostname).build();
    }

    private static RenderHost getNewRenderHost(String tags) {
        return RenderHost.newBuilder().setName(NEW_HOSTNAME).setBootTime(1192369572)
                // The minimum amount of free space in the temporary directory to book a host.
                .setFreeMcp(CueUtil.GB).setFreeMem(CueUtil.GB8).setFreeSwap(CueUtil.GB2).setLoad(0)
                .setTotalMcp(195430).setTotalMem(CueUtil.GB8).setTotalSwap(CueUtil.GB2)
                .setNimbyEnabled(false).setNumProcs(2).setCoresPerProc(100).addTags(tags)
                .setState(HardwareState.UP).setFacility("spi").putAttributes("SP_OS", "Linux")
                .putAttributes("freeGpu", String.format("%d", CueUtil.MB512))
                .putAttributes("totalGpu", String.format("%d", CueUtil.MB512)).build();
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testHandleHostReport() throws InterruptedException {
        CoreDetail cores = getCoreDetail(200, 200, 0, 0);
        HostReport report1 =
                HostReport.newBuilder().setHost(getRenderHost(hostname)).setCoreInfo(cores).build();
        HostReport report2 = HostReport.newBuilder().setHost(getRenderHost(hostname2))
                .setCoreInfo(cores).build();
        HostReport report1_2 = HostReport.newBuilder().setHost(getRenderHost(hostname))
                .setCoreInfo(getCoreDetail(200, 200, 100, 0)).build();

        hostReportHandler.handleHostReport(report1, false);
        DispatchHost host = getHost(hostname);
        assertEquals(LockState.OPEN, host.lockState);
        assertEquals(HardwareState.UP, host.hardwareState);
        hostReportHandler.handleHostReport(report1_2, false);
        host = getHost(hostname);
        assertEquals(HardwareState.UP, host.hardwareState);

        // Test Queue thread handling
        ThreadPoolExecutor queue = hostReportHandler.getReportQueue();
        // Make sure jobs flow normally without any nullpointer exception
        // Expecting results from a ThreadPool based class on JUnit is tricky
        // A future test will be developed in the future to better address the behavior
        // of
        // this feature
        hostReportHandler.queueHostReport(report1); // HOSTNAME
        hostReportHandler.queueHostReport(report2); // HOSTNAME2
        hostReportHandler.queueHostReport(report1); // HOSTNAME
        hostReportHandler.queueHostReport(report1); // HOSTNAME
        hostReportHandler.queueHostReport(report1_2); // HOSTNAME
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testHandleHostReportWithNewAllocation() {
        FacilityInterface facility =
                adminManager.getFacility("AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA0");
        assertEquals(facility.getName(), "spi");

        AllocationEntity detail = new AllocationEntity();
        detail.name = "test";
        detail.tag = "test";
        adminManager.createAllocation(facility, detail);
        detail = adminManager.findAllocationDetail("spi", "test");

        boolean isBoot = true;
        CoreDetail cores = getCoreDetail(200, 200, 0, 0);
        HostReport report = HostReport.newBuilder().setHost(getNewRenderHost("test"))
                .setCoreInfo(cores).build();

        hostReportHandler.handleHostReport(report, isBoot);
        DispatchHost host = hostManager.findDispatchHost(NEW_HOSTNAME);
        assertEquals(host.getAllocationId(), detail.id);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testHandleHostReportWithExistentAllocation() {
        AllocationEntity alloc =
                adminManager.getAllocationDetail("00000000-0000-0000-0000-000000000006");
        assertEquals(alloc.getName(), "spi.general");

        boolean isBoot = true;
        CoreDetail cores = getCoreDetail(200, 200, 0, 0);
        HostReport report = HostReport.newBuilder().setHost(getNewRenderHost("general"))
                .setCoreInfo(cores).build();

        hostReportHandler.handleHostReport(report, isBoot);
        DispatchHost host = hostManager.findDispatchHost(NEW_HOSTNAME);
        assertEquals(host.getAllocationId(), alloc.id);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testHandleHostReportWithNonExistentTags() {
        AllocationEntity alloc =
                adminManager.getAllocationDetail("00000000-0000-0000-0000-000000000002");
        assertEquals(alloc.getName(), "lax.unassigned");

        boolean isBoot = true;
        CoreDetail cores = getCoreDetail(200, 200, 0, 0);
        HostReport report = HostReport.newBuilder().setHost(getNewRenderHost("nonexistent"))
                .setCoreInfo(cores).build();

        hostReportHandler.handleHostReport(report, isBoot);
        DispatchHost host = hostManager.findDispatchHost(NEW_HOSTNAME);
        assertEquals(host.getAllocationId(), alloc.id);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testHandleHostReportWithFullTemporaryDirectories() {
        // Create CoreDetail
        CoreDetail cores = getCoreDetail(200, 200, 0, 0);

        /*
         * Test 1: Precondition: - HardwareState=UP Action: - Receives a HostReport with less
         * freeTempDir than the threshold (opencue.properties:
         * min_available_temp_storage_percentage) Postcondition: - Host hardwareState changes to
         * REPAIR - A comment is created with subject=SUBJECT_COMMENT_FULL_TEMP_DIR and
         * user=CUEBOT_COMMENT_USER
         */
        // Create HostReport with totalMcp=4GB and freeMcp=128MB
        HostReport report1 = HostReport.newBuilder()
                .setHost(getRenderHostBuilder(hostname).setFreeMcp(CueUtil.MB128).build())
                .setCoreInfo(cores).build();
        // Call handleHostReport() => Create the comment with
        // subject=SUBJECT_COMMENT_FULL_TEMP_DIR and change the
        // host's hardwareState to REPAIR
        hostReportHandler.handleHostReport(report1, false);
        // Get host
        DispatchHost host = getHost(hostname);
        // Get list of comments by host, user, and subject
        List<CommentDetail> comments = commentManager.getCommentsByHostUserAndSubject(host,
                CUEBOT_COMMENT_USER, SUBJECT_COMMENT_FULL_TEMP_DIR);
        // Check if there is 1 comment
        assertEquals(comments.size(), 1);
        // Get host comment
        CommentDetail comment = comments.get(0);
        // Check if the comment has the user = CUEBOT_COMMENT_USER
        assertEquals(comment.user, CUEBOT_COMMENT_USER);
        // Check if the comment has the subject = SUBJECT_COMMENT_FULL_TEMP_DIR
        assertEquals(comment.subject, SUBJECT_COMMENT_FULL_TEMP_DIR);
        // Check host lock state
        assertEquals(LockState.OPEN, host.lockState);
        // Check if host hardware state is REPAIR
        assertEquals(HardwareState.REPAIR, host.hardwareState);
        // Test Queue thread handling
        ThreadPoolExecutor queue = hostReportHandler.getReportQueue();
        // Make sure jobs flow normally without any nullpointer exception
        hostReportHandler.queueHostReport(report1); // HOSTNAME
        hostReportHandler.queueHostReport(report1); // HOSTNAME

        /*
         * Test 2: Precondition: - HardwareState=REPAIR - There is a comment for the host with
         * subject=SUBJECT_COMMENT_FULL_TEMP_DIR and user=CUEBOT_COMMENT_USER Action: Receives a
         * HostReport with more freeTempDir than the threshold (opencue.properties:
         * min_available_temp_storage_percentage) Postcondition: - Host hardwareState changes to UP
         * - Comment with subject=SUBJECT_COMMENT_FULL_TEMP_DIR and user=CUEBOT_COMMENT_USER gets
         * deleted
         */
        // Set the host freeTempDir to the minimum size required = 1GB (1048576 KB)
        HostReport report2 = HostReport.newBuilder()
                .setHost(getRenderHostBuilder(hostname).setFreeMcp(CueUtil.GB).build())
                .setCoreInfo(cores).build();
        // Call handleHostReport() => Delete the comment with
        // subject=SUBJECT_COMMENT_FULL_TEMP_DIR and change the
        // host's hardwareState to UP
        hostReportHandler.handleHostReport(report2, false);
        // Get host
        host = getHost(hostname);
        // Get list of comments by host, user, and subject
        comments = commentManager.getCommentsByHostUserAndSubject(host, CUEBOT_COMMENT_USER,
                SUBJECT_COMMENT_FULL_TEMP_DIR);
        // Check if there is no comment associated with the host
        assertEquals(comments.size(), 0);
        // Check host lock state
        assertEquals(LockState.OPEN, host.lockState);
        // Check if host hardware state is UP
        assertEquals(HardwareState.UP, host.hardwareState);
        // Test Queue thread handling
        queue = hostReportHandler.getReportQueue();
        // Make sure jobs flow normally without any nullpointer exception
        hostReportHandler.queueHostReport(report1); // HOSTNAME
        hostReportHandler.queueHostReport(report1); // HOSTNAME
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testHandleHostReportWithHardwareStateRepairNotRelatedToFullTempDir() {
        // Create CoreDetail
        CoreDetail cores = getCoreDetail(200, 200, 0, 0);

        /*
         * Test if host.hardwareState == HardwareState.REPAIR (Not related to freeMcp <
         * dispatcher.min_bookable_free_mcp_kb (opencue.properties))
         *
         * - There is no comment with subject=SUBJECT_COMMENT_FULL_MCP_DIR and
         * user=CUEBOT_COMMENT_USER associated with the host The host.hardwareState continue as
         * HardwareState.REPAIR
         */
        // Create HostReport
        HostReport report = HostReport.newBuilder()
                .setHost(getRenderHostBuilder(hostname).setFreeMcp(CueUtil.GB).build())
                .setCoreInfo(cores).build();
        // Get host
        DispatchHost host = getHost(hostname);
        // Host's HardwareState set to REPAIR
        hostManager.setHostState(host, HardwareState.REPAIR);
        host.hardwareState = HardwareState.REPAIR;
        // Get list of comments by host, user, and subject
        List<CommentDetail> hostComments = commentManager.getCommentsByHostUserAndSubject(host,
                CUEBOT_COMMENT_USER, SUBJECT_COMMENT_FULL_TEMP_DIR);
        // Check if there is no comment
        assertEquals(hostComments.size(), 0);
        // There is no comment to delete
        boolean commentsDeleted = commentManager.deleteCommentByHostUserAndSubject(host,
                CUEBOT_COMMENT_USER, SUBJECT_COMMENT_FULL_TEMP_DIR);
        assertFalse(commentsDeleted);
        // Call handleHostReport()
        hostReportHandler.handleHostReport(report, false);
        // Check host lock state
        assertEquals(LockState.OPEN, host.lockState);
        // Check if host hardware state is REPAIR
        assertEquals(HardwareState.REPAIR, host.hardwareState);
        // Test Queue thread handling
        ThreadPoolExecutor queueThread = hostReportHandler.getReportQueue();
        // Make sure jobs flow normally without any nullpointer exception
        hostReportHandler.queueHostReport(report); // HOSTNAME
        hostReportHandler.queueHostReport(report); // HOSTNAME
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testMemoryAndLlu() {
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_simple.xml"));

        DispatchHost host = getHost(hostname);
        List<VirtualProc> procs = dispatcher.dispatchHost(host);
        assertEquals(1, procs.size());
        VirtualProc proc = procs.get(0);

        CoreDetail cores = getCoreDetail(200, 200, 0, 0);
        long now = System.currentTimeMillis();

        RunningFrameInfo info = RunningFrameInfo.newBuilder().setJobId(proc.getJobId())
                .setLayerId(proc.getLayerId()).setFrameId(proc.getFrameId())
                .setResourceId(proc.getProcId()).setLluTime(now / 1000).setMaxRss(420000).build();
        HostReport report = HostReport.newBuilder().setHost(getRenderHost(hostname))
                .setCoreInfo(cores).addFrames(info).build();

        hostReportHandler.handleHostReport(report, false);

        FrameDetail frame = jobManager.getFrameDetail(proc.getFrameId());
        assertEquals(frame.dateLLU, new Timestamp(now / 1000 * 1000));
        assertEquals(420000, frame.maxRss);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testMemoryAggressionRss() {
        jobLauncher.testMode = true;
        dispatcher.setTestMode(true);

        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_simple.xml"));

        DispatchHost host = getHost(hostname);
        List<VirtualProc> procs = dispatcher.dispatchHost(host);
        assertEquals(1, procs.size());
        VirtualProc proc = procs.get(0);

        // 1.6 = 1 + dispatcher.oom_frame_overboard_allowed_threshold
        long memoryOverboard = (long) Math.ceil((double) proc.memoryReserved * 1.6);

        // Test rss overboard
        RunningFrameInfo info = RunningFrameInfo.newBuilder().setJobId(proc.getJobId())
                .setLayerId(proc.getLayerId()).setFrameId(proc.getFrameId())
                .setResourceId(proc.getProcId()).setRss(memoryOverboard).setMaxRss(memoryOverboard)
                .build();
        HostReport report = HostReport.newBuilder().setHost(getRenderHost(hostname))
                .setCoreInfo(getCoreDetail(200, 200, 0, 0)).addFrames(info).build();

        long killCount = DispatchSupport.killedOffenderProcs.get();
        hostReportHandler.handleHostReport(report, false);
        assertEquals(killCount + 1, DispatchSupport.killedOffenderProcs.get());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testMemoryAggressionMaxRss() {
        jobLauncher.testMode = true;
        dispatcher.setTestMode(true);
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_simple.xml"));

        DispatchHost host = getHost(hostname);
        List<VirtualProc> procs = dispatcher.dispatchHost(host);
        assertEquals(1, procs.size());
        VirtualProc proc = procs.get(0);

        // 0.6 = dispatcher.oom_frame_overboard_allowed_threshold
        long memoryOverboard = (long) Math.ceil((double) proc.memoryReserved * (1.0 + (2 * 0.6)));

        // Test rss>90% and maxRss overboard
        RunningFrameInfo info = RunningFrameInfo.newBuilder().setJobId(proc.getJobId())
                .setLayerId(proc.getLayerId()).setFrameId(proc.getFrameId())
                .setResourceId(proc.getProcId())
                .setRss((long) Math.ceil(0.95 * proc.memoryReserved)).setMaxRss(memoryOverboard)
                .build();
        HostReport report = HostReport.newBuilder().setHost(getRenderHost(hostname))
                .setCoreInfo(getCoreDetail(200, 200, 0, 0)).addFrames(info).build();

        long killCount = DispatchSupport.killedOffenderProcs.get();
        hostReportHandler.handleHostReport(report, false);
        assertEquals(killCount + 1, DispatchSupport.killedOffenderProcs.get());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testMemoryAggressionMemoryWarning() {
        jobLauncher.testMode = true;
        dispatcher.setTestMode(true);
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_multiple_frames.xml"));

        DispatchHost host = getHost(hostname);
        List<VirtualProc> procs = dispatcher.dispatchHost(host);
        assertEquals(3, procs.size());
        VirtualProc proc1 = procs.get(0);
        VirtualProc proc2 = procs.get(1);
        VirtualProc proc3 = procs.get(2);

        // Ok
        RunningFrameInfo info1 = RunningFrameInfo.newBuilder().setJobId(proc1.getJobId())
                .setLayerId(proc1.getLayerId()).setFrameId(proc1.getFrameId())
                .setResourceId(proc1.getProcId()).setUsedSwapMemory(CueUtil.MB512 - CueUtil.MB128)
                .setVsize(CueUtil.GB2).setRss(CueUtil.GB2).setMaxRss(CueUtil.GB2).build();

        // Overboard Rss
        RunningFrameInfo info2 = RunningFrameInfo.newBuilder().setJobId(proc2.getJobId())
                .setLayerId(proc2.getLayerId()).setFrameId(proc2.getFrameId())
                .setResourceId(proc2.getProcId()).setUsedSwapMemory(CueUtil.MB512)
                .setVsize(CueUtil.GB4).setRss(CueUtil.GB4).setMaxRss(CueUtil.GB4).build();

        // Overboard Rss
        long memoryUsedProc3 = CueUtil.GB8;
        RunningFrameInfo info3 = RunningFrameInfo.newBuilder().setJobId(proc3.getJobId())
                .setLayerId(proc3.getLayerId()).setFrameId(proc3.getFrameId())
                .setResourceId(proc3.getProcId()).setUsedSwapMemory(CueUtil.MB512 * 2)
                .setVsize(memoryUsedProc3).setRss(memoryUsedProc3).setMaxRss(memoryUsedProc3)
                .build();

        RenderHost hostAfterUpdate = getRenderHostBuilder(hostname).setFreeMem(0)
                .setFreeSwap(CueUtil.GB2 - info1.getUsedSwapMemory() - info2.getUsedSwapMemory()
                        - info3.getUsedSwapMemory())
                .build();

        HostReport report = HostReport.newBuilder().setHost(hostAfterUpdate)
                .setCoreInfo(getCoreDetail(200, 200, 0, 0))
                .addAllFrames(Arrays.asList(info1, info2, info3)).build();

        // Get layer state before report gets sent
        LayerDetail layerBeforeIncrease = jobManager.getLayerDetail(proc3.getLayerId());

        // In this case, killing 2 frames should be enough to ge the machine to a safe
        // state. Total Swap: 2GB, usage before kill: 1944MB, usage after kill: 348
        // (less than 20%)
        long killCount = DispatchSupport.killedOffenderProcs.get();
        hostReportHandler.handleHostReport(report, false);
        assertEquals(killCount + 2, DispatchSupport.killedOffenderProcs.get());

        // Confirm the frame will be set to retry after it's completion has been
        // processed

        RunningFrameInfo runningFrame = RunningFrameInfo.newBuilder().setFrameId(proc3.getFrameId())
                .setFrameName("frame_name").setLayerId(proc3.getLayerId()).setRss(memoryUsedProc3)
                .setMaxRss(memoryUsedProc3).setResourceId(proc3.id).build();
        FrameCompleteReport completeReport =
                FrameCompleteReport.newBuilder().setHost(hostAfterUpdate).setFrame(runningFrame)
                        .setExitSignal(9).setRunTime(1).setExitStatus(1).build();

        frameCompleteHandler.handleFrameCompleteReport(completeReport);
        FrameDetail killedFrame = jobManager.getFrameDetail(proc3.getFrameId());
        LayerDetail layer = jobManager.getLayerDetail(proc3.getLayerId());
        assertEquals(FrameState.WAITING, killedFrame.state);
        // Memory increases are processed in two different places.
        // First: proc.reserved + 2GB
        // Second: the maximum reported proc.maxRss
        // The higher valuer beween First and Second wins.
        // In this case, proc.maxRss
        assertEquals(
                Math.max(memoryUsedProc3, layerBeforeIncrease.getMinimumMemory() + CueUtil.GB2),
                layer.getMinimumMemory());
    }
}
