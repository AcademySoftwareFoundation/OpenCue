
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
import java.util.List;
import javax.annotation.Resource;
import java.util.LinkedHashSet;

import org.junit.Before;
import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.DispatchJob;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.ServiceOverrideEntity;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dao.ProcDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.dispatcher.BookingQueue;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.DispatchQueue;
import com.imageworks.spcue.dispatcher.DispatchSupport;
import com.imageworks.spcue.dispatcher.FrameCompleteHandler;
import com.imageworks.spcue.dispatcher.RedirectManager;
import com.imageworks.spcue.dispatcher.RqdRetryReportException;
import com.imageworks.spcue.dispatcher.commands.DispatchNextFrame;
import com.imageworks.spcue.dispatcher.commands.KeyRunnable;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.host.LockState;
import com.imageworks.spcue.grpc.job.FrameExitStatus;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.grpc.report.FrameCompleteReport;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.grpc.report.RunningFrameInfo;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JmsMover;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.ServiceManager;
import com.imageworks.spcue.test.TransactionalTest;
import com.imageworks.spcue.util.CueUtil;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.mockito.AdditionalAnswers.delegatesTo;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.spy;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;

import org.springframework.transaction.CannotCreateTransactionException;

import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.service.JobManagerSupport;

@ContextConfiguration
public class FrameCompleteHandlerTests extends TransactionalTest {

    @Resource
    AdminManager adminManager;

    @Resource
    FrameCompleteHandler frameCompleteHandler;

    @Resource
    HostManager hostManager;

    @Resource
    JobLauncher jobLauncher;

    @Resource
    JobManager jobManager;

    @Resource
    FrameDao frameDao;

    @Resource
    ProcDao procDao;

    @Resource
    LayerDao layerDao;

    @Resource
    Dispatcher dispatcher;

    @Resource
    DispatchSupport dispatchSupport;

    @Resource
    ServiceManager serviceManager;

    private static final String HOSTNAME = "beta";
    private static final String HOSTNAME2 = "zeta";

    @Before
    public void setTestMode() {

        dispatcher.setTestMode(true);
    }

    @Before
    public void launchJob() {
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_gpus_test.xml"));
    }

    @Before
    public void createHost() {
        RenderHost host = RenderHost.newBuilder().setName(HOSTNAME).setBootTime(1192369572)
                // The minimum amount of free space in the temporary directory to book a host.
                .setFreeMcp(CueUtil.GB).setFreeMem((int) CueUtil.GB8).setFreeSwap(20760).setLoad(0)
                .setTotalMcp(CueUtil.GB4).setTotalMem(CueUtil.GB8).setTotalSwap(CueUtil.GB2)
                .setNimbyEnabled(false).setNumProcs(40).setCoresPerProc(100)
                .setState(HardwareState.UP).setFacility("spi").putAttributes("SP_OS", "Linux")
                .setNumGpus(8).setFreeGpuMem(CueUtil.GB16 * 8).setTotalGpuMem(CueUtil.GB16 * 8)
                .build();

        hostManager.createHost(host, adminManager.findAllocationDetail("spi", "general"));

        RenderHost host2 = RenderHost.newBuilder().setName(HOSTNAME2).setBootTime(1192369572)
                // The minimum amount of free space in the temporary directory to book a host.
                .setFreeMcp(CueUtil.GB).setFreeMem((int) CueUtil.GB4).setFreeSwap((int) CueUtil.GB4)
                .setLoad(0).setTotalMcp(CueUtil.GB4).setTotalMem((int) CueUtil.GB8)
                .setTotalSwap((int) CueUtil.GB8).setNimbyEnabled(false).setNumProcs(8)
                .setCoresPerProc(100).setState(HardwareState.UP).setFacility("spi")
                .putAttributes("SP_OS", "Linux").build();

        hostManager.createHost(host2, adminManager.findAllocationDetail("spi", "general"));
    }

