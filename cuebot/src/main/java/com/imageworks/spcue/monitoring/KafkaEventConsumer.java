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

import java.time.Duration;
import java.util.Arrays;
import java.util.Properties;
import java.util.concurrent.atomic.AtomicBoolean;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;

import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

/**
 * Kafka consumer that ingests monitoring events and stores them in Elasticsearch. Consumes from all
 * OpenCue event topics and routes to appropriate Elasticsearch indices.
 */
public class KafkaEventConsumer {
    private static final Logger logger = LogManager.getLogger(KafkaEventConsumer.class);

    // Kafka topic names - must match producer topics
    private static final String TOPIC_JOB_EVENTS = "opencue.job.events";
    private static final String TOPIC_LAYER_EVENTS = "opencue.layer.events";
    private static final String TOPIC_FRAME_EVENTS = "opencue.frame.events";
    private static final String TOPIC_HOST_EVENTS = "opencue.host.events";
    private static final String TOPIC_PROC_EVENTS = "opencue.proc.events";

    @Autowired
    private Environment env;

    private ElasticsearchClient elasticsearchClient;

    private KafkaConsumer<String, String> consumer;
    private Thread consumerThread;
    private AtomicBoolean running = new AtomicBoolean(false);
    private boolean enabled = false;

    @PostConstruct
    public void initialize() {
        // Consumer is only enabled if both Kafka and Elasticsearch are enabled
        boolean kafkaEnabled = env.getProperty("monitoring.kafka.enabled", Boolean.class, false);
        boolean esEnabled =
                env.getProperty("monitoring.elasticsearch.enabled", Boolean.class, false);
        enabled = kafkaEnabled && esEnabled;

        if (!enabled) {
            logger.info(
                    "Kafka event consumer is disabled (kafka.enabled={}, elasticsearch.enabled={})",
                    kafkaEnabled, esEnabled);
            return;
        }

        initializeConsumer();
        startConsumerThread();

        logger.info("Kafka event consumer initialized and started");
    }

    private void initializeConsumer() {
        Properties props = new Properties();

        String bootstrapServers =
                env.getProperty("monitoring.kafka.bootstrap.servers", "localhost:9092");
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);

        props.put(ConsumerConfig.GROUP_ID_CONFIG, env.getProperty(
                "monitoring.kafka.consumer.group.id", "opencue-elasticsearch-indexer"));

        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG,
                StringDeserializer.class.getName());

        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG,
                env.getProperty("monitoring.kafka.consumer.auto.offset.reset", "earliest"));
        props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, env
                .getProperty("monitoring.kafka.consumer.enable.auto.commit", Boolean.class, true));
        props.put(ConsumerConfig.AUTO_COMMIT_INTERVAL_MS_CONFIG, env.getProperty(
                "monitoring.kafka.consumer.auto.commit.interval.ms", Integer.class, 5000));
        props.put(ConsumerConfig.MAX_POLL_RECORDS_CONFIG,
                env.getProperty("monitoring.kafka.consumer.max.poll.records", Integer.class, 500));

        consumer = new KafkaConsumer<>(props);

        // Subscribe to all event topics
        consumer.subscribe(Arrays.asList(TOPIC_JOB_EVENTS, TOPIC_LAYER_EVENTS, TOPIC_FRAME_EVENTS,
                TOPIC_HOST_EVENTS, TOPIC_PROC_EVENTS));
    }

    private void startConsumerThread() {
        running.set(true);
        consumerThread = new Thread(this::consumeLoop, "KafkaEventConsumer");
        consumerThread.setDaemon(true);
        consumerThread.start();
    }

    private void consumeLoop() {
        try {
            while (running.get()) {
                ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(1000));

                for (ConsumerRecord<String, String> record : records) {
                    try {
                        processRecord(record);
                    } catch (Exception e) {
                        logger.warn("Error processing record from topic {}: {}", record.topic(),
                                e.getMessage());
                    }
                }
            }
        } catch (Exception e) {
            if (running.get()) {
                logger.error("Kafka consumer error: {}", e.getMessage());
            }
        } finally {
            consumer.close();
        }
    }

    private void processRecord(ConsumerRecord<String, String> record) {
        String topic = record.topic();
        String value = record.value();

        // Extract event ID from the JSON document
        String eventId = extractEventId(value);
        if (eventId == null) {
            eventId = record.key(); // Fallback to record key
        }

        // Route to appropriate Elasticsearch index based on topic
        switch (topic) {
            case TOPIC_JOB_EVENTS:
                elasticsearchClient.indexJobEvent(eventId, value);
                break;
            case TOPIC_LAYER_EVENTS:
                elasticsearchClient.indexLayerEvent(eventId, value);
                break;
            case TOPIC_FRAME_EVENTS:
                elasticsearchClient.indexFrameEvent(eventId, value);
                break;
            case TOPIC_HOST_EVENTS:
                elasticsearchClient.indexHostEvent(eventId, value);
                break;
            case TOPIC_PROC_EVENTS:
                elasticsearchClient.indexProcEvent(eventId, value);
                break;
            default:
                logger.warn("Unknown topic: {}", topic);
        }
    }

    private String extractEventId(String jsonDocument) {
        try {
            JsonObject json = JsonParser.parseString(jsonDocument).getAsJsonObject();
            if (json.has("header")) {
                JsonObject header = json.getAsJsonObject("header");
                if (header.has("eventId")) {
                    return header.get("eventId").getAsString();
                }
            }
        } catch (Exception e) {
            // Ignore parsing errors
        }
        return null;
    }

    @PreDestroy
    public void shutdown() {
        running.set(false);

        if (consumerThread != null) {
            consumerThread.interrupt();
            try {
                consumerThread.join(5000);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }

        logger.info("Kafka event consumer shut down");
    }

    /**
     * Returns true if the consumer is enabled and running.
     */
    public boolean isRunning() {
        return enabled && running.get();
    }

    public ElasticsearchClient getElasticsearchClient() {
        return elasticsearchClient;
    }

    public void setElasticsearchClient(ElasticsearchClient elasticsearchClient) {
        this.elasticsearchClient = elasticsearchClient;
    }
}
