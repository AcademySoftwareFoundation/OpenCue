package com.imageworks.spcue;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;

import com.imageworks.spcue.dispatcher.BookingQueue;
import com.imageworks.spcue.dispatcher.DispatchQueue;
import com.imageworks.spcue.dispatcher.HostReportHandler;
import com.imageworks.spcue.dispatcher.HostReportQueue;

import io.prometheus.client.Counter;
import io.prometheus.client.Gauge;
import io.prometheus.client.Histogram;

/**
 * Collects and exposes metrics to Prometheus
 */
@Component
public class PrometheusMetricsCollector {
    private BookingQueue bookingQueue;

    private DispatchQueue manageQueue;

    private DispatchQueue dispatchQueue;

    private HostReportQueue reportQueue;

    private boolean enabled;

    // BookingQueue bookingQueue
    private static final Gauge bookingWaitingTotal = Gauge.build().name("cue_booking_waiting_total")
            .help("Booking Queue number of waiting tasks").labelNames("env", "cuebot_hosts")
            .register();
    private static final Gauge bookingRemainingCapacityTotal = Gauge.build()
            .name("cue_booking_remaining_capacity_total").help("Booking Queue remaining capacity")
            .labelNames("env", "cuebot_hosts").register();
    private static final Gauge bookingThreadsTotal = Gauge.build().name("cue_booking_threads_total")
            .help("Booking Queue number of active threads").labelNames("env", "cuebot_hosts")
            .register();
    private static final Gauge bookingExecutedTotal = Gauge.build()
            .name("cue_booking_executed_total").help("Booking Queue number of executed tasks")
            .labelNames("env", "cuebot_hosts").register();
    private static final Gauge bookingRejectedTotal = Gauge.build()
            .name("cue_booking_rejected_total").help("Booking Queue number of rejected tasks")
            .labelNames("env", "cuebot_hosts").register();

    // DispatchQueue manageQueue
    private static final Gauge manageWaitingTotal = Gauge.build().name("cue_manage_waiting_total")
            .help("Manage Queue number of waiting tasks").labelNames("env", "cuebot_hosts")
            .register();
    private static final Gauge manageRemainingCapacityTotal = Gauge.build()
            .name("cue_manage_remaining_capacity_total").help("Manage Queue remaining capacity")
            .labelNames("env", "cuebot_hosts").register();
    private static final Gauge manageThreadsTotal = Gauge.build().name("cue_manage_threads_total")
            .help("Manage Queue number of active threads").labelNames("env", "cuebot_hosts")
            .register();
    private static final Gauge manageExecutedTotal = Gauge.build().name("cue_manage_executed_total")
            .help("Manage Queue number of executed tasks").labelNames("env", "cuebot_hosts")
            .register();
    private static final Gauge manageRejectedTotal = Gauge.build().name("cue_manage_rejected_total")
            .help("Manage Queue number of rejected tasks").labelNames("env", "cuebot_hosts")
            .register();

    // DispatchQueue dispatchQueue
    private static final Gauge dispatchWaitingTotal = Gauge.build()
            .name("cue_dispatch_waiting_total").help("Dispatch Queue number of waiting tasks")
            .labelNames("env", "cuebot_hosts").register();
    private static final Gauge dispatchRemainingCapacityTotal = Gauge.build()
            .name("cue_dispatch_remaining_capacity_total").help("Dispatch Queue remaining capacity")
            .labelNames("env", "cuebot_hosts").register();
    private static final Gauge dispatchThreadsTotal = Gauge.build()
            .name("cue_dispatch_threads_total").help("Dispatch Queue number of active threads")
            .labelNames("env", "cuebot_hosts").register();
    private static final Gauge dispatchExecutedTotal = Gauge.build()
            .name("cue_dispatch_executed_total").help("Dispatch Queue number of executed tasks")
            .labelNames("env", "cuebot_hosts").register();
    private static final Gauge dispatchRejectedTotal = Gauge.build()
            .name("cue_dispatch_rejected_total").help("Dispatch Queue number of rejected tasks")
            .labelNames("env", "cuebot_hosts").register();