    public DispatchHost getHost(String hostname) {
        return hostManager.findDispatchHost(hostname);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGpuReport() {
        JobDetail job = jobManager.findJobDetail("pipe-default-testuser_test0");
        LayerDetail layer = layerDao.findLayerDetail(job, "layer0");
        jobManager.setJobPaused(job, false);

        DispatchHost host = getHost(HOSTNAME);
        List<VirtualProc> procs = dispatcher.dispatchHost(host);
        assertEquals(1, procs.size());
        VirtualProc proc = procs.get(0);

        assertEquals(7, host.idleGpus);
        assertEquals(CueUtil.GB16 * 8 - CueUtil.GB, host.idleGpuMemory);

        RunningFrameInfo info = RunningFrameInfo.newBuilder().setJobId(proc.getJobId())
                .setLayerId(proc.getLayerId()).setFrameId(proc.getFrameId())
                .setResourceId(proc.getProcId()).build();
        FrameCompleteReport report =
                FrameCompleteReport.newBuilder().setFrame(info).setExitStatus(0).build();
        frameCompleteHandler.handleFrameCompleteReport(report);

        assertTrue(jobManager.isLayerComplete(layer));
        assertTrue(jobManager.isJobComplete(job));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGpuReportMultiple() {
        JobDetail job0 = jobManager.findJobDetail("pipe-default-testuser_test0");
        LayerDetail layer0_0 = layerDao.findLayerDetail(job0, "layer0");
        jobManager.setJobPaused(job0, false);

        JobDetail job1 = jobManager.findJobDetail("pipe-default-testuser_test1");
        LayerDetail layer1_0 = layerDao.findLayerDetail(job1, "layer0");
        jobManager.setJobPaused(job1, false);

        DispatchHost host = getHost(HOSTNAME);
        List<VirtualProc> procs = dispatcher.dispatchHost(host);
        assertEquals(2, procs.size());

        assertEquals(4, host.idleGpus);
        assertEquals(CueUtil.GB16 * 8 - CueUtil.GB2, host.idleGpuMemory);

        for (VirtualProc proc : procs) {
            RunningFrameInfo info = RunningFrameInfo.newBuilder().setJobId(proc.getJobId())
                    .setLayerId(proc.getLayerId()).setFrameId(proc.getFrameId())
                    .setResourceId(proc.getProcId()).build();
            FrameCompleteReport report =
                    FrameCompleteReport.newBuilder().setFrame(info).setExitStatus(0).build();
            frameCompleteHandler.handleFrameCompleteReport(report);
        }

        assertTrue(jobManager.isLayerComplete(layer0_0));
        assertTrue(jobManager.isJobComplete(job0));
        assertTrue(jobManager.isLayerComplete(layer1_0));
        assertTrue(jobManager.isJobComplete(job1));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGpuReportOver() {
        JobDetail job1 = jobManager.findJobDetail("pipe-default-testuser_test1");
        LayerDetail layer1_0 = layerDao.findLayerDetail(job1, "layer0");
        jobManager.setJobPaused(job1, false);

        JobDetail job2 = jobManager.findJobDetail("pipe-default-testuser_test2");
        LayerDetail layer2_0 = layerDao.findLayerDetail(job2, "layer0");
        jobManager.setJobPaused(job2, false);

        DispatchHost host = getHost(HOSTNAME);
        List<VirtualProc> procs = dispatcher.dispatchHost(host);
        assertEquals(1, procs.size());

        assertTrue(host.idleGpus == 5 || host.idleGpus == 2);
        assertEquals(CueUtil.GB16 * 8 - CueUtil.GB, host.idleGpuMemory);

        for (VirtualProc proc : procs) {
            RunningFrameInfo info = RunningFrameInfo.newBuilder().setJobId(proc.getJobId())
                    .setLayerId(proc.getLayerId()).setFrameId(proc.getFrameId())
                    .setResourceId(proc.getProcId()).build();
            FrameCompleteReport report =
                    FrameCompleteReport.newBuilder().setFrame(info).setExitStatus(0).build();
            frameCompleteHandler.handleFrameCompleteReport(report);
        }

        assertEquals(1, (jobManager.isLayerComplete(layer1_0) ? 1 : 0)
                + (jobManager.isLayerComplete(layer2_0) ? 1 : 0));
        assertEquals(1, (jobManager.isJobComplete(job1) ? 1 : 0)
                + (jobManager.isJobComplete(job2) ? 1 : 0));
    }

    private void executeDepend(FrameState frameState, int exitStatus, int dependCount,
            FrameState dependState) {
        JobDetail job = jobManager.findJobDetail("pipe-default-testuser_test_depend");
        LayerDetail layerFirst = layerDao.findLayerDetail(job, "layer_first");
        LayerDetail layerSecond = layerDao.findLayerDetail(job, "layer_second");
        FrameDetail frameFirst = frameDao.findFrameDetail(job, "0000-layer_first");
        FrameDetail frameSecond = frameDao.findFrameDetail(job, "0000-layer_second");

        assertEquals(1, frameSecond.dependCount);
        assertEquals(FrameState.DEPEND, frameSecond.state);

        jobManager.setJobPaused(job, false);

        DispatchHost host = getHost(HOSTNAME);
        List<VirtualProc> procs = dispatcher.dispatchHost(host);
        assertEquals(1, procs.size());
        VirtualProc proc = procs.get(0);
        assertEquals(job.getId(), proc.getJobId());
        assertEquals(layerFirst.getId(), proc.getLayerId());
        assertEquals(frameFirst.getId(), proc.getFrameId());

        RunningFrameInfo info = RunningFrameInfo.newBuilder().setJobId(proc.getJobId())
                .setLayerId(proc.getLayerId()).setFrameId(proc.getFrameId())
                .setResourceId(proc.getProcId()).build();
        FrameCompleteReport report =
                FrameCompleteReport.newBuilder().setFrame(info).setExitStatus(exitStatus).build();

        DispatchJob dispatchJob = jobManager.getDispatchJob(proc.getJobId());
        DispatchFrame dispatchFrame = jobManager.getDispatchFrame(report.getFrame().getFrameId());
        FrameDetail frameDetail = jobManager.getFrameDetail(report.getFrame().getFrameId());
        dispatchSupport.stopFrame(dispatchFrame, frameState, report.getExitStatus(),
                report.getFrame().getMaxRss());
        frameCompleteHandler.handlePostFrameCompleteOperations(proc, report, dispatchJob,
                dispatchFrame, frameState, frameDetail);

        assertTrue(jobManager.isLayerComplete(layerFirst));
        assertFalse(jobManager.isLayerComplete(layerSecond));

        frameSecond = frameDao.findFrameDetail(job, "0000-layer_second");
        assertEquals(dependCount, frameSecond.dependCount);
        assertEquals(dependState, frameSecond.state);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDependOnSuccess() {
        assertTrue(frameCompleteHandler.getSatisfyDependOnlyOnFrameSuccess());
        executeDepend(FrameState.SUCCEEDED, 0, 0, FrameState.WAITING);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDependOnFailure() {
        assertTrue(frameCompleteHandler.getSatisfyDependOnlyOnFrameSuccess());
        executeDepend(FrameState.EATEN, -1, 1, FrameState.DEPEND);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDependOnSuccessSatifyOnAny() {
        frameCompleteHandler.setSatisfyDependOnlyOnFrameSuccess(false);
        assertFalse(frameCompleteHandler.getSatisfyDependOnlyOnFrameSuccess());
        executeDepend(FrameState.SUCCEEDED, 0, 0, FrameState.WAITING);
        frameCompleteHandler.setSatisfyDependOnlyOnFrameSuccess(true);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDependOnFailureSatisfyOnAny() {
        frameCompleteHandler.setSatisfyDependOnlyOnFrameSuccess(false);
        assertFalse(frameCompleteHandler.getSatisfyDependOnlyOnFrameSuccess());
        executeDepend(FrameState.EATEN, -1, 0, FrameState.WAITING);
        frameCompleteHandler.setSatisfyDependOnlyOnFrameSuccess(true);
    }

    private void executeMinMemIncrease(int expected, boolean override, int exitStatus) {
        if (override) {
            ServiceOverrideEntity soe = new ServiceOverrideEntity();
            soe.showId = "00000000-0000-0000-0000-000000000000";
            soe.name = "apitest";
            soe.threadable = false;
            soe.minCores = 10;
            soe.minMemory = (int) CueUtil.GB2;
            soe.tags = new LinkedHashSet<>();
            soe.tags.add("general");
            soe.minMemoryIncrease = (int) CueUtil.GB8;

            serviceManager.createService(soe);
        }

        String jobName = "pipe-default-testuser_min_mem_test";
        JobDetail job = jobManager.findJobDetail(jobName);
        LayerDetail layer = layerDao.findLayerDetail(job, "test_layer");
        FrameDetail frame = frameDao.findFrameDetail(job, "0000-test_layer");
        jobManager.setJobPaused(job, false);

        DispatchHost host = getHost(HOSTNAME2);
        List<VirtualProc> procs = dispatcher.dispatchHost(host);
        assertEquals(1, procs.size());
        VirtualProc proc = procs.get(0);
        assertEquals(job.getId(), proc.getJobId());
        assertEquals(layer.getId(), proc.getLayerId());
        assertEquals(frame.getId(), proc.getFrameId());

        RunningFrameInfo info = RunningFrameInfo.newBuilder().setJobId(proc.getJobId())
                .setLayerId(proc.getLayerId()).setFrameId(proc.getFrameId())
                .setResourceId(proc.getProcId()).build();
        FrameCompleteReport report =
                FrameCompleteReport.newBuilder().setFrame(info).setExitStatus(exitStatus).build();

        DispatchJob dispatchJob = jobManager.getDispatchJob(proc.getJobId());
        DispatchFrame dispatchFrame = jobManager.getDispatchFrame(report.getFrame().getFrameId());
        FrameDetail frameDetail = jobManager.getFrameDetail(report.getFrame().getFrameId());
        dispatchSupport.stopFrame(dispatchFrame, FrameState.DEAD, report.getExitStatus(),
                report.getFrame().getMaxRss());
        frameCompleteHandler.handlePostFrameCompleteOperations(proc, report, dispatchJob,
                dispatchFrame, FrameState.WAITING, frameDetail);

        assertFalse(jobManager.isLayerComplete(layer));

        JobDetail ujob = jobManager.findJobDetail(jobName);
        LayerDetail ulayer = layerDao.findLayerDetail(ujob, "test_layer");
        assertEquals(expected, ulayer.getMinimumMemory());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testMinMemIncrease() {
        executeMinMemIncrease(6291456, false, Dispatcher.EXIT_STATUS_MEMORY_FAILURE);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testMinMemIncreaseShowOverride() {
        executeMinMemIncrease(10485760, true, Dispatcher.EXIT_STATUS_MEMORY_FAILURE);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testMinMemIncreaseDocker() {
        executeMinMemIncrease(6291456, false, Dispatcher.DOCKER_EXIT_STATUS_MEMORY_FAILURE);
    }

    /**
     * Helper that runs the depend flow with a spy on jobManagerSupport that throws on
     * satisfyWhatDependsOn(FrameInterface) for the first {@code failCount} calls, then delegates to
     * the real implementation.
     */
    private void executeDependWithRetry(int failCount, int expectedDependCount,
            FrameState expectedDependState) {
        JobDetail job = jobManager.findJobDetail("pipe-default-testuser_test_depend");
        LayerDetail layerFirst = layerDao.findLayerDetail(job, "layer_first");
        LayerDetail layerSecond = layerDao.findLayerDetail(job, "layer_second");
        FrameDetail frameFirst = frameDao.findFrameDetail(job, "0000-layer_first");
        FrameDetail frameSecond = frameDao.findFrameDetail(job, "0000-layer_second");

        assertEquals(1, frameSecond.dependCount);
        assertEquals(FrameState.DEPEND, frameSecond.state);

        jobManager.setJobPaused(job, false);

        DispatchHost host = getHost(HOSTNAME);
        List<VirtualProc> procs = dispatcher.dispatchHost(host);
        assertEquals(1, procs.size());
        VirtualProc proc = procs.get(0);
        assertEquals(job.getId(), proc.getJobId());
        assertEquals(layerFirst.getId(), proc.getLayerId());
        assertEquals(frameFirst.getId(), proc.getFrameId());

        RunningFrameInfo info = RunningFrameInfo.newBuilder().setJobId(proc.getJobId())
                .setLayerId(proc.getLayerId()).setFrameId(proc.getFrameId())
                .setResourceId(proc.getProcId()).build();
        FrameCompleteReport report =
                FrameCompleteReport.newBuilder().setFrame(info).setExitStatus(0).build();

        DispatchJob dispatchJob = jobManager.getDispatchJob(proc.getJobId());
        DispatchFrame dispatchFrame = jobManager.getDispatchFrame(report.getFrame().getFrameId());
        FrameDetail frameDetail = jobManager.getFrameDetail(report.getFrame().getFrameId());
        dispatchSupport.stopFrame(dispatchFrame, FrameState.SUCCEEDED, report.getExitStatus(),
                report.getFrame().getMaxRss());

        // Spy on jobManagerSupport to simulate transient failures
        JobManagerSupport originalSupport = frameCompleteHandler.getJobManagerSupport();
        JobManagerSupport spySupport = spy(originalSupport);

        final int[] frameCallCount = {0};
        doAnswer(invocation -> {
            frameCallCount[0]++;
            if (frameCallCount[0] <= failCount) {
                throw new CannotCreateTransactionException(
                        "Simulated pool exhaustion (call " + frameCallCount[0] + ")");
            }
            invocation.callRealMethod();
            return null;
        }).when(spySupport).satisfyWhatDependsOn(any(FrameInterface.class));

        final int[] layerCallCount = {0};
        doAnswer(invocation -> {
            layerCallCount[0]++;
            if (layerCallCount[0] <= failCount) {
                throw new CannotCreateTransactionException(
                        "Simulated pool exhaustion (call " + layerCallCount[0] + ")");
            }
            invocation.callRealMethod();
            return null;
        }).when(spySupport).satisfyWhatDependsOn(any(LayerInterface.class));

        frameCompleteHandler.setJobManagerSupport(spySupport);
        try {
            frameCompleteHandler.handlePostFrameCompleteOperations(proc, report, dispatchJob,
                    dispatchFrame, FrameState.SUCCEEDED, frameDetail);
        } finally {
            frameCompleteHandler.setJobManagerSupport(originalSupport);
        }

        assertTrue(jobManager.isLayerComplete(layerFirst));
        assertFalse(jobManager.isLayerComplete(layerSecond));

        frameSecond = frameDao.findFrameDetail(job, "0000-layer_second");
        assertEquals(expectedDependCount, frameSecond.dependCount);
        assertEquals(expectedDependState, frameSecond.state);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDependRetrySucceedsOnSecondAttempt() {
        // First call fails, second succeeds — depend should be satisfied
        executeDependWithRetry(1, 0, FrameState.WAITING);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDependRetrySucceedsOnThirdAttempt() {
        // First two calls fail, third succeeds — depend should be satisfied
        executeDependWithRetry(2, 0, FrameState.WAITING);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDependRetryExhausted() {
        // All three calls fail — depend remains unsatisfied, frame stays in DEPEND
        executeDependWithRetry(3, 1, FrameState.DEPEND);
    }

    /**
     * Drives a frame completion through the proc-reuse branch (the job still has a WAITING frame,
     * so it stays dispatchable) and asserts whether the scheduler-managed release path fired. When
     * the show is scheduler-managed, the standalone scheduler owns dispatch, so Cuebot must release
     * (unbook) the proc here instead of rebooking it on the same proc — otherwise the proc lingers
     * with pk_frame=NULL holding reserved cores. The release is identified by the unique reason
     * string passed to unbookProc, which makes this independent of the nondeterministic downstream
     * dispatch.
     *
     * <p>
     * isSchedulerManaged is stubbed on a spy rather than written to the DB on purpose: the real
     * flag lives in an in-memory cache on ShowDaoJdbc that is NOT rolled back with the transaction,
     * so a real write would leak scheduler-managed behavior into other tests sharing the Spring
     * context.
     */
    private void executeProcReuseGate(boolean schedulerManaged, FrameState terminalState) {
        JobDetail job = jobManager.findJobDetail("pipe-default-testuser_test_depend");
        jobManager.setJobPaused(job, false);

        DispatchHost host = getHost(HOSTNAME);
        List<VirtualProc> procs = dispatcher.dispatchHost(host);
        assertEquals(1, procs.size());
        VirtualProc proc = procs.get(0);

        RunningFrameInfo info = RunningFrameInfo.newBuilder().setJobId(proc.getJobId())
                .setLayerId(proc.getLayerId()).setFrameId(proc.getFrameId())
                .setResourceId(proc.getProcId()).build();
        // The report must carry a healthy host (UP, plenty of free memory), otherwise the handler
        // unbooks the proc early (e.g. the < 512MB low-memory check) and returns before reaching
        // the
        // WAITING/SUCCEEDED proc-reuse branch that the scheduler-managed gate lives in.
        RenderHost reportHost =
                RenderHost.newBuilder().setName(HOSTNAME).setFreeMem((int) CueUtil.GB8)
                        .setNimbyEnabled(false).setState(HardwareState.UP).build();
        FrameCompleteReport report = FrameCompleteReport.newBuilder().setFrame(info)
                .setHost(reportHost).setExitStatus(0).build();

        DispatchJob dispatchJob = jobManager.getDispatchJob(proc.getJobId());
        DispatchFrame dispatchFrame = jobManager.getDispatchFrame(report.getFrame().getFrameId());
        FrameDetail frameDetail = jobManager.getFrameDetail(report.getFrame().getFrameId());
        dispatchSupport.stopFrame(dispatchFrame, terminalState, report.getExitStatus(),
                report.getFrame().getMaxRss());

        // The DAO beans are Spring JDK dynamic proxies (final), so they can't be spied. Wrap them
        // in interface mocks that delegate to the real bean for everything except the one method we
        // stub, while still recording invocations for verification.
        ShowDao originalShowDao = frameCompleteHandler.getShowDao();
        DispatchSupport originalDispatchSupport = frameCompleteHandler.getDispatchSupport();
        ShowDao mockShowDao = mock(ShowDao.class, delegatesTo(originalShowDao));
        DispatchSupport mockDispatchSupport =
                mock(DispatchSupport.class, delegatesTo(originalDispatchSupport));
        doReturn(schedulerManaged).when(mockShowDao).isSchedulerManaged(proc.getShowId());

        frameCompleteHandler.setShowDao(mockShowDao);
        frameCompleteHandler.setDispatchSupport(mockDispatchSupport);
        try {
            frameCompleteHandler.handlePostFrameCompleteOperations(proc, report, dispatchJob,
                    dispatchFrame, terminalState, frameDetail);
        } finally {
            frameCompleteHandler.setShowDao(originalShowDao);
            frameCompleteHandler.setDispatchSupport(originalDispatchSupport);
        }

        verify(mockDispatchSupport, schedulerManaged ? times(1) : never())
                .unbookProc(any(VirtualProc.class), eq("scheduler-managed show, releasing proc"));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testSchedulerManagedShowReleasesProc() {
        // Scheduler-managed, SUCCEEDED: the proc must be unbooked (released), not reused.
        executeProcReuseGate(true, FrameState.SUCCEEDED);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testNonSchedulerManagedShowReusesProc() {
        // Control, SUCCEEDED: the scheduler-managed release branch must not fire.
        executeProcReuseGate(false, FrameState.SUCCEEDED);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testSchedulerManagedShowReleasesProcWaiting() {
        // Scheduler-managed, WAITING: the other side of the WAITING/SUCCEEDED gate must also
        // release the proc.
        executeProcReuseGate(true, FrameState.WAITING);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testNonSchedulerManagedShowReusesProcWaiting() {
        // Control, WAITING: the scheduler-managed release branch must not fire.
        executeProcReuseGate(false, FrameState.WAITING);
    }

    /**
     * Bundles mock collaborators for the handler. The managers delegate to the real beans so only
     * individual methods need stubbing, while the queues, JMS mover and redirect manager are plain
     * mocks so no asynchronous work escapes the test thread. Run the code under test through
     * {@link #runWith} so installation is always paired with restoration of the real beans.
     */
    private class HandlerMocks {
        final DispatchSupport origDispatchSupport = frameCompleteHandler.getDispatchSupport();
        final HostManager origHostManager = frameCompleteHandler.getHostManager();
        final JobManager origJobManager = frameCompleteHandler.getJobManager();
        final DispatchQueue origDispatchQueue = frameCompleteHandler.getDispatchQueue();
        final BookingQueue origBookingQueue = frameCompleteHandler.getBookingQueue();
        final JmsMover origJmsMover = frameCompleteHandler.getJmsMover();
        final RedirectManager origRedirectManager = frameCompleteHandler.getRedirectManager();

        final DispatchSupport dispatchSupport =
                mock(DispatchSupport.class, delegatesTo(origDispatchSupport));
        final HostManager hostManager = mock(HostManager.class, delegatesTo(origHostManager));
        final JobManager jobManager = mock(JobManager.class, delegatesTo(origJobManager));
        final DispatchQueue dispatchQueue = mock(DispatchQueue.class);
        final BookingQueue bookingQueue = mock(BookingQueue.class);
        final JmsMover jmsMover = mock(JmsMover.class);
        final RedirectManager redirectManager = mock(RedirectManager.class);

        /** Installs the mocks on the handler, runs the task, and always restores the real beans. */
        void runWith(Runnable task) {
            install();
            try {
                task.run();
            } finally {
                restore();
            }
        }

        private void install() {
            frameCompleteHandler.setDispatchSupport(dispatchSupport);
            frameCompleteHandler.setHostManager(hostManager);
            frameCompleteHandler.setJobManager(jobManager);
            frameCompleteHandler.setDispatchQueue(dispatchQueue);
            frameCompleteHandler.setBookingQueue(bookingQueue);
            frameCompleteHandler.setJmsMover(jmsMover);
            frameCompleteHandler.setRedirectManager(redirectManager);
        }

        private void restore() {
            frameCompleteHandler.setDispatchSupport(origDispatchSupport);
            frameCompleteHandler.setHostManager(origHostManager);
            frameCompleteHandler.setJobManager(origJobManager);
            frameCompleteHandler.setDispatchQueue(origDispatchQueue);
            frameCompleteHandler.setBookingQueue(origBookingQueue);
            frameCompleteHandler.setJmsMover(origJmsMover);
            frameCompleteHandler.setRedirectManager(origRedirectManager);
        }
    }

    private RenderHost.Builder healthyReportHost() {
        return RenderHost.newBuilder().setName(HOSTNAME).setFreeMem((int) CueUtil.GB8)
                .setNimbyEnabled(false).setState(HardwareState.UP);
    }

    private VirtualProc dispatchTestDependProc() {
        JobDetail job = jobManager.findJobDetail("pipe-default-testuser_test_depend");
        jobManager.setJobPaused(job, false);
        List<VirtualProc> procs = dispatcher.dispatchHost(getHost(HOSTNAME));
        assertEquals(1, procs.size());
        return procs.get(0);
    }

    private FrameCompleteReport buildReport(VirtualProc proc, String resourceId, RenderHost host,
            int exitStatus) {
        RunningFrameInfo info = RunningFrameInfo.newBuilder().setJobId(proc.getJobId())
                .setLayerId(proc.getLayerId()).setFrameId(proc.getFrameId())
                .setResourceId(resourceId).build();
        return FrameCompleteReport.newBuilder().setFrame(info).setHost(host)
                .setExitStatus(exitStatus).build();
    }

    private FrameCompleteReport buildReport(VirtualProc proc, RenderHost host, int exitStatus) {
        return buildReport(proc, proc.getProcId(), host, exitStatus);
    }

    /**
     * Stops the proc's frame with the given state, then runs handlePostFrameCompleteOperations with
     * the mocks installed.
     */
    private void runPostFrameComplete(HandlerMocks mocks, VirtualProc proc,
            FrameCompleteReport report, FrameState newFrameState, DispatchJob dispatchJob) {
        DispatchFrame dispatchFrame = jobManager.getDispatchFrame(report.getFrame().getFrameId());
        FrameDetail frameDetail = jobManager.getFrameDetail(report.getFrame().getFrameId());
        dispatchSupport.stopFrame(dispatchFrame, newFrameState, report.getExitStatus(),
                report.getFrame().getMaxRss());
        mocks.runWith(() -> frameCompleteHandler.handlePostFrameCompleteOperations(proc, report,
                dispatchJob, dispatchFrame, newFrameState, frameDetail));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFailedLaunchUnbooksProc() {
        VirtualProc proc = dispatchTestDependProc();
        HandlerMocks mocks = new HandlerMocks();
        runPostFrameComplete(mocks, proc,
                buildReport(proc, healthyReportHost().build(), FrameExitStatus.FAILED_LAUNCH_VALUE),
                FrameState.WAITING, jobManager.getDispatchJob(proc.getJobId()));

        verify(mocks.dispatchSupport).unbookProc(proc);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testNimbyLockedHostUnbooksProcAndSetsHostLock() {
        VirtualProc proc = dispatchTestDependProc();
        HandlerMocks mocks = new HandlerMocks();
        runPostFrameComplete(mocks, proc,
                buildReport(proc, healthyReportHost().setNimbyLocked(true).build(), 0),
                FrameState.SUCCEEDED, jobManager.getDispatchJob(proc.getJobId()));

        verify(mocks.hostManager).setHostLock(eq(proc), eq(LockState.NIMBY_LOCKED),
                any(Source.class));
        verify(mocks.dispatchSupport).unbookProc(proc);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testLowMemoryHostUnbooksProc() {
        VirtualProc proc = dispatchTestDependProc();
        HandlerMocks mocks = new HandlerMocks();
        runPostFrameComplete(mocks, proc,
                buildReport(proc, healthyReportHost().setFreeMem(1000).build(), 0),
                FrameState.SUCCEEDED, jobManager.getDispatchJob(proc.getJobId()));

        verify(mocks.dispatchSupport).unbookProc(proc);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testShowOverBurstUnbooksProc() {
        VirtualProc proc = dispatchTestDependProc();
        HandlerMocks mocks = new HandlerMocks();
        doReturn(true).when(mocks.dispatchSupport).isShowOverBurst(any(VirtualProc.class));
        runPostFrameComplete(mocks, proc, buildReport(proc, healthyReportHost().build(), 0),
                FrameState.SUCCEEDED, jobManager.getDispatchJob(proc.getJobId()));

        verify(mocks.dispatchSupport).unbookProc(proc);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDownHostUnbooksProc() {
        VirtualProc proc = dispatchTestDependProc();
        HandlerMocks mocks = new HandlerMocks();
        doReturn(false).when(mocks.hostManager).isHostUp(any(HostInterface.class));
        runPostFrameComplete(mocks, proc, buildReport(proc, healthyReportHost().build(), 0),
                FrameState.SUCCEEDED, jobManager.getDispatchJob(proc.getJobId()));

        verify(mocks.dispatchSupport).unbookProc(proc);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testLockedHostUnbooksProc() {
        VirtualProc proc = dispatchTestDependProc();
        HandlerMocks mocks = new HandlerMocks();
        doReturn(true).when(mocks.hostManager).isLocked(any(HostInterface.class));
        runPostFrameComplete(mocks, proc, buildReport(proc, healthyReportHost().build(), 0),
                FrameState.SUCCEEDED, jobManager.getDispatchJob(proc.getJobId()));

        verify(mocks.dispatchSupport).unbookProc(proc);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testLocalDispatchWithoutAssignmentUnbooksProc() {
        VirtualProc proc = dispatchTestDependProc();
        proc.isLocalDispatch = true;
        HandlerMocks mocks = new HandlerMocks();
        runPostFrameComplete(mocks, proc, buildReport(proc, healthyReportHost().build(), 0),
                FrameState.SUCCEEDED, jobManager.getDispatchJob(proc.getJobId()));

        verify(mocks.dispatchSupport).unbookProc(proc);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFinishedJobUnbooksProcAndSendsJmsUpdate() {
        VirtualProc proc = dispatchTestDependProc();
        DispatchJob dispatchJob = jobManager.getDispatchJob(proc.getJobId());
        dispatchJob.state = JobState.FINISHED;
        HandlerMocks mocks = new HandlerMocks();
        runPostFrameComplete(mocks, proc, buildReport(proc, healthyReportHost().build(), 0),
                FrameState.SUCCEEDED, dispatchJob);

        verify(mocks.dispatchSupport).unbookProc(proc);
        verify(mocks.jmsMover).send(dispatchJob);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testStrandedCoresRebookHost() {
        VirtualProc proc = dispatchTestDependProc();
        HandlerMocks mocks = new HandlerMocks();
        doReturn(true).when(mocks.dispatchSupport).hasStrandedCores(any(HostInterface.class));
        doReturn(true).when(mocks.dispatchSupport).isJobBookable(any(JobInterface.class));
        doReturn(true).when(mocks.jobManager).isLayerThreadable(any(LayerInterface.class));
        doReturn(200).when(mocks.hostManager).getStrandedCoreUnits(any(HostInterface.class));
        runPostFrameComplete(mocks, proc, buildReport(proc, healthyReportHost().build(), 0),
                FrameState.SUCCEEDED, jobManager.getDispatchJob(proc.getJobId()));

        verify(mocks.dispatchSupport).strandCores(any(DispatchHost.class), eq(200));
        verify(mocks.dispatchSupport).unbookProc(proc);
        verify(mocks.bookingQueue).execute(any(KeyRunnable.class));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testTerminalFrameStateUnbooksProc() {
        VirtualProc proc = dispatchTestDependProc();
        HandlerMocks mocks = new HandlerMocks();
        // A DEAD frame leaves this job with no waiting frames, which would divert the flow into
        // the undispatchable-job branch before the terminal-state check this test pins down.
        doReturn(true).when(mocks.dispatchSupport).isJobDispatchable(any(JobInterface.class),
                anyBoolean());
        runPostFrameComplete(mocks, proc, buildReport(proc, healthyReportHost().build(), 1),
                FrameState.DEAD, jobManager.getDispatchJob(proc.getJobId()));

        verify(mocks.dispatchSupport).unbookProc(proc, "frame state was DEAD");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testMemoryFailureFollowsSuccessfulRedirect() {
        VirtualProc proc = dispatchTestDependProc();
        HandlerMocks mocks = new HandlerMocks();
        doReturn(true).when(mocks.redirectManager).hasRedirect(any(VirtualProc.class));
        doReturn(true).when(mocks.redirectManager).redirect(any(VirtualProc.class));
        runPostFrameComplete(mocks, proc,
                buildReport(proc, healthyReportHost().build(),
                        Dispatcher.EXIT_STATUS_MEMORY_FAILURE),
                FrameState.WAITING, jobManager.getDispatchJob(proc.getJobId()));

        // A successful redirect must win over the unbook flag set by the memory failure.
        verify(mocks.redirectManager).redirect(any(VirtualProc.class));
        verify(mocks.dispatchSupport, never()).unbookProc(any(VirtualProc.class));
        verify(mocks.dispatchSupport, never()).unbookProc(any(VirtualProc.class), anyString());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFailedRedirectFallsThroughToNextFrame() {
        VirtualProc proc = dispatchTestDependProc();
        HandlerMocks mocks = new HandlerMocks();
        doReturn(true).when(mocks.redirectManager).hasRedirect(any(VirtualProc.class));
        doReturn(false).when(mocks.redirectManager).redirect(any(VirtualProc.class));
        runPostFrameComplete(mocks, proc, buildReport(proc, healthyReportHost().build(), 0),
                FrameState.SUCCEEDED, jobManager.getDispatchJob(proc.getJobId()));

        // A failed redirect must not strand the proc; the next frame is booked as usual.
        verify(mocks.dispatchQueue).execute(any(DispatchNextFrame.class));
        verify(mocks.dispatchSupport, never()).unbookProc(any(VirtualProc.class));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testHealthyProcBooksNextFrame() {
        VirtualProc proc = dispatchTestDependProc();
        HandlerMocks mocks = new HandlerMocks();
        runPostFrameComplete(mocks, proc, buildReport(proc, healthyReportHost().build(), 0),
                FrameState.SUCCEEDED, jobManager.getDispatchJob(proc.getJobId()));

        verify(mocks.dispatchQueue).execute(any(DispatchNextFrame.class));
        verify(mocks.dispatchSupport, never()).unbookProc(any(VirtualProc.class));
        verify(mocks.dispatchSupport, never()).unbookProc(any(VirtualProc.class), anyString());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testStaleReportUnbooksProc() {
        VirtualProc proc = dispatchTestDependProc();
        DispatchFrame dispatchFrame = jobManager.getDispatchFrame(proc.getFrameId());
        dispatchSupport.stopFrame(dispatchFrame, FrameState.WAITING, 1, 0);

        HandlerMocks mocks = new HandlerMocks();
        doAnswer(invocation -> {
            ((KeyRunnable) invocation.getArgument(0)).run();
            return null;
        }).when(mocks.dispatchQueue).execute(any(KeyRunnable.class));

        mocks.runWith(() -> frameCompleteHandler
                .handleFrameCompleteReport(buildReport(proc, healthyReportHost().build(), 0)));

        // The stale branch must go through the dispatch queue, never run inline.
        verify(mocks.dispatchQueue).execute(any(KeyRunnable.class));
        verify(mocks.dispatchSupport).unbookProc(any(VirtualProc.class));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testStaleReportFollowsRedirect() {
        VirtualProc proc = dispatchTestDependProc();
        DispatchFrame dispatchFrame = jobManager.getDispatchFrame(proc.getFrameId());
        dispatchSupport.stopFrame(dispatchFrame, FrameState.WAITING, 1, 0);

        HandlerMocks mocks = new HandlerMocks();
        doReturn(true).when(mocks.redirectManager).hasRedirect(any(VirtualProc.class));
        doReturn(true).when(mocks.redirectManager).redirect(any(VirtualProc.class));
        doAnswer(invocation -> {
            ((KeyRunnable) invocation.getArgument(0)).run();
            return null;
        }).when(mocks.dispatchQueue).execute(any(KeyRunnable.class));

        mocks.runWith(() -> frameCompleteHandler
                .handleFrameCompleteReport(buildReport(proc, healthyReportHost().build(), 0)));

        // The stale branch must go through the dispatch queue, never run inline.
        verify(mocks.dispatchQueue).execute(any(KeyRunnable.class));
        verify(mocks.redirectManager).redirect(any(VirtualProc.class));
        verify(mocks.dispatchSupport, never()).unbookProc(any(VirtualProc.class));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDuplicateReportDroppedWhenProcMovedToNextFrame() {
        JobDetail job = jobManager.findJobDetail("pipe-default-testuser_test_depend");
        VirtualProc proc = dispatchTestDependProc();

        // Snapshot report 1, which targets the frame the proc is currently running.
        FrameCompleteReport report = buildReport(proc, healthyReportHost().build(), 0);
        String firstFrameId = proc.getFrameId();

        // Simulate report 1 having already been fully processed: its frame is stopped
        // and the proc has been rebooked onto its next frame, keeping the same pk_proc.
        DispatchFrame firstFrame = jobManager.getDispatchFrame(firstFrameId);
        dispatchSupport.stopFrame(firstFrame, FrameState.SUCCEEDED, 0, 0);
        FrameDetail secondFrame = frameDao.findFrameDetail(job, "0000-layer_second");
        proc.frameId = secondFrame.getFrameId();
        proc.layerId = secondFrame.getLayerId();
        procDao.updateVirtualProcAssignment(proc);

        HandlerMocks mocks = new HandlerMocks();
        doAnswer(invocation -> {
            ((KeyRunnable) invocation.getArgument(0)).run();
            return null;
        }).when(mocks.dispatchQueue).execute(any(KeyRunnable.class));

        // RQD resends report 1 after its ack was lost.
        mocks.runWith(() -> frameCompleteHandler.handleFrameCompleteReport(report));

        // The duplicate must be dropped: the proc is never unbooked and keeps the new
        // frame, so frame N+1 is not orphaned.
        verify(mocks.dispatchSupport, never()).unbookProc(any(VirtualProc.class));
        verify(mocks.dispatchSupport, never()).unbookProc(any(VirtualProc.class), anyString());
        VirtualProc live = hostManager.getVirtualProc(proc.getProcId());
        assertEquals(secondFrame.getFrameId(), live.getFrameId());
    }

    @Test(expected = RqdRetryReportException.class)
    public void testShutdownRejectsNewReports() {
        FrameCompleteHandler handler =
                new FrameCompleteHandler(applicationContext.getEnvironment());
        handler.shutdown();
        handler.handleFrameCompleteReport(FrameCompleteReport.getDefaultInstance());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testOrphanedReportFinalizesRunningFrame() {
        JobDetail job = jobManager.findJobDetail("pipe-default-testuser_test_depend");
        LayerDetail layerFirst = layerDao.findLayerDetail(job, "layer_first");
        VirtualProc proc = dispatchTestDependProc();

        // Remove the proc while the frame is still RUNNING, orphaning it.
        dispatchSupport.unbookProc(proc);
        assertEquals(FrameState.RUNNING, frameDao.findFrameDetail(job, "0000-layer_first").state);

        frameCompleteHandler
                .handleFrameCompleteReport(buildReport(proc, healthyReportHost().build(), 0));

        assertEquals(FrameState.SUCCEEDED, frameDao.findFrameDetail(job, "0000-layer_first").state);
        assertTrue(jobManager.isLayerComplete(layerFirst));

        FrameDetail frameSecond = frameDao.findFrameDetail(job, "0000-layer_second");
        assertEquals(0, frameSecond.dependCount);
        assertEquals(FrameState.WAITING, frameSecond.state);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testOrphanedReportIgnoredWhenFrameNotRunning() {
        JobDetail job = jobManager.findJobDetail("pipe-default-testuser_test_depend");
        VirtualProc proc = dispatchTestDependProc();

        DispatchFrame dispatchFrame = jobManager.getDispatchFrame(proc.getFrameId());
        dispatchSupport.stopFrame(dispatchFrame, FrameState.EATEN, 0, 0);
        dispatchSupport.unbookProc(proc);

        HandlerMocks mocks = new HandlerMocks();
        mocks.runWith(() -> frameCompleteHandler
                .handleFrameCompleteReport(buildReport(proc, healthyReportHost().build(), 0)));

        // The stale report must be dropped without touching the frame or its counters.
        verify(mocks.dispatchSupport, never()).stopFrame(any(DispatchFrame.class),
                any(FrameState.class), anyInt(), anyLong());
        verify(mocks.dispatchSupport, never()).updateUsageCounters(any(DispatchFrame.class),
                anyInt());
        assertEquals(FrameState.EATEN, frameDao.findFrameDetail(job, "0000-layer_first").state);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testOrphanedReportIgnoredWhenFrameOwnedByAnotherProc() {
        JobDetail job = jobManager.findJobDetail("pipe-default-testuser_test_depend");
        VirtualProc proc = dispatchTestDependProc();

        // Report from a proc id that no longer exists, while the live proc still owns the frame.
        frameCompleteHandler.handleFrameCompleteReport(buildReport(proc,
                "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", healthyReportHost().build(), 0));

        assertEquals(FrameState.RUNNING, frameDao.findFrameDetail(job, "0000-layer_first").state);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testOrphanedReportForUnknownFrameIsDropped() {
        RunningFrameInfo info =
                RunningFrameInfo.newBuilder().setJobId("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
                        .setLayerId("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
                        .setFrameId("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
                        .setResourceId("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa").build();
        FrameCompleteReport report = FrameCompleteReport.newBuilder().setFrame(info)
                .setHost(healthyReportHost().build()).setExitStatus(0).build();

        // Both the proc and the frame are gone; the report must be dropped without retrying RQD.
        frameCompleteHandler.handleFrameCompleteReport(report);
    }
}
