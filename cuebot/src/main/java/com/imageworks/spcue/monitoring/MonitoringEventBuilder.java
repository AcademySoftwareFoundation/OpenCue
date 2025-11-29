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

package com.imageworks.spcue.monitoring;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.DispatchJob;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.host.LockState;
import com.imageworks.spcue.grpc.host.ThreadMode;
import com.imageworks.spcue.grpc.job.CheckpointState;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.grpc.job.LayerType;
import com.imageworks.spcue.grpc.monitoring.EventHeader;
import com.imageworks.spcue.grpc.monitoring.EventType;
import com.imageworks.spcue.grpc.monitoring.FrameEvent;
import com.imageworks.spcue.grpc.monitoring.HostEvent;
import com.imageworks.spcue.grpc.monitoring.HostReportEvent;
import com.imageworks.spcue.grpc.monitoring.JobEvent;
import com.imageworks.spcue.grpc.monitoring.LayerEvent;
import com.imageworks.spcue.grpc.monitoring.ProcEvent;
import com.imageworks.spcue.grpc.monitoring.RunningFrameSummary;
import com.imageworks.spcue.grpc.report.FrameCompleteReport;
import com.imageworks.spcue.grpc.report.HostReport;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.grpc.report.RunningFrameInfo;

import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;

/**
 * Helper class for building monitoring events from OpenCue domain objects. Provides factory methods
 * to create properly populated event messages.
 */
public class MonitoringEventBuilder {

    private final KafkaEventPublisher publisher;

    public MonitoringEventBuilder(KafkaEventPublisher publisher) {
        this.publisher = publisher;
    }

    /**
     * Builds a JobEvent for a job state change.
     */
    public JobEvent buildJobEvent(EventType eventType, JobDetail job, JobState previousState,
            String reason, String killedBy) {
        EventHeader header = publisher.createEventHeader(eventType, job.getJobId()).build();

        JobEvent.Builder builder = JobEvent.newBuilder().setHeader(header).setJobId(job.getJobId())
                .setJobName(job.getName()).setShow(job.showName != null ? job.showName : "")
                .setShot(job.shot).setUser(job.user).setFacility(job.facilityName)
                .setGroup(job.groupId != null ? job.groupId : "").setState(job.state)
                .setPreviousState(previousState).setPriority(job.priority)
                .setMinCores(job.minCoreUnits / 100.0f).setMaxCores(job.maxCoreUnits / 100.0f)
                .setMinGpus(job.minGpuUnits).setMaxGpus(job.maxGpuUnits).setIsPaused(job.isPaused)
                .setAutoEat(job.isAutoEat).setLogDir(job.logDir != null ? job.logDir : "")
                .setOs(job.os != null ? job.os : "");

        if (job.startTime > 0) {
            builder.setStartTime(job.startTime);
        }
        if (job.stopTime > 0) {
            builder.setStopTime(job.stopTime);
        }
        if (reason != null) {
            builder.setReason(reason);
        }
        if (killedBy != null) {
            builder.setKilledBy(killedBy);
        }

        return builder.build();
    }

    /**
     * Builds a JobEvent for a dispatch job (lighter weight).
     */
    public JobEvent buildJobEvent(EventType eventType, DispatchJob job, JobState previousState) {
        EventHeader header = publisher.createEventHeader(eventType, job.getJobId()).build();

        return JobEvent.newBuilder().setHeader(header).setJobId(job.getJobId())
                .setJobName(job.getName()).setState(job.state).setPreviousState(previousState)
                .setIsPaused(job.paused).setAutoEat(job.autoEat).build();
    }

    /**
     * Builds a LayerEvent for a layer.
     */
    public LayerEvent buildLayerEvent(EventType eventType, LayerDetail layer, String jobName,
            String show) {
        EventHeader header = publisher.createEventHeader(eventType, layer.getJobId()).build();

        LayerEvent.Builder builder = LayerEvent.newBuilder().setHeader(header)
                .setLayerId(layer.getLayerId()).setLayerName(layer.getName())
                .setJobId(layer.getJobId()).setJobName(jobName).setShow(show).setType(layer.type)
                .setMinCores(layer.minimumCores / 100.0f).setMaxCores(layer.maximumCores / 100.0f)
                .setMinGpus(layer.minimumGpus).setMaxGpus(layer.maximumGpus)
                .setMinMemory(layer.minimumMemory).setMinGpuMemory(layer.minimumGpuMemory)
                .setIsThreadable(layer.isThreadable).setChunkSize(layer.chunkSize)
                .setTimeout(layer.timeout).setTimeoutLlu(layer.timeout_llu);

        if (layer.tags != null && !layer.tags.isEmpty()) {
            builder.addAllTags(layer.tags);
        }
        if (layer.services != null && !layer.services.isEmpty()) {
            builder.addAllServices(layer.services);
        }
        if (layer.command != null) {
            builder.setCommand(layer.command);
        }

        return builder.build();
    }

