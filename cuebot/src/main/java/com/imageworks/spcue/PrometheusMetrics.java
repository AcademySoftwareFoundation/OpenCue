package com.imageworks.spcue;

import io.prometheus.client.Counter;
import io.prometheus.client.Gauge;
import io.prometheus.client.Histogram;

public class PrometheusMetrics {
    private static final Counter findJobsByShowQueryCountMetric = Counter.build()
            .name("cue_find_jobs_by_show_count")
            .help("Count the occurrences of the query FIND_JOBS_BY_SHOW.")
            .labelNames("env", "cuebot_hosts")
            .register();
    private static final Gauge bookingDurationMillisMetric = Gauge.build()
            .name("cue_booking_durations_in_millis")
            .help("Register duration of booking steps in milliseconds.")
            .labelNames("env", "cuebot_host", "stage_desc")
            .register();
    private static final Histogram bookingDurationMillisHistogramMetric = Histogram.build()
            .name("cue_booking_durations_histogram_in_millis")
            .help("Register a summary of duration of booking steps in milliseconds.")
            .labelNames("env", "cuebot_host", "stage_desc")
            .register();

    private static final Counter frameOomKilledCounter = Counter.build()
            .name("cue_frame_oom_killed_counter")
            .help("Number of frames killed for being above memory on a host under OOM")
            .labelNames("env", "cuebot_host", "render_node")
            .register();

    private String deployment_environment;
    private String cuebot_host;

    public PrometheusMetrics() {
        this.cuebot_host = System.getenv("NODE_HOSTNAME");
        if (this.cuebot_host == null) {
            this.cuebot_host = "undefined";
        }
        // Use the same environment set for SENTRY as the prometheus environment
        this.deployment_environment =  System.getenv("SENTRY_ENVIRONMENT");
        if (this.deployment_environment == null) {
            this.deployment_environment = "undefined";
        }
    }

    public void setBookingDurationMetric(String stage_desc, double value) {
        bookingDurationMillisMetric.labels(this.deployment_environment, this.cuebot_host, stage_desc).set(value);
        bookingDurationMillisHistogramMetric.labels(this.deployment_environment, this.cuebot_host, stage_desc).observe(value);
    }

    public void incrementFindJobsByShowQueryCountMetric() {
        findJobsByShowQueryCountMetric.labels(this.deployment_environment, this.cuebot_host).inc();
    }

    public void incrementFrameOomKilledCounter(String renderNode) {
        frameOomKilledCounter.labels(this.deployment_environment, this.cuebot_host, renderNode).inc();
    }
}