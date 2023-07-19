
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



package com.imageworks.spcue.test.dispatcher;

import java.io.File;
import java.sql.Timestamp;
import java.util.List;
import java.util.concurrent.ThreadPoolExecutor;
import javax.annotation.Resource;

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
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.CommentManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.test.TransactionalTest;
import com.imageworks.spcue.util.CueUtil;
import com.imageworks.spcue.VirtualProc;

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
    private static final String SUBJECT_COMMENT_FULL_MCP_DIR = "Host set to REPAIR for not having enough storage " +
            "space on /mcp";
    private static final String CUEBOT_COMMENT_USER = "cuebot";

    @Before
    public void setTestMode() {
        dispatcher.setTestMode(true);
    }

    @Before
    public void createHost() {
        hostname = UUID.randomUUID().toString().substring(0, 8);
        hostname2 = UUID.randomUUID().toString().substring(0, 8);
        hostManager.createHost(getRenderHost(hostname, HardwareState.UP),
                adminManager.findAllocationDetail("spi","general"));
        hostManager.createHost(getRenderHost(hostname2, HardwareState.UP),
                adminManager.findAllocationDetail("spi","general"));
    }

    private static CoreDetail getCoreDetail(int total, int idle, int booked, int locked) {
        return CoreDetail.newBuilder()
                .setTotalCores(total)
                .setIdleCores(idle)
                .setBookedCores(booked)
                .setLockedCores(locked)
                .build();
    }

    private DispatchHost getHost(String hostname) {
        return hostManager.findDispatchHost(hostname);
    }

    private static RenderHost getRenderHost(String hostname, HardwareState state) {
        return RenderHost.newBuilder()
                .setName(hostname)
                .setBootTime(1192369572)
                // The minimum amount of free space in the /mcp directory to book a host.
                .setFreeMcp(1048576)
                .setFreeMem((int) CueUtil.GB8)
                .setFreeSwap(20760)
                .setLoad(0)
                .setTotalMcp(195430)
                .setTotalMem(CueUtil.GB8)
                .setTotalSwap(CueUtil.GB2)
                .setNimbyEnabled(false)
                .setNumProcs(2)
                .setCoresPerProc(100)
                .addTags("test")
                .setState(state)
                .setFacility("spi")
                .putAttributes("SP_OS", "Linux")
                .setFreeGpuMem((int) CueUtil.MB512)
                .setTotalGpuMem((int) CueUtil.MB512)
                .build();
    }

    private static RenderHost getRenderHost(String hostname, HardwareState state, Long freeMcp) {
        return RenderHost.newBuilder()
                .setName(hostname)
                .setBootTime(1192369572)
                // The minimum amount of free space in the /mcp directory to book a host.
                .setFreeMcp(freeMcp)
                .setFreeMem((int) CueUtil.GB8)
                .setFreeSwap(20760)
                .setLoad(0)
                .setTotalMcp(195430)
                .setTotalMem(CueUtil.GB8)
                .setTotalSwap(CueUtil.GB2)
                .setNimbyEnabled(false)
                .setNumProcs(2)
                .setCoresPerProc(100)
                .addTags("test")
                .setState(state)
                .setFacility("spi")
                .putAttributes("SP_OS", "Linux")
                .setFreeGpuMem((int) CueUtil.MB512)
                .setTotalGpuMem((int) CueUtil.MB512)
                .build();
    }

    private static RenderHost getNewRenderHost(String tags) {
        return RenderHost.newBuilder()
                .setName(NEW_HOSTNAME)
                .setBootTime(1192369572)
                // The minimum amount of free space in the /mcp directory to book a host.
                .setFreeMcp(1048576)
                .setFreeMem(53500)
                .setFreeSwap(20760)
                .setLoad(0)
                .setTotalMcp(195430)
                .setTotalMem(8173264)
                .setTotalSwap(20960)
                .setNimbyEnabled(false)
                .setNumProcs(2)
                .setCoresPerProc(100)
                .addTags(tags)
                .setState(HardwareState.UP)
                .setFacility("spi")
                .putAttributes("SP_OS", "Linux")
                .putAttributes("freeGpu", String.format("%d", CueUtil.MB512))
                .putAttributes("totalGpu", String.format("%d", CueUtil.MB512))
                .build();
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testHandleHostReport() throws InterruptedException {
        CoreDetail cores = getCoreDetail(200, 200, 0, 0);
        HostReport report1 = HostReport.newBuilder()
                .setHost(getRenderHost(hostname, HardwareState.UP))
                .setCoreInfo(cores)
                .build();
        HostReport report2 = HostReport.newBuilder()
                .setHost(getRenderHost(hostname2, HardwareState.UP))
                .setCoreInfo(cores)
                .build();
        HostReport report1_2 = HostReport.newBuilder()
                .setHost(getRenderHost(hostname, HardwareState.UP))
                .setCoreInfo(getCoreDetail(200, 200, 100, 0))
                .build();

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
        // A future test will be developed in the future to better address the behavior of
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
        FacilityInterface facility = adminManager.getFacility(
                "AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA0");
        assertEquals(facility.getName(), "spi");

        AllocationEntity detail = new AllocationEntity();
        detail.name = "test";
        detail.tag = "test";
        adminManager.createAllocation(facility, detail);
        detail = adminManager.findAllocationDetail("spi", "test");

        boolean isBoot = true;
        CoreDetail cores = getCoreDetail(200, 200, 0, 0);
        HostReport report = HostReport.newBuilder()
                .setHost(getNewRenderHost("test"))
                .setCoreInfo(cores)
                .build();

        hostReportHandler.handleHostReport(report, isBoot);
        DispatchHost host = hostManager.findDispatchHost(NEW_HOSTNAME);
        assertEquals(host.getAllocationId(), detail.id);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testHandleHostReportWithExistentAllocation() {
        AllocationEntity alloc = adminManager.getAllocationDetail(
                "00000000-0000-0000-0000-000000000006");
        assertEquals(alloc.getName(), "spi.general");

        boolean isBoot = true;
        CoreDetail cores = getCoreDetail(200, 200, 0, 0);
        HostReport report = HostReport.newBuilder()
                .setHost(getNewRenderHost("general"))
                .setCoreInfo(cores)
                .build();

        hostReportHandler.handleHostReport(report, isBoot);
        DispatchHost host = hostManager.findDispatchHost(NEW_HOSTNAME);
        assertEquals(host.getAllocationId(), alloc.id);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testHandleHostReportWithNonExistentTags() {
        AllocationEntity alloc = adminManager.getAllocationDetail(
                "00000000-0000-0000-0000-000000000002");
        assertEquals(alloc.getName(), "lax.unassigned");

        boolean isBoot = true;
        CoreDetail cores = getCoreDetail(200, 200, 0, 0);
        HostReport report = HostReport.newBuilder()
                .setHost(getNewRenderHost("nonexistent"))
                .setCoreInfo(cores)
                .build();

        hostReportHandler.handleHostReport(report, isBoot);
        DispatchHost host = hostManager.findDispatchHost(NEW_HOSTNAME);
        assertEquals(host.getAllocationId(), alloc.id);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testHandleHostReportWithFullMCPDirectories() {
        // Create CoreDetail
        CoreDetail cores = getCoreDetail(200, 200, 0, 0);

        /*
        * Test 1:
        *   Precondition:
        *     - HardwareState=UP
        *   Action:
        *     - Receives a HostReport with freeMCP < dispatcher.min_bookable_free_mcp_kb (opencue.properties)
        *   Postcondition:
        *     - Host hardwareState changes to REPAIR
        *     - A comment is created with subject=SUBJECT_COMMENT_FULL_MCP_DIR and user=CUEBOT_COMMENT_USER
        * */
        // Create HostReport
        HostReport report1 = HostReport.newBuilder()
                .setHost(getRenderHost(hostname, HardwareState.UP, 1024L))
                .setCoreInfo(cores)
                .build();
        // Call handleHostReport() => Create the comment with subject=SUBJECT_COMMENT_FULL_MCP_DIR and change the host's
        // hardwareState to REPAIR
        hostReportHandler.handleHostReport(report1, false);
        // Get host
        DispatchHost host = getHost(hostname);
        // Get list of comments by host, user, and subject
        List<CommentDetail> comments = commentManager.getCommentsByHostUserAndSubject(host, CUEBOT_COMMENT_USER,
                SUBJECT_COMMENT_FULL_MCP_DIR);
        // Check if there is 1 comment
        assertEquals(comments.size(), 1);
        // Get host comment
        CommentDetail comment = comments.get(0);
        // Check if the comment has the user = CUEBOT_COMMENT_USER
        assertEquals(comment.user, CUEBOT_COMMENT_USER);
        // Check if the comment has the subject = SUBJECT_COMMENT_FULL_MCP_DIR
        assertEquals(comment.subject, SUBJECT_COMMENT_FULL_MCP_DIR);
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
         * Test 2:
         *   Precondition: 
         *     - HardwareState=REPAIR
         *     - There is a comment for the host with subject=SUBJECT_COMMENT_FULL_MCP_DIR and user=CUEBOT_COMMENT_USER
         *   Action:
         *     - Receives a HostReport with freeMCP >= dispatcher.min_bookable_free_mcp_kb (opencue.properties)
         *   Postcondition:
         *     - Host hardwareState changes to UP
         *     - Comment with subject=SUBJECT_COMMENT_FULL_MCP_DIR and user=CUEBOT_COMMENT_USER gets deleted
         * */
        // Set the host freeMcp to the minimum size required = 1GB (1048576 KB)
        HostReport report2 = HostReport.newBuilder()
                .setHost(getRenderHost(hostname, HardwareState.UP, 1048576L))
                .setCoreInfo(cores)
                .build();
        // Call handleHostReport() => Delete the comment with subject=SUBJECT_COMMENT_FULL_MCP_DIR and change the host's
        // hardwareState to UP
        hostReportHandler.handleHostReport(report2, false);
        // Get host
        host = getHost(hostname);
        // Get list of comments by host, user, and subject
        comments = commentManager.getCommentsByHostUserAndSubject(host, CUEBOT_COMMENT_USER,
                SUBJECT_COMMENT_FULL_MCP_DIR);
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
    public void testHandleHostReportWithHardwareStateRepairNotRelatedToFullMCPdirectories() {
        // Create CoreDetail
        CoreDetail cores = getCoreDetail(200, 200, 0, 0);

        /*
         * Test if host.hardwareState == HardwareState.REPAIR
         * (Not related to freeMcp < dispatcher.min_bookable_free_mcp_kb (opencue.properties))
         *
         * - There is no comment with subject=SUBJECT_COMMENT_FULL_MCP_DIR and user=CUEBOT_COMMENT_USER associated with
         * the host
         * The host.hardwareState continue as HardwareState.REPAIR
         * */
        // Create HostReport
        HostReport report = HostReport.newBuilder()
                .setHost(getRenderHost(hostname, HardwareState.UP, 1048576L))
                .setCoreInfo(cores)
                .build();
        // Get host
        DispatchHost host = getHost(hostname);
        // Host's HardwareState set to REPAIR
        hostManager.setHostState(host, HardwareState.REPAIR);
        host.hardwareState = HardwareState.REPAIR;
        // Get list of comments by host, user, and subject
        List<CommentDetail> hostComments = commentManager.getCommentsByHostUserAndSubject(host, CUEBOT_COMMENT_USER,
                SUBJECT_COMMENT_FULL_MCP_DIR);
        // Check if there is no comment
        assertEquals(hostComments.size(), 0);
        // There is no comment to delete
        boolean commentsDeleted = commentManager.deleteCommentByHostUserAndSubject(host,
                CUEBOT_COMMENT_USER, SUBJECT_COMMENT_FULL_MCP_DIR);
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

        RunningFrameInfo info = RunningFrameInfo.newBuilder()
                .setJobId(proc.getJobId())
                .setLayerId(proc.getLayerId())
                .setFrameId(proc.getFrameId())
                .setResourceId(proc.getProcId())
                .setLluTime(now / 1000)
                .setMaxRss(420000)
                .build();
        HostReport report = HostReport.newBuilder()
                .setHost(getRenderHost(hostname, HardwareState.UP))
                .setCoreInfo(cores)
                .addFrames(info)
                .build();

        hostReportHandler.handleHostReport(report, false);

        FrameDetail frame = jobManager.getFrameDetail(proc.getFrameId());
        assertEquals(frame.dateLLU, new Timestamp(now / 1000 * 1000));
        assertEquals(420000, frame.maxRss);
    }
}

