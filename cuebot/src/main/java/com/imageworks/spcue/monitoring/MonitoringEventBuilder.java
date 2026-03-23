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
import com.imageworks.spcue.grpc.host.Host;
import com.imageworks.spcue.grpc.host.LockState;
import com.imageworks.spcue.grpc.host.ThreadMode;
import com.imageworks.spcue.grpc.job.CheckpointState;
import com.imageworks.spcue.grpc.job.Frame;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.job.Job;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.grpc.job.Layer;
import com.imageworks.spcue.grpc.job.LayerType;
import com.imageworks.spcue.grpc.monitoring.EventHeader;
import com.imageworks.spcue.grpc.monitoring.EventType;
import com.imageworks.spcue.grpc.monitoring.FrameEvent;
import com.imageworks.spcue.grpc.monitoring.HostEvent;
import com.imageworks.spcue.grpc.monitoring.JobEvent;
import com.imageworks.spcue.grpc.monitoring.LayerEvent;
import com.imageworks.spcue.grpc.monitoring.ProcEvent;
import com.imageworks.spcue.grpc.report.FrameCompleteReport;

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

        // Build the embedded Job message
        Job.Builder jobBuilder = Job.newBuilder().setId(job.getJobId()).setName(job.getName())
                .setShow(job.showName != null ? job.showName : "").setShot(job.shot)
                .setUser(job.user).setFacility(job.facilityName)
                .setGroup(job.groupId != null ? job.groupId : "").setState(job.state)
                .setPriority(job.priority).setMinCores(job.minCoreUnits / 100.0f)
                .setMaxCores(job.maxCoreUnits / 100.0f).setMinGpus(job.minGpuUnits)
                .setMaxGpus(job.maxGpuUnits).setIsPaused(job.isPaused).setAutoEat(job.isAutoEat)
                .setLogDir(job.logDir != null ? job.logDir : "")
                .setOs(job.os != null ? job.os : "");

        if (job.startTime > 0) {
            jobBuilder.setStartTime(job.startTime);
        }
        if (job.stopTime > 0) {
            jobBuilder.setStopTime(job.stopTime);
        }

        JobEvent.Builder builder = JobEvent.newBuilder().setHeader(header)
                .setJob(jobBuilder.build()).setPreviousState(previousState);

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

        // Build the embedded Job message (minimal fields)
        Job jobProto = Job.newBuilder().setId(job.getJobId()).setName(job.getName())
                .setState(job.state).setIsPaused(job.paused).setAutoEat(job.autoEat).build();

        return JobEvent.newBuilder().setHeader(header).setJob(jobProto)
                .setPreviousState(previousState).build();
    }

    /**
     * Builds a LayerEvent for a layer.
     */
    public LayerEvent buildLayerEvent(EventType eventType, LayerDetail layer, String jobName,
            String show) {
        EventHeader header = publisher.createEventHeader(eventType, layer.getJobId()).build();

        // Build the embedded Layer message
        Layer.Builder layerBuilder =
                Layer.newBuilder().setId(layer.getLayerId()).setName(layer.getName())
                        .setType(layer.type).setMinCores(layer.minimumCores / 100.0f)
                        .setMaxCores(layer.maximumCores / 100.0f).setMinGpus(layer.minimumGpus)
                        .setMaxGpus(layer.maximumGpus).setMinMemory(layer.minimumMemory)
                        .setMinGpuMemory(layer.minimumGpuMemory).setIsThreadable(layer.isThreadable)
                        .setChunkSize(layer.chunkSize).setTimeout(layer.timeout)
                        .setTimeoutLlu(layer.timeout_llu).setParentId(layer.getJobId());

        if (layer.tags != null && !layer.tags.isEmpty()) {
            layerBuilder.addAllTags(layer.tags);
        }
        if (layer.services != null && !layer.services.isEmpty()) {
            layerBuilder.addAllServices(layer.services);
        }
        if (layer.command != null) {
            layerBuilder.setCommand(layer.command);
        }

        return LayerEvent.newBuilder().setHeader(header).setLayer(layerBuilder.build())
                .setJobId(layer.getJobId()).setJobName(jobName).setShow(show).build();
    }

    /**
     * Builds a FrameEvent for a frame completion.
     */
    public FrameEvent buildFrameCompleteEvent(FrameCompleteReport report, FrameState newState,
            FrameState previousState, DispatchFrame frame, VirtualProc proc) {
        EventType eventType = determineFrameEventType(newState);
        EventHeader header = publisher.createEventHeader(eventType, frame.getJobId()).build();

        // Build the embedded Frame message
        Frame frameProto = Frame.newBuilder().setId(frame.getFrameId()).setName(frame.getName())
                .setLayerName(frame.layerName).setState(newState).setRetryCount(frame.retries)
                .setExitStatus(report.getExitStatus())
                .setStartTime((int) report.getFrame().getStartTime())
                .setStopTime((int) (System.currentTimeMillis() / 1000))
                .setMaxRss(report.getFrame().getMaxRss()).setUsedMemory(report.getFrame().getRss())
                .setMaxPss(report.getFrame().getMaxPss()).setUsedPss(report.getFrame().getPss())
                .setReservedMemory(proc.memoryReserved).setReservedGpuMemory(proc.gpuMemoryReserved)
                .setLluTime((int) report.getFrame().getLluTime())
                .setMaxGpuMemory(report.getFrame().getMaxUsedGpuMemory())
                .setUsedGpuMemory(report.getFrame().getUsedGpuMemory())
                .setLastResource(report.getFrame().getResourceId()).build();

        return FrameEvent.newBuilder().setHeader(header).setFrame(frameProto)
                .setLayerId(frame.getLayerId()).setJobId(frame.getJobId())
                .setJobName(report.getFrame().getJobName()).setShow(frame.show)
                .setPreviousState(previousState).setExitSignal(report.getExitSignal())
                .setRunTime(report.getRunTime()).setNumCores(report.getFrame().getNumCores())
                .setNumGpus(report.getFrame().getNumGpus()).setHostName(report.getHost().getName())
                .setResourceId(report.getFrame().getResourceId()).build();
    }

    /**
     * Builds a FrameEvent for a frame becoming dispatchable (DEPEND -> WAITING transition).
     */
    public FrameEvent buildFrameDispatchableEvent(FrameDetail frame) {
        EventHeader header =
                publisher.createEventHeader(EventType.FRAME_DISPATCHED, frame.getJobId()).build();

        // Build the embedded Frame message
        Frame frameProto = Frame.newBuilder().setId(frame.getFrameId()).setName(frame.getName())
                .setNumber(frame.number).setState(FrameState.WAITING)
                .setRetryCount(frame.retryCount).setDispatchOrder(frame.dispatchOrder).build();

        return FrameEvent.newBuilder().setHeader(header).setFrame(frameProto)
                .setLayerId(frame.getLayerId()).setJobId(frame.getJobId())
                .setPreviousState(FrameState.DEPEND).build();
    }

    /**
     * Builds a FrameEvent for a frame being started (WAITING -> RUNNING transition).
     */
    public FrameEvent buildFrameStartedEvent(DispatchFrame frame, VirtualProc proc) {
        EventHeader header =
                publisher.createEventHeader(EventType.FRAME_STARTED, frame.getJobId()).build();

        // Build the embedded Frame message
        Frame frameProto = Frame.newBuilder().setId(frame.getFrameId()).setName(frame.getName())
                .setLayerName(frame.layerName).setState(FrameState.RUNNING)
                .setRetryCount(frame.retries)
                .setStartTime((int) (System.currentTimeMillis() / 1000))
                .setReservedMemory(proc.memoryReserved).setReservedGpuMemory(proc.gpuMemoryReserved)
                .build();

        return FrameEvent.newBuilder().setHeader(header).setFrame(frameProto)
                .setLayerId(frame.getLayerId()).setJobId(frame.getJobId()).setJobName(frame.jobName)
                .setShow(frame.show).setPreviousState(frame.state)
                .setNumCores((int) (proc.coresReserved / 100.0f)).setNumGpus(proc.gpusReserved)
                .setHostName(proc.hostName).build();
    }

    /**
     * Builds a FrameEvent for a frame state change (not completion).
     */
    public FrameEvent buildFrameEvent(EventType eventType, FrameDetail frame, String jobName,
            String layerName, String show, FrameState previousState, String reason,
            String killedBy) {
        EventHeader header = publisher.createEventHeader(eventType, frame.getJobId()).build();

        // Build the embedded Frame message
        Frame.Builder frameBuilder = Frame.newBuilder().setId(frame.getFrameId())
                .setName(frame.getName()).setLayerName(layerName).setNumber(frame.number)
                .setState(frame.state).setRetryCount(frame.retryCount)
                .setExitStatus(frame.exitStatus).setDispatchOrder(frame.dispatchOrder);

        if (frame.dateStarted != null) {
            frameBuilder.setStartTime((int) (frame.dateStarted.getTime() / 1000));
        }
        if (frame.dateStopped != null) {
            frameBuilder.setStopTime((int) (frame.dateStopped.getTime() / 1000));
        }
        if (frame.maxRss > 0) {
            frameBuilder.setMaxRss(frame.maxRss);
        }
        if (frame.maxPss > 0) {
            frameBuilder.setMaxPss(frame.maxPss);
        }
        if (frame.lastResource != null) {
            frameBuilder.setLastResource(frame.lastResource);
        }

        FrameEvent.Builder builder =
                FrameEvent.newBuilder().setHeader(header).setFrame(frameBuilder.build())
                        .setLayerId(frame.getLayerId()).setJobId(frame.getJobId())
                        .setJobName(jobName).setShow(show).setPreviousState(previousState);

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

        // Build the embedded Host message
        Host.Builder hostBuilder = Host.newBuilder().setId(host.getHostId()).setName(host.getName())
                .setAllocName(host.getAllocationId() != null ? host.getAllocationId() : "")
                .setNimbyEnabled(host.isNimby).setCores(host.cores / 100.0f)
                .setIdleCores(host.idleCores / 100.0f).setMemory(host.memory)
                .setIdleMemory(host.idleMemory).setTotalMemory(host.memory).setGpus(host.gpus)
                .setIdleGpus(host.idleGpus).setGpuMemory(host.gpuMemory)
                .setIdleGpuMemory(host.idleGpuMemory).setTotalGpuMemory(host.gpuMemory)
                .setState(host.hardwareState).setLockState(host.lockState)
                .setThreadMode(threadMode);

        String[] osArray = host.getOs();
        if (osArray != null && osArray.length > 0) {
            hostBuilder.setOs(String.join(",", osArray));
        }
        if (host.tags != null) {
            hostBuilder.addAllTags(Arrays.asList(host.tags.split("\\|")));
        }

        HostEvent.Builder builder =
                HostEvent.newBuilder().setHeader(header).setHost(hostBuilder.build())
                        .setFacility(host.getFacilityId() != null ? host.getFacilityId() : "")
                        .setPreviousState(previousState).setPreviousLockState(previousLockState);

        if (reason != null) {
            builder.setReason(reason);
        }

        return builder.build();
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