    // HostReportQueue reportQueue
    private static final Gauge reportQueueWaitingTotal = Gauge.build()
            .name("cue_report_waiting_total").help("Report Queue number of waiting tasks")
            .labelNames("env", "cuebot_hosts").register();
    private static final Gauge reportQueueRemainingCapacityTotal = Gauge.build()
            .name("cue_report_remaining_capacity_total").help("Report Queue remaining capacity")
            .labelNames("env", "cuebot_hosts").register();
    private static final Gauge reportQueueThreadsTotal = Gauge.build()
            .name("cue_report_threads_total").help("Report Queue number of active threads")
            .labelNames("env", "cuebot_hosts").register();
    private static final Gauge reportQueueExecutedTotal = Gauge.build()
            .name("cue_report_executed_total").help("Report Queue number of executed tasks")
            .labelNames("env", "cuebot_hosts").register();
    private static final Gauge reportQueueRejectedTotal = Gauge.build()
            .name("cue_report_rejected_total").help("Report Queue number of rejected tasks")
            .labelNames("env", "cuebot_hosts").register();

    private static final Counter findJobsByShowQueryCountMetric =
            Counter.build().name("cue_find_jobs_by_show_count")
                    .help("Count the occurrences of the query FIND_JOBS_BY_SHOW.")
                    .labelNames("env", "cuebot_hosts").register();
    private static final Gauge bookingDurationMillisMetric =
            Gauge.build().name("cue_booking_durations_in_millis")
                    .help("Register duration of booking steps in milliseconds.")
                    .labelNames("env", "cuebot_host", "stage_desc").register();
    private static final Histogram bookingDurationMillisHistogramMetric =
            Histogram.build().name("cue_booking_durations_histogram_in_millis")
                    .help("Register a summary of duration of booking steps in milliseconds.")
                    .labelNames("env", "cuebot_host", "stage_desc").register();

    private static final Counter frameKilledCounter = Counter.build()
            .name("cue_frame_killed_counter").help("Number of frames kill requests processed")
            .labelNames("env", "cuebot_host", "render_node", "cause").register();

    private static final Counter frameKillFailureCounter = Counter.build()
            .name("cue_frame_kill_failure_counter")
            .help("Number of frames that failed to be killed after FRAME_KILL_RETRY_LIMIT tries")
            .labelNames("env", "cuebot_host", "render_node", "job_name", "frame_name", "frame_id")
            .register();

    private String deployment_environment;
    private String cuebot_host;

    @Autowired
    public PrometheusMetricsCollector(Environment env) {
        if (env == null) {
            throw new SpcueRuntimeException("Env not defined");
        }
        this.enabled = env.getProperty("metrics.prometheus.collector", Boolean.class, false);
        String envKey = env.getProperty("metrics.prometheus.environment_id.environment_variable",
                String.class, "DEPLOYMENT_ENVIRONMENT");

        this.cuebot_host = getHostNameFromEnv();
        // Get environment id from environment variable
        this.deployment_environment = System.getenv(envKey);
        if (this.deployment_environment == null) {
            this.deployment_environment = "undefined";
        }
    }

    /**
     * Get hostname from environment variable
     * 
     * Uses the following fallback order:
     * 
     * - NODE_HOSTNAME -> HOSTNAME -> HOST -> "undefined"
     * 
     * @return
     */
    private String getHostNameFromEnv() {
        String hostname = System.getenv("NODE_HOSTNAME");
        if (hostname != null) {
            return hostname;
        }

        hostname = System.getenv("HOSTNAME");
        if (hostname != null) {
            return hostname;
        }

        hostname = System.getenv("HOST");
        if (hostname != null) {
            return hostname;
        }

        return "undefined";
    }

