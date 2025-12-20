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

import java.net.InetAddress;
import java.net.UnknownHostException;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.UUID;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;

import org.apache.kafka.clients.admin.AdminClient;
import org.apache.kafka.clients.admin.AdminClientConfig;
import org.apache.kafka.clients.admin.CreateTopicsResult;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.errors.TopicExistsException;
import org.apache.kafka.common.serialization.StringSerializer;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;

import com.google.protobuf.Message;
import com.google.protobuf.util.JsonFormat;
import com.imageworks.spcue.grpc.monitoring.EventHeader;
import com.imageworks.spcue.grpc.monitoring.EventType;
import com.imageworks.spcue.grpc.monitoring.FrameEvent;
import com.imageworks.spcue.grpc.monitoring.HostEvent;
import com.imageworks.spcue.grpc.monitoring.JobEvent;
import com.imageworks.spcue.grpc.monitoring.LayerEvent;
import com.imageworks.spcue.grpc.monitoring.ProcEvent;
import com.imageworks.spcue.util.CueExceptionUtil;

/**
 * KafkaEventPublisher publishes monitoring events to Kafka topics for downstream processing. Events
 * are serialized as JSON for compatibility with Elasticsearch and other consumers.
 *
 * This service is the central point for all monitoring event publishing in Cuebot. Events are
 * queued and published asynchronously to avoid blocking the main dispatch threads.
 */
public class KafkaEventPublisher extends ThreadPoolExecutor {
    private static final Logger logger = LogManager.getLogger(KafkaEventPublisher.class);

    // Thread pool configuration
    private static final int THREAD_POOL_SIZE_INITIAL = 2;
    private static final int THREAD_POOL_SIZE_MAX = 4;
    private static final int QUEUE_SIZE = 5000;

    // Kafka topic names
    private static final String TOPIC_JOB_EVENTS = "opencue.job.events";
    private static final String TOPIC_LAYER_EVENTS = "opencue.layer.events";
    private static final String TOPIC_FRAME_EVENTS = "opencue.frame.events";
    private static final String TOPIC_HOST_EVENTS = "opencue.host.events";
    private static final String TOPIC_PROC_EVENTS = "opencue.proc.events";

    // All topics managed by this publisher
    private static final List<String> ALL_TOPICS = Arrays.asList(TOPIC_JOB_EVENTS,
            TOPIC_LAYER_EVENTS, TOPIC_FRAME_EVENTS, TOPIC_HOST_EVENTS, TOPIC_PROC_EVENTS);

    // Default topic configuration
    private static final int DEFAULT_NUM_PARTITIONS = 3;
    private static final short DEFAULT_REPLICATION_FACTOR = 1;
    private static final String DEFAULT_RETENTION_MS = "604800000"; // 7 days
    private static final String DEFAULT_CLEANUP_POLICY = "delete";
    private static final String DEFAULT_SEGMENT_MS = "86400000"; // 1 day
    private static final String DEFAULT_SEGMENT_BYTES = "1073741824"; // 1GB

    @Autowired
    private Environment env;

    private KafkaProducer<String, String> producer;
    private AdminClient adminClient;
    private JsonFormat.Printer jsonPrinter;
    private String sourceCuebot;
    private String bootstrapServers;
    private boolean enabled = false;

    public KafkaEventPublisher() {
        super(THREAD_POOL_SIZE_INITIAL, THREAD_POOL_SIZE_MAX, 10, TimeUnit.SECONDS,
                new LinkedBlockingQueue<Runnable>(QUEUE_SIZE));
    }

    @PostConstruct
    public void initialize() {
        enabled = env.getProperty("monitoring.kafka.enabled", Boolean.class, false);

        if (!enabled) {
            logger.info("Kafka event publishing is disabled");
            return;
        }

        try {
            sourceCuebot = InetAddress.getLocalHost().getHostName();
        } catch (UnknownHostException e) {
            sourceCuebot = "unknown";
        }

        bootstrapServers = env.getProperty("monitoring.kafka.bootstrap.servers", "localhost:9092");

        jsonPrinter =
                JsonFormat.printer().includingDefaultValueFields().preservingProtoFieldNames();

        // Initialize admin client and create topics before starting the producer
        initializeAdminClient();
        createTopics();
        initializeKafkaProducer();

        logger.info("Kafka event publishing initialized, source cuebot: {}", sourceCuebot);
    }

