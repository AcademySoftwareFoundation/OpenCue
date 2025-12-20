
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

package com.imageworks.spcue.test.monitoring;

import org.junit.Before;
import org.junit.Test;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.monitoring.EventHeader;
import com.imageworks.spcue.grpc.monitoring.EventType;
import com.imageworks.spcue.grpc.monitoring.FrameEvent;
import com.imageworks.spcue.monitoring.KafkaEventPublisher;
import com.imageworks.spcue.monitoring.MonitoringEventBuilder;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

/**
 * Unit tests for MonitoringEventBuilder, specifically testing the pickup time tracking events: -
 * FRAME_STARTED (WAITING -> RUNNING transition) - FRAME_DISPATCHED (DEPEND -> WAITING transition)
 */
public class MonitoringEventBuilderTests {

    private MonitoringEventBuilder eventBuilder;
    private TestKafkaEventPublisher testPublisher;

    /**
     * A test implementation of KafkaEventPublisher that provides event headers without requiring
     * actual Kafka connectivity.
     */
    private static class TestKafkaEventPublisher extends KafkaEventPublisher {
        private final String sourceCuebot = "test-cuebot";

        @Override
        public EventHeader.Builder createEventHeader(EventType eventType) {
            return EventHeader.newBuilder().setEventId("test-event-id").setEventType(eventType)
                    .setTimestamp(System.currentTimeMillis()).setSourceCuebot(sourceCuebot);
        }

        @Override
        public EventHeader.Builder createEventHeader(EventType eventType, String correlationId) {
            return createEventHeader(eventType).setCorrelationId(correlationId);
        }

        @Override
        public boolean isEnabled() {
            return false; // Disabled for testing - we don't want to publish to real Kafka
        }
    }

    @Before
    public void setUp() {
        testPublisher = new TestKafkaEventPublisher();
        eventBuilder = new MonitoringEventBuilder(testPublisher);
    }

    /**
     * Test buildFrameStartedEvent for WAITING -> RUNNING transition. This event is used to
     * calculate pickup time (time from ready to dispatch).
     */
    @Test
    public void testBuildFrameStartedEvent() {
        // Setup test data
        DispatchFrame frame = createTestDispatchFrame();
        VirtualProc proc = createTestVirtualProc();

        // Build the event
        FrameEvent event = eventBuilder.buildFrameStartedEvent(frame, proc);

        // Verify the event
        assertNotNull("Event should not be null", event);
        assertNotNull("Event header should not be null", event.getHeader());
        assertEquals("Event type should be FRAME_STARTED", EventType.FRAME_STARTED,
                event.getHeader().getEventType());

        // Verify embedded frame fields (now using composition)
        assertNotNull("Embedded frame should not be null", event.getFrame());
        assertEquals("test-frame-id", event.getFrame().getId());
        assertEquals("0001-test_layer", event.getFrame().getName());
        assertEquals("test_layer", event.getFrame().getLayerName());

        // Verify context fields (still on event level)
        assertEquals("test-layer-id", event.getLayerId());
        assertEquals("test-job-id", event.getJobId());
        assertEquals("test-job-name", event.getJobName());
        assertEquals("testing", event.getShow());

        // Verify state transition
        assertEquals("State should be RUNNING", FrameState.RUNNING, event.getFrame().getState());
        assertEquals("Previous state should be WAITING", FrameState.WAITING,
                event.getPreviousState());

        // Verify proc fields
        assertEquals("test-host", event.getHostName());
        assertEquals(1, event.getNumCores());
        assertEquals(0, event.getNumGpus());
        assertTrue("Start time should be set", event.getFrame().getStartTime() > 0);
    }