    /**
     * Builds a FrameEvent for a frame completion.
     */
    public FrameEvent buildFrameCompleteEvent(FrameCompleteReport report, FrameState newState,
            FrameState previousState, DispatchFrame frame, VirtualProc proc) {
        EventType eventType = determineFrameEventType(newState);
        EventHeader header = publisher.createEventHeader(eventType, frame.getJobId()).build();

        FrameEvent.Builder builder = FrameEvent.newBuilder().setHeader(header)
                .setFrameId(frame.getFrameId()).setFrameName(frame.getName())
                .setLayerId(frame.getLayerId()).setLayerName(frame.layerName)
                .setJobId(frame.getJobId()).setJobName(report.getFrame().getJobName())
                .setShow(frame.show).setState(newState).setPreviousState(previousState)
                .setRetryCount(frame.retries).setExitStatus(report.getExitStatus())
                .setExitSignal(report.getExitSignal())
                .setStartTime(report.getFrame().getStartTime())
                .setStopTime(System.currentTimeMillis()).setRunTime(report.getRunTime())
                .setLluTime(report.getFrame().getLluTime()).setMaxRss(report.getFrame().getMaxRss())
                .setUsedMemory(report.getFrame().getRss()).setReservedMemory(proc.memoryReserved)
                .setMaxGpuMemory(report.getFrame().getMaxUsedGpuMemory())
                .setUsedGpuMemory(report.getFrame().getUsedGpuMemory())
                .setReservedGpuMemory(proc.gpuMemoryReserved)
                .setNumCores(report.getFrame().getNumCores())
                .setNumGpus(report.getFrame().getNumGpus()).setHostName(report.getHost().getName())
                .setResourceId(report.getFrame().getResourceId());

        return builder.build();
    }

    /**
     * Builds a FrameEvent for a frame becoming dispatchable (DEPEND -> WAITING transition).
     */
    public FrameEvent buildFrameDispatchableEvent(FrameDetail frame) {
        EventHeader header =
                publisher.createEventHeader(EventType.FRAME_DISPATCHED, frame.getJobId()).build();

        FrameEvent.Builder builder =
                FrameEvent.newBuilder().setHeader(header).setFrameId(frame.getFrameId())
                        .setFrameName(frame.getName()).setFrameNumber(frame.number)
                        .setLayerId(frame.getLayerId()).setJobId(frame.getJobId())
                        .setState(FrameState.WAITING).setPreviousState(FrameState.DEPEND)
                        .setRetryCount(frame.retryCount).setDispatchOrder(frame.dispatchOrder);

        return builder.build();
    }

    /**
     * Builds a FrameEvent for a frame being started (WAITING -> RUNNING transition).
     */
    public FrameEvent buildFrameStartedEvent(DispatchFrame frame, VirtualProc proc) {
        EventHeader header =
                publisher.createEventHeader(EventType.FRAME_STARTED, frame.getJobId()).build();

        FrameEvent.Builder builder = FrameEvent.newBuilder().setHeader(header)
                .setFrameId(frame.getFrameId()).setFrameName(frame.getName())
                .setLayerId(frame.getLayerId()).setLayerName(frame.layerName)
                .setJobId(frame.getJobId()).setJobName(frame.jobName).setShow(frame.show)
                .setState(FrameState.RUNNING).setPreviousState(frame.state)
                .setRetryCount(frame.retries).setStartTime(System.currentTimeMillis())
                .setReservedMemory(proc.memoryReserved).setReservedGpuMemory(proc.gpuMemoryReserved)
                .setNumCores((int) (proc.coresReserved / 100.0f)).setNumGpus(proc.gpusReserved)
                .setHostName(proc.hostName);

        return builder.build();
    }

    /**
     * Builds a FrameEvent for a frame state change (not completion).
     */
    public FrameEvent buildFrameEvent(EventType eventType, FrameDetail frame, String jobName,
            String layerName, String show, FrameState previousState, String reason,
            String killedBy) {
        EventHeader header = publisher.createEventHeader(eventType, frame.getJobId()).build();

        FrameEvent.Builder builder = FrameEvent.newBuilder().setHeader(header)
                .setFrameId(frame.getFrameId()).setFrameName(frame.getName())
                .setFrameNumber(frame.number).setLayerId(frame.getLayerId()).setLayerName(layerName)
                .setJobId(frame.getJobId()).setJobName(jobName).setShow(show).setState(frame.state)
                .setPreviousState(previousState).setRetryCount(frame.retryCount)
                .setExitStatus(frame.exitStatus).setDispatchOrder(frame.dispatchOrder);

        if (frame.dateStarted != null) {
            builder.setStartTime(frame.dateStarted.getTime());
        }
        if (frame.dateStopped != null) {
            builder.setStopTime(frame.dateStopped.getTime());
        }
        if (frame.maxRss > 0) {
            builder.setMaxRss(frame.maxRss);
        }
        if (frame.lastResource != null) {
            builder.setHostName(frame.lastResource);
        }
        if (reason != null) {
            builder.setReason(reason);
        }
        if (killedBy != null) {
            builder.setKilledBy(killedBy);
        }

        return builder.build();
    }