    private void initializeAdminClient() {
        Properties props = new Properties();
        props.put(AdminClientConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(AdminClientConfig.REQUEST_TIMEOUT_MS_CONFIG,
                env.getProperty("monitoring.kafka.admin.timeout.ms", Integer.class, 30000));
        adminClient = AdminClient.create(props);
        logger.info("Kafka AdminClient initialized");
    }

    /**
     * Creates all monitoring topics with proper configuration. Topics that already exist are
     * skipped.
     */
    private void createTopics() {
        int numPartitions = env.getProperty("monitoring.kafka.topic.partitions", Integer.class,
                DEFAULT_NUM_PARTITIONS);
        short replicationFactor = env.getProperty("monitoring.kafka.topic.replication.factor",
                Short.class, DEFAULT_REPLICATION_FACTOR);
        String retentionMs =
                env.getProperty("monitoring.kafka.topic.retention.ms", DEFAULT_RETENTION_MS);
        String cleanupPolicy =
                env.getProperty("monitoring.kafka.topic.cleanup.policy", DEFAULT_CLEANUP_POLICY);
        String segmentMs = env.getProperty("monitoring.kafka.topic.segment.ms", DEFAULT_SEGMENT_MS);
        String segmentBytes =
                env.getProperty("monitoring.kafka.topic.segment.bytes", DEFAULT_SEGMENT_BYTES);

        // Topic configuration
        Map<String, String> topicConfig = new HashMap<>();
        topicConfig.put("retention.ms", retentionMs);
        topicConfig.put("cleanup.policy", cleanupPolicy);
        topicConfig.put("segment.ms", segmentMs);
        topicConfig.put("segment.bytes", segmentBytes);

        for (String topicName : ALL_TOPICS) {
            createTopic(topicName, numPartitions, replicationFactor, topicConfig);
        }
    }

    /**
     * Creates a single topic with the specified configuration.
     */
    private void createTopic(String topicName, int numPartitions, short replicationFactor,
            Map<String, String> config) {
        NewTopic newTopic = new NewTopic(topicName, numPartitions, replicationFactor);
        newTopic.configs(config);

        CreateTopicsResult result = adminClient.createTopics(Collections.singletonList(newTopic));

        try {
            result.values().get(topicName).get();
            logger.info("Topic '{}' created successfully with {} partitions, replication={}",
                    topicName, numPartitions, replicationFactor);
        } catch (ExecutionException e) {
            if (e.getCause() instanceof TopicExistsException) {
                logger.info("Topic '{}' already exists", topicName);
            } else {
                logger.error("Failed to create topic '{}': {}", topicName, e.getMessage());
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            logger.error("Interrupted while creating topic '{}': {}", topicName, e.getMessage());
        }
    }

    private void initializeKafkaProducer() {
        Properties props = new Properties();

        // Kafka broker configuration
        props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);

        // Serialization
        props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());

        // Producer configuration for reliability
        props.put(ProducerConfig.ACKS_CONFIG, env.getProperty("monitoring.kafka.acks", "1"));
        props.put(ProducerConfig.RETRIES_CONFIG,
                env.getProperty("monitoring.kafka.retries", Integer.class, 3));
        props.put(ProducerConfig.BATCH_SIZE_CONFIG,
                env.getProperty("monitoring.kafka.batch.size", Integer.class, 16384));
        props.put(ProducerConfig.LINGER_MS_CONFIG,
                env.getProperty("monitoring.kafka.linger.ms", Integer.class, 10));
        props.put(ProducerConfig.BUFFER_MEMORY_CONFIG,
                env.getProperty("monitoring.kafka.buffer.memory", Long.class, 33554432L));

        // Compression
        props.put(ProducerConfig.COMPRESSION_TYPE_CONFIG,
                env.getProperty("monitoring.kafka.compression.type", "lz4"));

        // Client ID
        props.put(ProducerConfig.CLIENT_ID_CONFIG, "cuebot-" + sourceCuebot);

        producer = new KafkaProducer<>(props);
    }

