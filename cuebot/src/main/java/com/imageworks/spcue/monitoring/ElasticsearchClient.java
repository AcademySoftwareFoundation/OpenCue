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

import java.io.IOException;
import java.io.StringReader;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;

import org.apache.http.HttpHost;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.elasticsearch.client.RestClient;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;

import co.elastic.clients.elasticsearch.core.IndexRequest;
import co.elastic.clients.elasticsearch.core.IndexResponse;
import co.elastic.clients.json.JsonData;
import co.elastic.clients.json.jackson.JacksonJsonpMapper;
import co.elastic.clients.transport.ElasticsearchTransport;
import co.elastic.clients.transport.rest_client.RestClientTransport;

/**
 * Elasticsearch client for storing historical monitoring data. Provides methods to index job,
 * layer, frame, and host events for long-term storage and analysis.
 */
public class ElasticsearchClient {
    private static final Logger logger = LogManager.getLogger(ElasticsearchClient.class);

    private static final int THREAD_POOL_SIZE = 4;
    private static final int QUEUE_SIZE = 10000;

    // Index name prefixes
    private static final String INDEX_JOB_EVENTS = "opencue-job-events";
    private static final String INDEX_LAYER_EVENTS = "opencue-layer-events";
    private static final String INDEX_FRAME_EVENTS = "opencue-frame-events";
    private static final String INDEX_HOST_EVENTS = "opencue-host-events";
    private static final String INDEX_HOST_REPORTS = "opencue-host-reports";
    private static final String INDEX_PROC_EVENTS = "opencue-proc-events";

    @Autowired
    private Environment env;

    private RestClient restClient;
    private ElasticsearchTransport transport;
    private co.elastic.clients.elasticsearch.ElasticsearchClient esClient;
    private ThreadPoolExecutor indexingPool;
    private boolean enabled = false;
    private DateTimeFormatter indexDateFormatter = DateTimeFormatter.ofPattern("yyyy.MM.dd");

    @PostConstruct
    public void initialize() {
        enabled = env.getProperty("monitoring.elasticsearch.enabled", Boolean.class, false);

        if (!enabled) {
            logger.info("Elasticsearch storage is disabled");
            return;
        }

        initializeClient();
        initializeThreadPool();

        logger.info("Elasticsearch client initialized");
    }

    private void initializeClient() {
        String host = env.getProperty("monitoring.elasticsearch.host", "localhost");
        int port = env.getProperty("monitoring.elasticsearch.port", Integer.class, 9200);
        String scheme = env.getProperty("monitoring.elasticsearch.scheme", "http");

        restClient = RestClient.builder(new HttpHost(host, port, scheme)).build();
        transport = new RestClientTransport(restClient, new JacksonJsonpMapper());
        esClient = new co.elastic.clients.elasticsearch.ElasticsearchClient(transport);
    }

    private void initializeThreadPool() {
        indexingPool = new ThreadPoolExecutor(THREAD_POOL_SIZE, THREAD_POOL_SIZE, 60L,
                TimeUnit.SECONDS, new LinkedBlockingQueue<>(QUEUE_SIZE));
    }

    @PreDestroy
    public void shutdown() {
        if (indexingPool != null) {
            indexingPool.shutdown();
            try {
                if (!indexingPool.awaitTermination(30, TimeUnit.SECONDS)) {
                    indexingPool.shutdownNow();
                }
            } catch (InterruptedException e) {
                indexingPool.shutdownNow();
                Thread.currentThread().interrupt();
            }
        }

        if (transport != null) {
            try {
                transport.close();
            } catch (IOException e) {
                logger.warn("Error closing Elasticsearch transport: {}", e.getMessage());
            }
        }

        if (restClient != null) {
            try {
                restClient.close();
            } catch (IOException e) {
                logger.warn("Error closing Elasticsearch rest client: {}", e.getMessage());
            }
        }

        logger.info("Elasticsearch client shut down");
    }

    /**
     * Indexes a job event document.
     */
    public void indexJobEvent(String eventId, String jsonDocument) {
        if (!enabled)
            return;
        indexDocument(INDEX_JOB_EVENTS, eventId, jsonDocument);
    }

    /**
     * Indexes a layer event document.
     */
    public void indexLayerEvent(String eventId, String jsonDocument) {
        if (!enabled)
            return;
        indexDocument(INDEX_LAYER_EVENTS, eventId, jsonDocument);
    }

    /**
     * Indexes a frame event document.
     */
    public void indexFrameEvent(String eventId, String jsonDocument) {
        if (!enabled)
            return;
        indexDocument(INDEX_FRAME_EVENTS, eventId, jsonDocument);
    }

    /**
     * Indexes a host event document.
     */
    public void indexHostEvent(String eventId, String jsonDocument) {
        if (!enabled)
            return;
        indexDocument(INDEX_HOST_EVENTS, eventId, jsonDocument);
    }

    /**
     * Indexes a host report document.
     */
    public void indexHostReport(String eventId, String jsonDocument) {
        if (!enabled)
            return;
        indexDocument(INDEX_HOST_REPORTS, eventId, jsonDocument);
    }

    /**
     * Indexes a proc event document.
     */
    public void indexProcEvent(String eventId, String jsonDocument) {
        if (!enabled)
            return;
        indexDocument(INDEX_PROC_EVENTS, eventId, jsonDocument);
    }

    /**
     * Internal method to index a document with daily index rotation.
     */
    private void indexDocument(String indexPrefix, String documentId, String jsonDocument) {
        if (indexingPool.getQueue().remainingCapacity() == 0) {
            logger.warn("Elasticsearch indexing queue is full, dropping document for index {}",
                    indexPrefix);
            return;
        }

        indexingPool.execute(() -> {
            try {
                // Use daily index pattern for time-based data
                String indexName = indexPrefix + "-" + LocalDate.now().format(indexDateFormatter);

                // Parse JSON string into JsonData using the mapper's parser
                jakarta.json.stream.JsonParser parser = esClient._jsonpMapper().jsonProvider()
                        .createParser(new StringReader(jsonDocument));
                JsonData document = JsonData.from(parser, esClient._jsonpMapper());

                IndexRequest<JsonData> request = IndexRequest
                        .of(builder -> builder.index(indexName).id(documentId).document(document));

                IndexResponse response = esClient.index(request);
                logger.trace("Indexed document {} to index {}, result: {}", documentId, indexName,
                        response.result());

            } catch (Exception e) {
                logger.warn("Failed to index document to {}: {}", indexPrefix, e.getMessage());
            }
        });
    }

    /**
     * Returns true if Elasticsearch storage is enabled.
     */
    public boolean isEnabled() {
        return enabled;
    }

    /**
     * Returns the number of pending indexing operations.
     */
    public int getPendingIndexCount() {
        return indexingPool != null ? indexingPool.getQueue().size() : 0;
    }
}