    /**
     * Collect metrics from queues
     */
    public void collectPrometheusMetrics() {
        if (this.enabled) {
            // BookingQueue bookingQueue
            bookingWaitingTotal.labels(this.deployment_environment, this.cuebot_host)
                    .set(bookingQueue.getSize());
            bookingRemainingCapacityTotal.labels(this.deployment_environment, this.cuebot_host)
                    .set(bookingQueue.getRemainingCapacity());
            bookingThreadsTotal.labels(this.deployment_environment, this.cuebot_host)
                    .set(bookingQueue.getActiveCount());
            bookingExecutedTotal.labels(this.deployment_environment, this.cuebot_host)
                    .set(bookingQueue.getCompletedTaskCount());
            bookingRejectedTotal.labels(this.deployment_environment, this.cuebot_host)
                    .set(bookingQueue.getRejectedTaskCount());

            // DispatchQueue manageQueue
            manageWaitingTotal.labels(this.deployment_environment, this.cuebot_host)
                    .set(manageQueue.getSize());
            manageRemainingCapacityTotal.labels(this.deployment_environment, this.cuebot_host)
                    .set(manageQueue.getRemainingCapacity());
            manageThreadsTotal.labels(this.deployment_environment, this.cuebot_host)
                    .set(manageQueue.getActiveCount());
            manageExecutedTotal.labels(this.deployment_environment, this.cuebot_host)
                    .set(manageQueue.getCompletedTaskCount());
            manageRejectedTotal.labels(this.deployment_environment, this.cuebot_host)
                    .set(manageQueue.getRejectedTaskCount());

            // DispatchQueue dispatchQueue
            dispatchWaitingTotal.labels(this.deployment_environment, this.cuebot_host)
                    .set(dispatchQueue.getSize());
            dispatchRemainingCapacityTotal.labels(this.deployment_environment, this.cuebot_host)
                    .set(dispatchQueue.getRemainingCapacity());
            dispatchThreadsTotal.labels(this.deployment_environment, this.cuebot_host)
                    .set(dispatchQueue.getActiveCount());
            dispatchExecutedTotal.labels(this.deployment_environment, this.cuebot_host)
                    .set(dispatchQueue.getCompletedTaskCount());
            dispatchRejectedTotal.labels(this.deployment_environment, this.cuebot_host)
                    .set(dispatchQueue.getRejectedTaskCount());

            // HostReportQueue reportQueue
            reportQueueWaitingTotal.labels(this.deployment_environment, this.cuebot_host)
                    .set(reportQueue.getQueue().size());
            reportQueueRemainingCapacityTotal.labels(this.deployment_environment, this.cuebot_host)
                    .set(reportQueue.getQueue().remainingCapacity());
            reportQueueThreadsTotal.labels(this.deployment_environment, this.cuebot_host)
                    .set(reportQueue.getActiveCount());
            reportQueueExecutedTotal.labels(this.deployment_environment, this.cuebot_host)
                    .set(reportQueue.getTaskCount());
            reportQueueRejectedTotal.labels(this.deployment_environment, this.cuebot_host)
                    .set(reportQueue.getRejectedTaskCount());
        }
    }

    /**
     * Set a new value to the cue_booking_durations_in_millis metric
     * 
     * @param stage_desc booking stage description to be used as a tag
     * @param value value to set
     */
    public void setBookingDurationMetric(String stage_desc, double value) {
        bookingDurationMillisMetric
                .labels(this.deployment_environment, this.cuebot_host, stage_desc).set(value);
        bookingDurationMillisHistogramMetric
                .labels(this.deployment_environment, this.cuebot_host, stage_desc).observe(value);
    }

    /**
     * Increment cue_find_jobs_by_show_count metric
     */
    public void incrementFindJobsByShowQueryCountMetric() {
        findJobsByShowQueryCountMetric.labels(this.deployment_environment, this.cuebot_host).inc();
    }

    /**
     * Increment cue_frame_killed_counter metric
     * 
     * @param renderNode hostname of the render node receiving the kill request
     * @param killCause cause assigned to the request
     */
    public void incrementFrameKilledCounter(String renderNode,
            HostReportHandler.KillCause killCause) {
        frameKilledCounter
                .labels(this.deployment_environment, this.cuebot_host, renderNode, killCause.name())
                .inc();
    }

    /**
     * Increment cue_frame_kill_failure_counter metric
     * 
     * @param hostname
     * @param jobName
     * @param frameName
     * @param frameId
     */
    public void incrementFrameKillFailureCounter(String hostname, String jobName, String frameName,
            String frameId) {
        frameKillFailureCounter.labels(this.deployment_environment, this.cuebot_host, hostname,
                jobName, frameName, frameId).inc();
    }

    // Setters used for dependency injection
    public void setBookingQueue(BookingQueue bookingQueue) {
        this.bookingQueue = bookingQueue;
    }

    public void setManageQueue(DispatchQueue manageQueue) {
        this.manageQueue = manageQueue;
    }

    public void setDispatchQueue(DispatchQueue dispatchQueue) {
        this.dispatchQueue = dispatchQueue;
    }

    public void setReportQueue(HostReportQueue reportQueue) {
        this.reportQueue = reportQueue;
    }
}