    /**
     * Test buildFrameDispatchableEvent for DEPEND -> WAITING transition. This event marks when a
     * frame becomes ready for dispatch after dependencies are satisfied.
     */
    @Test
    public void testBuildFrameDispatchableEvent() {
        // Setup test data
        FrameDetail frame = createTestFrameDetail();

        // Build the event
        FrameEvent event = eventBuilder.buildFrameDispatchableEvent(frame);

        // Verify the event
        assertNotNull("Event should not be null", event);
        assertNotNull("Event header should not be null", event.getHeader());
        assertEquals("Event type should be FRAME_DISPATCHED", EventType.FRAME_DISPATCHED,
                event.getHeader().getEventType());

        // Verify embedded frame fields (now using composition)
        assertNotNull("Embedded frame should not be null", event.getFrame());
        assertEquals("test-frame-id", event.getFrame().getId());
        assertEquals("0001-test_layer", event.getFrame().getName());
        assertEquals(1, event.getFrame().getNumber());

        // Verify context fields (still on event level)
        assertEquals("test-layer-id", event.getLayerId());
        assertEquals("test-job-id", event.getJobId());

        // Verify state transition
        assertEquals("State should be WAITING", FrameState.WAITING, event.getFrame().getState());
        assertEquals("Previous state should be DEPEND", FrameState.DEPEND,
                event.getPreviousState());

        // Verify other fields (now in embedded frame)
        assertEquals(0, event.getFrame().getRetryCount());
        assertEquals(1, event.getFrame().getDispatchOrder());
    }

    /**
     * Test that FRAME_STARTED event includes reserved resources from the proc.
     */
    @Test
    public void testBuildFrameStartedEventIncludesResources() {
        DispatchFrame frame = createTestDispatchFrame();
        VirtualProc proc = createTestVirtualProc();
        proc.memoryReserved = 4194304; // 4GB
        proc.gpuMemoryReserved = 2097152; // 2GB
        proc.coresReserved = 200; // 2 cores
        proc.gpusReserved = 1;

        FrameEvent event = eventBuilder.buildFrameStartedEvent(frame, proc);

        // Reserved memory is now in the embedded Frame
        assertEquals("Reserved memory should match", 4194304, event.getFrame().getReservedMemory());
        assertEquals("Reserved GPU memory should match", 2097152,
                event.getFrame().getReservedGpuMemory());
        // Num cores and GPUs are still on event level (resource allocation info)
        assertEquals("Num cores should be calculated from coresReserved/100", 2,
                event.getNumCores());
        assertEquals("Num GPUs should match", 1, event.getNumGpus());
    }

    /**
     * Test that events maintain correct correlation ID for tracing.
     */
    @Test
    public void testEventCorrelationId() {
        DispatchFrame frame = createTestDispatchFrame();
        VirtualProc proc = createTestVirtualProc();

        FrameEvent event = eventBuilder.buildFrameStartedEvent(frame, proc);

        assertEquals("Correlation ID should be the job ID", "test-job-id",
                event.getHeader().getCorrelationId());
    }

    /**
     * Test building event with retry count.
     */
    @Test
    public void testBuildFrameStartedEventWithRetries() {
        DispatchFrame frame = createTestDispatchFrame();
        frame.retries = 3;
        VirtualProc proc = createTestVirtualProc();

        FrameEvent event = eventBuilder.buildFrameStartedEvent(frame, proc);

        // Retry count is now in the embedded Frame
        assertEquals("Retry count should be included", 3, event.getFrame().getRetryCount());
    }

    // Helper methods to create test objects

    private DispatchFrame createTestDispatchFrame() {
        DispatchFrame frame = new DispatchFrame();
        frame.id = "test-frame-id";
        frame.name = "0001-test_layer";
        frame.layerId = "test-layer-id";
        frame.layerName = "test_layer";
        frame.jobId = "test-job-id";
        frame.jobName = "test-job-name";
        frame.show = "testing";
        frame.state = FrameState.WAITING;
        frame.retries = 0;
        return frame;
    }

    private FrameDetail createTestFrameDetail() {
        FrameDetail frame = new FrameDetail();
        frame.id = "test-frame-id";
        frame.name = "0001-test_layer";
        frame.number = 1;
        frame.layerId = "test-layer-id";
        frame.jobId = "test-job-id";
        frame.state = FrameState.WAITING;
        frame.retryCount = 0;
        frame.dispatchOrder = 1;
        return frame;
    }

    private VirtualProc createTestVirtualProc() {
        VirtualProc proc = new VirtualProc();
        proc.id = "test-proc-id";
        proc.hostName = "test-host";
        proc.coresReserved = 100; // 1 core
        proc.gpusReserved = 0;
        proc.memoryReserved = 3355443;
        proc.gpuMemoryReserved = 0;
        return proc;
    }
}