    /**
     * Builds a HostEvent for a host state change.
     */
    public HostEvent buildHostEvent(EventType eventType, DispatchHost host,
            HardwareState previousState, LockState previousLockState, String reason) {
        EventHeader header = publisher.createEventHeader(eventType, host.getHostId()).build();

        // Convert int threadMode to ThreadMode enum
        ThreadMode threadMode = host.threadMode == 0 ? ThreadMode.AUTO : ThreadMode.ALL;

        HostEvent.Builder builder = HostEvent.newBuilder().setHeader(header)
                .setHostId(host.getHostId()).setHostName(host.getName())
                .setFacility(host.getFacilityId() != null ? host.getFacilityId() : "")
                .setAllocation(host.getAllocationId() != null ? host.getAllocationId() : "")
                .setState(host.hardwareState).setPreviousState(previousState)
                .setLockState(host.lockState).setPreviousLockState(previousLockState)
                .setNimbyEnabled(host.isNimby).setThreadMode(threadMode)
                .setTotalCores(host.cores / 100.0f).setIdleCores(host.idleCores / 100.0f)
                .setTotalMemory(host.memory).setIdleMemory(host.idleMemory).setTotalGpus(host.gpus)
                .setIdleGpus(host.idleGpus).setTotalGpuMemory(host.gpuMemory)
                .setIdleGpuMemory(host.idleGpuMemory);

        String[] osArray = host.getOs();
        if (osArray != null && osArray.length > 0) {
            builder.setOs(String.join(",", osArray));
        }
        if (host.tags != null) {
            builder.addAllTags(Arrays.asList(host.tags.split("\\|")));
        }
        if (reason != null) {
            builder.setReason(reason);
        }

        return builder.build();
    }

    /**
     * Builds a HostReportEvent from a host report.
     */
    public HostReportEvent buildHostReportEvent(HostReport report, boolean isBoot) {
        EventType eventType = isBoot ? EventType.HOST_BOOT : EventType.HOST_REPORT;
        EventHeader header = publisher.createEventHeader(eventType).build();

        RenderHost rhost = report.getHost();

        HostReportEvent.Builder builder = HostReportEvent.newBuilder().setHeader(header)
                .setHostName(rhost.getName()).setFacility(rhost.getFacility()).setHostData(rhost)
                .setCoreInfo(report.getCoreInfo()).setIsBootReport(isBoot);

        // Add running frame summaries
        List<RunningFrameSummary> frameSummaries = report.getFramesList().stream()
                .map(this::buildRunningFrameSummary).collect(Collectors.toList());
        builder.addAllRunningFrames(frameSummaries);

        return builder.build();
    }

    /**
     * Builds a running frame summary from RunningFrameInfo.
     */
    private RunningFrameSummary buildRunningFrameSummary(RunningFrameInfo frame) {
        return RunningFrameSummary.newBuilder().setFrameId(frame.getFrameId())
                .setFrameName(frame.getFrameName()).setJobId(frame.getJobId())
                .setJobName(frame.getJobName()).setLayerId(frame.getLayerId())
                .setNumCores(frame.getNumCores()).setStartTime(frame.getStartTime())
                .setRss(frame.getRss()).setMaxRss(frame.getMaxRss()).setVsize(frame.getVsize())
                .setMaxVsize(frame.getMaxVsize()).setUsedGpuMemory(frame.getUsedGpuMemory())
                .setMaxUsedGpuMemory(frame.getMaxUsedGpuMemory())
                .setUsedSwapMemory(frame.getUsedSwapMemory()).setLluTime(frame.getLluTime())
                .build();
    }

    /**
     * Builds a ProcEvent for a proc booking/unbooking.
     */
    public ProcEvent buildProcEvent(EventType eventType, VirtualProc proc) {
        EventHeader header = publisher.createEventHeader(eventType, proc.getJobId()).build();

        ProcEvent.Builder builder = ProcEvent.newBuilder().setHeader(header)
                .setProcId(proc.getProcId()).setProcName(proc.getName()).setHostId(proc.getHostId())
                .setHostName(proc.hostName).setJobId(proc.getJobId())
                .setFrameId(proc.frameId != null ? proc.frameId : "")
                .setReservedCores(proc.coresReserved / 100.0f).setReservedGpus(proc.gpusReserved)
                .setReservedMemory(proc.memoryReserved).setReservedGpuMemory(proc.gpuMemoryReserved)
                .setIsLocalDispatch(proc.isLocalDispatch).setIsUnbooked(proc.unbooked);

        return builder.build();
    }

    /**
     * Determines the appropriate event type based on the frame's new state.
     */
    private EventType determineFrameEventType(FrameState state) {
        switch (state) {
            case SUCCEEDED:
                return EventType.FRAME_COMPLETED;
            case DEAD:
                return EventType.FRAME_FAILED;
            case EATEN:
                return EventType.FRAME_EATEN;
            case WAITING:
                return EventType.FRAME_RETRIED;
            case CHECKPOINT:
                return EventType.FRAME_CHECKPOINT;
            default:
                return EventType.FRAME_COMPLETED;
        }
    }
}
