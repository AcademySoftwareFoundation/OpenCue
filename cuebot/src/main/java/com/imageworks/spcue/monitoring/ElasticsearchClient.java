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
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
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

import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.grpc.job.LayerType;
import com.imageworks.spcue.grpc.monitoring.HistoricalFrame;
import com.imageworks.spcue.grpc.monitoring.HistoricalJob;
import com.imageworks.spcue.grpc.monitoring.HistoricalLayer;
import com.imageworks.spcue.grpc.monitoring.LayerMemoryRecord;

import co.elastic.clients.elasticsearch._types.FieldValue;
import co.elastic.clients.elasticsearch._types.SortOrder;
import co.elastic.clients.elasticsearch._types.query_dsl.BoolQuery;
import co.elastic.clients.elasticsearch._types.query_dsl.Query;
import co.elastic.clients.elasticsearch.core.IndexRequest;
import co.elastic.clients.elasticsearch.core.IndexResponse;
import co.elastic.clients.elasticsearch.core.SearchRequest;
import co.elastic.clients.elasticsearch.core.SearchResponse;
import co.elastic.clients.elasticsearch.core.search.Hit;
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
        createIndexTemplates();

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

    /**
     * Creates index templates with proper field mappings to ensure timestamp fields are mapped as
     * date type instead of text.
     */
    private void createIndexTemplates() {
        String[] indexPrefixes = {INDEX_JOB_EVENTS, INDEX_LAYER_EVENTS, INDEX_FRAME_EVENTS,
                INDEX_HOST_EVENTS, INDEX_HOST_REPORTS, INDEX_PROC_EVENTS};

        for (String prefix : indexPrefixes) {
            try {
                String templateName = prefix.replace("-", "_") + "_template";

                // Check if template already exists
                boolean templateExists =
                        esClient.indices().existsIndexTemplate(r -> r.name(templateName)).value();

                if (!templateExists) {
                    esClient.indices().putIndexTemplate(t -> t.name(templateName)
                            .indexPatterns(List.of(prefix + "-*")).priority(100)
                            .template(template -> template.mappings(m -> m
                                    // Map header.timestamp as date with epoch_millis format
                                    .properties("header",
                                            p -> p.object(o -> o
                                                    .properties("timestamp",
                                                            tp -> tp.date(
                                                                    d -> d.format("epoch_millis")))
                                                    .properties("event_type",
                                                            ep -> ep.keyword(k -> k))
                                                    .properties("event_id",
                                                            ep -> ep.keyword(k -> k))
                                                    .properties("source_cuebot",
                                                            ep -> ep.keyword(k -> k))
                                                    .properties("correlation_id",
                                                            ep -> ep.keyword(k -> k))))
                                    // Map common fields as keywords for proper aggregation
                                    .properties("job_id", p -> p.keyword(k -> k))
                                    .properties("job_name", p -> p.keyword(k -> k))
                                    .properties("layer_id", p -> p.keyword(k -> k))
                                    .properties("layer_name", p -> p.keyword(k -> k))
                                    .properties("show", p -> p.keyword(k -> k))
                                    .properties("host_name", p -> p.keyword(k -> k))
                                    .properties("previous_state", p -> p.keyword(k -> k)))));

                    logger.info("Created index template: {}", templateName);
                } else {
                    logger.debug("Index template already exists: {}", templateName);
                }
            } catch (Exception e) {
                logger.warn("Failed to create index template for {}: {}", prefix, e.getMessage());
            }
        }
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

    // -------- Query Methods --------

    /**
     * Searches for historical job events.
     */
    @SuppressWarnings({"rawtypes", "unchecked"})
    public List<HistoricalJob> searchJobHistory(List<String> shows, List<String> users,
            List<String> shots, List<String> jobNameRegex, List<JobState> states, long startTime,
            long endTime, int page, int pageSize, int maxResults) {
        if (!enabled || esClient == null) {
            return Collections.emptyList();
        }

        try {
            BoolQuery.Builder boolQuery = new BoolQuery.Builder();

            // Filter by event type (job finished/killed)
            boolQuery.must(Query.of(q -> q.terms(t -> t.field("header.eventType").terms(v -> v
                    .value(List.of(FieldValue.of("JOB_FINISHED"), FieldValue.of("JOB_KILLED")))))));

            // Time range filter
            if (startTime > 0 || endTime > 0) {
                boolQuery.must(Query.of(q -> q.range(r -> {
                    r.field("header.timestamp");
                    if (startTime > 0)
                        r.gte(JsonData.of(startTime));
                    if (endTime > 0)
                        r.lte(JsonData.of(endTime));
                    return r;
                })));
            }

            // Filter by shows
            if (shows != null && !shows.isEmpty()) {
                List<FieldValue> showValues = shows.stream().map(FieldValue::of)
                        .collect(java.util.stream.Collectors.toList());
                boolQuery.must(Query
                        .of(q -> q.terms(t -> t.field("show").terms(v -> v.value(showValues)))));
            }

            // Filter by users
            if (users != null && !users.isEmpty()) {
                List<FieldValue> userValues = users.stream().map(FieldValue::of)
                        .collect(java.util.stream.Collectors.toList());
                boolQuery.must(Query
                        .of(q -> q.terms(t -> t.field("user").terms(v -> v.value(userValues)))));
            }

            // Filter by shots
            if (shots != null && !shots.isEmpty()) {
                List<FieldValue> shotValues = shots.stream().map(FieldValue::of)
                        .collect(java.util.stream.Collectors.toList());
                boolQuery.must(Query
                        .of(q -> q.terms(t -> t.field("shot").terms(v -> v.value(shotValues)))));
            }

            // Filter by job name regex
            if (jobNameRegex != null && !jobNameRegex.isEmpty()) {
                for (String regex : jobNameRegex) {
                    boolQuery.must(Query.of(q -> q.regexp(r -> r.field("jobName").value(regex))));
                }
            }

            // Filter by states
            if (states != null && !states.isEmpty()) {
                List<FieldValue> stateValues = states.stream().map(s -> FieldValue.of(s.name()))
                        .collect(java.util.stream.Collectors.toList());
                boolQuery.must(Query
                        .of(q -> q.terms(t -> t.field("state").terms(v -> v.value(stateValues)))));
            }

            int size = Math.min(pageSize > 0 ? pageSize : 100, maxResults > 0 ? maxResults : 1000);
            int from = page > 0 ? (page - 1) * size : 0;

            SearchRequest request = SearchRequest.of(s -> s.index(INDEX_JOB_EVENTS + "-*")
                    .query(Query.of(q -> q.bool(boolQuery.build()))).from(from).size(size)
                    .sort(sort -> sort
                            .field(f -> f.field("header.timestamp").order(SortOrder.Desc))));

            SearchResponse<Map> response = esClient.search(request, Map.class);

            List<HistoricalJob> results = new ArrayList<>();
            for (Hit<Map> hit : response.hits().hits()) {
                Map<String, Object> source = hit.source();
                if (source != null) {
                    results.add(mapToHistoricalJob(source));
                }
            }

            return results;
        } catch (Exception e) {
            logger.warn("Failed to search job history: {}", e.getMessage());
            return Collections.emptyList();
        }
    }

    /**
     * Searches for historical frame events.
     */
    @SuppressWarnings({"rawtypes", "unchecked"})
    public List<HistoricalFrame> searchFrameHistory(String jobId, String jobName,
            List<String> layerNames, List<FrameState> states, long startTime, long endTime,
            int page, int pageSize) {
        if (!enabled || esClient == null) {
            return Collections.emptyList();
        }

        try {
            BoolQuery.Builder boolQuery = new BoolQuery.Builder();

            // Filter by event type (frame completed/failed/eaten)
            boolQuery
                    .must(Query.of(q -> q.terms(t -> t.field("header.eventType")
                            .terms(v -> v.value(List.of(FieldValue.of("FRAME_COMPLETED"),
                                    FieldValue.of("FRAME_FAILED"),
                                    FieldValue.of("FRAME_EATEN")))))));

            // Filter by job
            if (jobId != null && !jobId.isEmpty()) {
                boolQuery.must(Query.of(q -> q.term(t -> t.field("jobId").value(jobId))));
            }
            if (jobName != null && !jobName.isEmpty()) {
                boolQuery.must(Query.of(q -> q.term(t -> t.field("jobName").value(jobName))));
            }

            // Time range filter
            if (startTime > 0 || endTime > 0) {
                boolQuery.must(Query.of(q -> q.range(r -> {
                    r.field("header.timestamp");
                    if (startTime > 0)
                        r.gte(JsonData.of(startTime));
                    if (endTime > 0)
                        r.lte(JsonData.of(endTime));
                    return r;
                })));
            }

            // Filter by layer names
            if (layerNames != null && !layerNames.isEmpty()) {
                List<FieldValue> layerValues = layerNames.stream().map(FieldValue::of)
                        .collect(java.util.stream.Collectors.toList());
                boolQuery.must(Query.of(
                        q -> q.terms(t -> t.field("layerName").terms(v -> v.value(layerValues)))));
            }

            // Filter by states
            if (states != null && !states.isEmpty()) {
                List<FieldValue> stateValues = states.stream().map(s -> FieldValue.of(s.name()))
                        .collect(java.util.stream.Collectors.toList());
                boolQuery.must(Query
                        .of(q -> q.terms(t -> t.field("state").terms(v -> v.value(stateValues)))));
            }

            int size = pageSize > 0 ? pageSize : 100;
            int from = page > 0 ? (page - 1) * size : 0;

            SearchRequest request = SearchRequest.of(s -> s.index(INDEX_FRAME_EVENTS + "-*")
                    .query(Query.of(q -> q.bool(boolQuery.build()))).from(from).size(size)
                    .sort(sort -> sort
                            .field(f -> f.field("header.timestamp").order(SortOrder.Desc))));

            SearchResponse<Map> response = esClient.search(request, Map.class);

            List<HistoricalFrame> results = new ArrayList<>();
            for (Hit<Map> hit : response.hits().hits()) {
                Map<String, Object> source = hit.source();
                if (source != null) {
                    results.add(mapToHistoricalFrame(source));
                }
            }

            return results;
        } catch (Exception e) {
            logger.warn("Failed to search frame history: {}", e.getMessage());
            return Collections.emptyList();
        }
    }

    /**
     * Searches for historical layer events.
     */
    @SuppressWarnings({"rawtypes", "unchecked"})
    public List<HistoricalLayer> searchLayerHistory(String jobId, String jobName, long startTime,
            long endTime, int page, int pageSize) {
        if (!enabled || esClient == null) {
            return Collections.emptyList();
        }

        try {
            BoolQuery.Builder boolQuery = new BoolQuery.Builder();

            // Filter by event type
            boolQuery.must(Query
                    .of(q -> q.term(t -> t.field("header.eventType").value("LAYER_COMPLETED"))));

            // Filter by job
            if (jobId != null && !jobId.isEmpty()) {
                boolQuery.must(Query.of(q -> q.term(t -> t.field("jobId").value(jobId))));
            }
            if (jobName != null && !jobName.isEmpty()) {
                boolQuery.must(Query.of(q -> q.term(t -> t.field("jobName").value(jobName))));
            }

            // Time range filter
            if (startTime > 0 || endTime > 0) {
                boolQuery.must(Query.of(q -> q.range(r -> {
                    r.field("header.timestamp");
                    if (startTime > 0)
                        r.gte(JsonData.of(startTime));
                    if (endTime > 0)
                        r.lte(JsonData.of(endTime));
                    return r;
                })));
            }

            int size = pageSize > 0 ? pageSize : 100;
            int from = page > 0 ? (page - 1) * size : 0;

            SearchRequest request = SearchRequest.of(s -> s.index(INDEX_LAYER_EVENTS + "-*")
                    .query(Query.of(q -> q.bool(boolQuery.build()))).from(from).size(size)
                    .sort(sort -> sort
                            .field(f -> f.field("header.timestamp").order(SortOrder.Desc))));

            SearchResponse<Map> response = esClient.search(request, Map.class);

            List<HistoricalLayer> results = new ArrayList<>();
            for (Hit<Map> hit : response.hits().hits()) {
                Map<String, Object> source = hit.source();
                if (source != null) {
                    results.add(mapToHistoricalLayer(source));
                }
            }

            return results;
        } catch (Exception e) {
            logger.warn("Failed to search layer history: {}", e.getMessage());
            return Collections.emptyList();
        }
    }

    /**
     * Searches for layer memory history records.
     */
    @SuppressWarnings({"rawtypes", "unchecked"})
    public List<LayerMemoryRecord> searchLayerMemoryHistory(String layerName, List<String> shows,
            long startTime, long endTime, int maxResults) {
        if (!enabled || esClient == null) {
            return Collections.emptyList();
        }

        try {
            BoolQuery.Builder boolQuery = new BoolQuery.Builder();

            // Filter by event type (frame completed to get memory data)
            boolQuery.must(Query
                    .of(q -> q.term(t -> t.field("header.eventType").value("FRAME_COMPLETED"))));

            // Filter by layer name
            if (layerName != null && !layerName.isEmpty()) {
                boolQuery.must(Query.of(q -> q.term(t -> t.field("layerName").value(layerName))));
            }

            // Filter by shows
            if (shows != null && !shows.isEmpty()) {
                List<FieldValue> showValues = shows.stream().map(FieldValue::of)
                        .collect(java.util.stream.Collectors.toList());
                boolQuery.must(Query
                        .of(q -> q.terms(t -> t.field("show").terms(v -> v.value(showValues)))));
            }

            // Time range filter
            if (startTime > 0 || endTime > 0) {
                boolQuery.must(Query.of(q -> q.range(r -> {
                    r.field("header.timestamp");
                    if (startTime > 0)
                        r.gte(JsonData.of(startTime));
                    if (endTime > 0)
                        r.lte(JsonData.of(endTime));
                    return r;
                })));
            }

            int size = maxResults > 0 ? maxResults : 1000;

            SearchRequest request = SearchRequest.of(s -> s.index(INDEX_FRAME_EVENTS + "-*")
                    .query(Query.of(q -> q.bool(boolQuery.build()))).size(size).sort(sort -> sort
                            .field(f -> f.field("header.timestamp").order(SortOrder.Desc))));

            SearchResponse<Map> response = esClient.search(request, Map.class);

            List<LayerMemoryRecord> results = new ArrayList<>();
            for (Hit<Map> hit : response.hits().hits()) {
                Map<String, Object> source = hit.source();
                if (source != null) {
                    results.add(mapToLayerMemoryRecord(source));
                }
            }

            return results;
        } catch (Exception e) {
            logger.warn("Failed to search layer memory history: {}", e.getMessage());
            return Collections.emptyList();
        }
    }

    // -------- Helper Methods for Mapping --------

    @SuppressWarnings("unchecked")
    private HistoricalJob mapToHistoricalJob(Map<String, Object> source) {
        HistoricalJob.Builder builder = HistoricalJob.newBuilder();

        builder.setId(getStringValue(source, "jobId"));
        builder.setName(getStringValue(source, "jobName"));
        builder.setShow(getStringValue(source, "show"));
        builder.setShot(getStringValue(source, "shot"));
        builder.setUser(getStringValue(source, "user"));
        builder.setFacility(getStringValue(source, "facility"));

        String stateStr = getStringValue(source, "state");
        if (!stateStr.isEmpty()) {
            try {
                builder.setFinalState(JobState.valueOf(stateStr));
            } catch (IllegalArgumentException e) {
                builder.setFinalState(JobState.FINISHED);
            }
        }

        builder.setStartTime(getIntValue(source, "startTime"));
        builder.setStopTime(getIntValue(source, "stopTime"));
        builder.setPriority(getIntValue(source, "priority"));

        // Stats from nested object
        Map<String, Object> stats = (Map<String, Object>) source.get("stats");
        if (stats != null) {
            builder.setTotalFrames(getIntValue(stats, "totalFrames"));
            builder.setSucceededFrames(getIntValue(stats, "succeededFrames"));
            builder.setFailedFrames(getIntValue(stats, "deadFrames"));
            builder.setTotalCoreSeconds(getLongValue(stats, "renderedCoreSeconds"));
            builder.setTotalGpuSeconds(getLongValue(stats, "renderedGpuSeconds"));
            builder.setMaxRss(getLongValue(stats, "maxRss"));
        }

        return builder.build();
    }

    @SuppressWarnings("unchecked")
    private HistoricalFrame mapToHistoricalFrame(Map<String, Object> source) {
        HistoricalFrame.Builder builder = HistoricalFrame.newBuilder();

        builder.setId(getStringValue(source, "frameId"));
        builder.setName(getStringValue(source, "frameName"));
        builder.setLayerName(getStringValue(source, "layerName"));
        builder.setJobName(getStringValue(source, "jobName"));
        builder.setShow(getStringValue(source, "show"));
        builder.setFrameNumber(getIntValue(source, "frameNumber"));

        String stateStr = getStringValue(source, "state");
        if (!stateStr.isEmpty()) {
            try {
                builder.setFinalState(FrameState.valueOf(stateStr));
            } catch (IllegalArgumentException e) {
                builder.setFinalState(FrameState.SUCCEEDED);
            }
        }

        builder.setExitStatus(getIntValue(source, "exitStatus"));
        builder.setRetryCount(getIntValue(source, "retryCount"));
        builder.setStartTime(getIntValue(source, "startTime"));
        builder.setStopTime(getIntValue(source, "stopTime"));
        builder.setMaxRss(getLongValue(source, "maxRss"));
        builder.setLastHost(getStringValue(source, "hostName"));
        builder.setTotalCoreTime(getIntValue(source, "totalCoreTime"));
        builder.setTotalGpuTime(getIntValue(source, "totalGpuTime"));

        return builder.build();
    }

    @SuppressWarnings("unchecked")
    private HistoricalLayer mapToHistoricalLayer(Map<String, Object> source) {
        HistoricalLayer.Builder builder = HistoricalLayer.newBuilder();

        builder.setId(getStringValue(source, "layerId"));
        builder.setName(getStringValue(source, "layerName"));
        builder.setJobName(getStringValue(source, "jobName"));
        builder.setShow(getStringValue(source, "show"));

        String typeStr = getStringValue(source, "type");
        if (!typeStr.isEmpty()) {
            try {
                builder.setType(LayerType.valueOf(typeStr));
            } catch (IllegalArgumentException e) {
                builder.setType(LayerType.RENDER);
            }
        }

        List<String> tags = (List<String>) source.get("tags");
        if (tags != null) {
            builder.addAllTags(tags);
        }

        List<String> services = (List<String>) source.get("services");
        if (services != null) {
            builder.addAllServices(services);
        }

        // Stats from nested object
        Map<String, Object> stats = (Map<String, Object>) source.get("stats");
        if (stats != null) {
            builder.setTotalFrames(getIntValue(stats, "totalFrames"));
            builder.setSucceededFrames(getIntValue(stats, "succeededFrames"));
            builder.setFailedFrames(getIntValue(stats, "deadFrames"));
            builder.setTotalCoreSeconds(getLongValue(stats, "totalCoreSeconds"));
            builder.setTotalGpuSeconds(getLongValue(stats, "totalGpuSeconds"));
            builder.setMaxRss(getLongValue(stats, "maxRss"));
            builder.setAvgFrameSeconds(getLongValue(stats, "avgFrameSec"));
        }

        return builder.build();
    }

    private LayerMemoryRecord mapToLayerMemoryRecord(Map<String, Object> source) {
        LayerMemoryRecord.Builder builder = LayerMemoryRecord.newBuilder();

        builder.setJobName(getStringValue(source, "jobName"));
        builder.setLayerName(getStringValue(source, "layerName"));
        builder.setShow(getStringValue(source, "show"));

        // Get timestamp from header
        @SuppressWarnings("unchecked")
        Map<String, Object> header = (Map<String, Object>) source.get("header");
        if (header != null) {
            builder.setTimestamp((int) (getLongValue(header, "timestamp") / 1000));
        }

        builder.setMaxRss(getLongValue(source, "maxRss"));
        builder.setReservedMemory(getLongValue(source, "reservedMemory"));

        return builder.build();
    }

    private String getStringValue(Map<String, Object> map, String key) {
        Object value = map.get(key);
        return value != null ? value.toString() : "";
    }

    private int getIntValue(Map<String, Object> map, String key) {
        Object value = map.get(key);
        if (value instanceof Number) {
            return ((Number) value).intValue();
        }
        return 0;
    }

    private long getLongValue(Map<String, Object> map, String key) {
        Object value = map.get(key);
        if (value instanceof Number) {
            return ((Number) value).longValue();
        }
        return 0L;
    }

    /**
     * Generates the index pattern for a time range.
     */
    private String getIndexPattern(String prefix, long startTime, long endTime) {
        if (startTime <= 0 && endTime <= 0) {
            return prefix + "-*";
        }

        // For simplicity, use wildcard pattern
        // In production, could optimize to specific date ranges
        return prefix + "-*";
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

    /**
     * Returns the native Elasticsearch client for advanced queries.
     */
    public co.elastic.clients.elasticsearch.ElasticsearchClient getNativeClient() {
        return esClient;
    }
}