    @PreDestroy
    public void shutdown() {
        if (producer != null) {
            producer.flush();
            producer.close();
        }
        if (adminClient != null) {
            adminClient.close();
        }
        shutdownNow();
        logger.info("Kafka event publisher shut down");
    }

    /**
     * Creates a standard event header with common fields populated.
     */
    public EventHeader.Builder createEventHeader(EventType eventType) {
        return EventHeader.newBuilder().setEventId(UUID.randomUUID().toString())
                .setEventType(eventType).setTimestamp(System.currentTimeMillis())
                .setSourceCuebot(sourceCuebot);
    }

    /**
     * Creates an event header with a correlation ID for tracing related events.
     */
    public EventHeader.Builder createEventHeader(EventType eventType, String correlationId) {
        return createEventHeader(eventType).setCorrelationId(correlationId);
    }

    /**
     * Publishes a job event to Kafka.
     */
    public void publishJobEvent(JobEvent event) {
        if (!enabled)
            return;
        publishEvent(TOPIC_JOB_EVENTS, event.getJob().getId(), event,
                event.getHeader().getEventType().name());
    }

    /**
     * Publishes a layer event to Kafka.
     */
    public void publishLayerEvent(LayerEvent event) {
        if (!enabled)
            return;
        publishEvent(TOPIC_LAYER_EVENTS, event.getLayer().getId(), event,
                event.getHeader().getEventType().name());
    }

    /**
     * Publishes a frame event to Kafka.
     */
    public void publishFrameEvent(FrameEvent event) {
        if (!enabled)
            return;
        publishEvent(TOPIC_FRAME_EVENTS, event.getFrame().getId(), event,
                event.getHeader().getEventType().name());
    }

    /**
     * Publishes a host event to Kafka.
     */
    public void publishHostEvent(HostEvent event) {
        if (!enabled)
            return;
        publishEvent(TOPIC_HOST_EVENTS, event.getHost().getName(), event,
                event.getHeader().getEventType().name());
    }

    /**
     * Publishes a proc event to Kafka.
     */
    public void publishProcEvent(ProcEvent event) {
        if (!enabled)
            return;
        publishEvent(TOPIC_PROC_EVENTS, event.getProcId(), event,
                event.getHeader().getEventType().name());
    }

    /**
     * Internal method to publish any protobuf message to a Kafka topic.
     */
    private void publishEvent(String topic, String key, Message event, String eventType) {
        try {
            execute(() -> {
                try {
                    String jsonValue = jsonPrinter.print(event);
                    ProducerRecord<String, String> record =
                            new ProducerRecord<>(topic, key, jsonValue);

                    producer.send(record, (metadata, exception) -> {
                        if (exception != null) {
                            logger.warn("Failed to publish event to topic {}: {}", topic,
                                    exception.getMessage());
                        } else {
                            logger.trace("Published event to {}, partition={}, offset={}", topic,
                                    metadata.partition(), metadata.offset());
                        }
                    });
                } catch (Exception e) {
                    logger.warn("Error serializing event for topic {}: {}", topic, e.getMessage());
                    CueExceptionUtil.logStackTrace("KafkaEventPublisher error", e);
                }
            });
        } catch (RejectedExecutionException e) {
            logger.warn("Event queue is full, dropping event for topic {}", topic);
        }
    }

    /**
     * Returns true if Kafka event publishing is enabled.
     */
    public boolean isEnabled() {
        return enabled;
    }

    /**
     * Returns the name of this cuebot instance for event attribution.
     */
    public String getSourceCuebot() {
        return sourceCuebot;
    }

    /**
     * Returns the number of pending events in the queue.
     */
    public int getPendingEventCount() {
        return getQueue().size();
    }
}
