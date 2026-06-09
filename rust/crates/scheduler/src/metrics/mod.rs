// Copyright Contributors to the OpenCue Project
//
// Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
// in compliance with the License. You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software distributed under the License
// is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
// or implied. See the License for the specific language governing permissions and limitations under
// the License.

use axum::{response::IntoResponse, routing::get, Router};
use lazy_static::lazy_static;
use prometheus::{
    register_counter, register_counter_vec, register_histogram, Counter, CounterVec, Encoder,
    Histogram, TextEncoder,
};
use std::time::Duration;
use tracing::{error, info};

lazy_static! {
    // Job metrics from entrypoint.rs
    pub static ref JOBS_QUERIED_TOTAL: Counter = register_counter!(
        "scheduler_jobs_queried_total",
        "Total number of jobs queried from the database"
    )
    .expect("Failed to register jobs_queried_total counter");

    pub static ref JOBS_PROCESSED_TOTAL: CounterVec = register_counter_vec!(
        "scheduler_jobs_processed_total",
        "Total number of jobs processed by the scheduler",
        &["show_name"]
    )
    .expect("Failed to register jobs_processed_total counter");

    // Matcher metrics from matcher.rs
    pub static ref NO_CANDIDATE_ITERATIONS_TOTAL: Counter = register_counter!(
        "scheduler_no_candidate_iterations_total",
        "Total number of NoCandidateAvailable iterations"
    )
    .expect("Failed to register no_candidate_iterations_total counter");

    pub static ref CANDIDATES_PER_LAYER: Histogram = register_histogram!(
        "scheduler_candidates_per_layer",
        "Histogram of candidates needed to fully consume a layer",
        vec![1.0, 5.0, 10.0, 20.0, 50.0, 100.0]
    )
    .expect("Failed to register candidates_per_layer histogram");

    // Dispatcher metrics from dispatcher/actor.rs
    pub static ref FRAMES_DISPATCHED_TOTAL: CounterVec = register_counter_vec!(
        "scheduler_frames_dispatched_total",
        "Total number of frames dispatched",
        &["show_name"]
    )
    .expect("Failed to register frames_dispatched_total counter");

    pub static ref TIME_TO_BOOK_SECONDS: Histogram = register_histogram!(
        "scheduler_time_to_book_seconds",
        "Time from frame updated_at until it got fully dispatched",
        vec![0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
    )
    .expect("Failed to register time_to_book_seconds histogram");

    // Accounting metrics from accounting/mod.rs + dispatcher/actor.rs
    //
    // Labeled by the table whose cap was hit (subscription / folder / job). Tracks
    // dispatch attempts that paid for a Redis Lua round-trip only to be rejected by
    // the Lua cap check. Used to decide whether the pre-CheckOut pre-check
    // optimization described in `pipeline/matcher.rs::process_layer` is worth
    // implementing.
    pub static ref ACCOUNTING_LIMIT_EXCEEDED_TOTAL: CounterVec = register_counter_vec!(
        "scheduler_accounting_limit_exceeded_total",
        "Dispatch attempts rejected by the Redis Lua cap check, labeled by table",
        &["table"]
    )
    .expect("Failed to register accounting_limit_exceeded_total counter");

    // Job query metrics from dao/job_dao.rs
    pub static ref JOB_QUERY_DURATION_SECONDS: Histogram = register_histogram!(
        "scheduler_job_query_duration_seconds",
        "Duration of job query operations",
        vec![0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0]
    )
    .expect("Failed to register job_query_duration_seconds histogram");

    // Cluster feed metrics from cluster.rs
    pub static ref CLUSTER_ROUND_TRIP_SECONDS: Histogram = register_histogram!(
        "scheduler_cluster_round_trip_seconds",
        "Time between successive emissions of the same active (non-sleeping) cluster",
        vec![0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0]
    )
    .expect("Failed to register cluster_round_trip_seconds histogram");

    // E-PVM placement metrics from host_cache/cache.rs. Observed only on the
    // Epvm path (Saturation always scores 0.0). Buckets are dimensionless W3
    // fractional-layer-frames units; calibration may need adjustment after
    // production rollout. See design Risk 1.
    pub static ref PLACEMENT_SCORE_CHOSEN: Histogram = register_histogram!(
        "scheduler_placement_score_chosen",
        "E-PVM score of the host chosen by check_out_best",
        vec![0.0, 0.5, 1.0, 2.0, 5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 1000.0]
    )
    .expect("Failed to register placement_score_chosen histogram");
}

/// Handler for the /metrics endpoint
async fn metrics_handler() -> impl IntoResponse {
    let encoder = TextEncoder::new();
    let metric_families = prometheus::gather();
    let mut buffer = Vec::new();

    match encoder.encode(&metric_families, &mut buffer) {
        Ok(_) => {
            let response = String::from_utf8(buffer).unwrap_or_else(|_| String::from(""));
            (
                axum::http::StatusCode::OK,
                [("content-type", "text/plain; version=0.0.4")],
                response,
            )
        }
        Err(e) => {
            error!("Failed to encode metrics: {}", e);
            (
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                [("content-type", "text/plain")],
                format!("Failed to encode metrics: {}", e),
            )
        }
    }
}

/// Start the metrics HTTP server
///
/// # Arguments
///
/// * `addr` - The address to bind the server to (e.g., "0.0.0.0:9090")
///
/// # Returns
///
/// This function runs indefinitely and only returns if the server fails to start
pub async fn start_server(addr: &str) -> miette::Result<()> {
    let app = Router::new().route("/metrics", get(metrics_handler));

    let listener = tokio::net::TcpListener::bind(addr)
        .await
        .map_err(|e| miette::miette!("Failed to bind metrics server to {}: {}", addr, e))?;

    info!("Metrics server listening on http://{}/metrics", addr);

    axum::serve(listener, app)
        .await
        .map_err(|e| miette::miette!("Metrics server error: {}", e))?;

    Ok(())
}

/// Helper function to increment jobs queried counter
#[inline]
pub fn increment_jobs_queried(count: usize) {
    JOBS_QUERIED_TOTAL.inc_by(count as f64);
}

/// Helper function to increment jobs processed counter
#[inline]
pub fn increment_jobs_processed(show_name: &str) {
    JOBS_PROCESSED_TOTAL.with_label_values(&[show_name]).inc();
}

/// Helper function to increment no candidate iterations counter
#[inline]
pub fn increment_no_candidate_iterations() {
    NO_CANDIDATE_ITERATIONS_TOTAL.inc();
}

/// Helper function to observe candidates per layer
#[inline]
pub fn observe_candidates_per_layer(candidates: usize) {
    CANDIDATES_PER_LAYER.observe(candidates as f64);
}

/// Helper function to increment frames dispatched counter
#[inline]
pub fn increment_frames_dispatched(show_name: &str) {
    FRAMES_DISPATCHED_TOTAL
        .with_label_values(&[show_name])
        .inc();
}

/// Helper function to observe time to book
#[inline]
pub fn observe_time_to_book(duration: Duration) {
    TIME_TO_BOOK_SECONDS.observe(duration.as_secs_f64());
}

/// Helper function to increment accounting limit-exceeded counter
#[inline]
pub fn increment_accounting_limit_exceeded(table: &str) {
    ACCOUNTING_LIMIT_EXCEEDED_TOTAL
        .with_label_values(&[table])
        .inc();
}

/// Helper function to observe job query duration
#[inline]
pub fn observe_job_query_duration(duration: Duration) {
    JOB_QUERY_DURATION_SECONDS.observe(duration.as_secs_f64());
}

/// Helper function to observe cluster round-trip duration
#[inline]
pub fn observe_cluster_round_trip(duration: Duration) {
    CLUSTER_ROUND_TRIP_SECONDS.observe(duration.as_secs_f64());
}

/// Records the E-PVM score of the host returned by `check_out_best`.
/// Called only on the Epvm path; Saturation never invokes this.
#[inline]
pub fn observe_placement_score_chosen(score: f64) {
    PLACEMENT_SCORE_CHOSEN.observe(score);
}
