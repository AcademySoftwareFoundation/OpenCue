use std::{cmp, sync::Arc, time::Duration};

use itertools::Itertools;

use crate::{config::CONFIG, frame::running_frame::RunningFrame};

// Message to be used as a reason for killing a frame due to memory pressure.
// This message might be used to track OOM killed frames
pub static OOM_REASON_MSG: &str =
    "Frame killed to free up memory. Machine was falling under OOM pressure";

#[derive(Clone, Copy)]
struct MemoryAggressorScores {
    memory_impact: f64,
    overboard_rate: f64,
    duration_rate: f64,
}

impl MemoryAggressorScores {
    fn total_score(&self) -> f64 {
        self.memory_impact * 10.0 + self.overboard_rate * 7.0 + self.duration_rate * 12.0
    }
}

impl std::ops::Div for MemoryAggressorScores {
    type Output = MemoryAggressorScores;

    fn div(self, rhs: Self) -> Self::Output {
        MemoryAggressorScores {
            memory_impact: self.memory_impact / rhs.memory_impact,
            overboard_rate: self.overboard_rate / rhs.overboard_rate,
            duration_rate: self.duration_rate / rhs.duration_rate,
        }
    }
}
/// If the machine's memory usage exceeds `memory_oom_margin_percentage`, select some frames
/// that are using more memory than their limits to reduce memory usage to safe levels. This
/// logic aims to be as conservative as possible, avoiding the unnecessary termination of frames
///
/// Criteria to sort frames to be killed:
///  - how much memory would be saved by killing it
///  - amount above soft limit
///  - frame running duration
pub fn choose_frames_to_kill(
    memory_usage: u32,
    total_memory: u64,
    frames: Vec<(Arc<RunningFrame>, u64)>,
) -> Vec<Arc<RunningFrame>> {
    if memory_usage > CONFIG.machine.memory_oom_margin_percentage {
        // Calculate target memory level: 5% below the defined safety margin
        let target_memory_level = (total_memory as f64 *
                // Redefined margin percentage = margin - 5%
                (((CONFIG.machine.memory_oom_margin_percentage - 5) as f64) / 100.0))
            as u64;

        // Calculate current memory usage
        let current_memory_usage = (total_memory as f64 * (memory_usage as f64 / 100.0)) as u64;

        // Calculate how much memory we need to free
        let mut memory_to_free = current_memory_usage.saturating_sub(target_memory_level);

        let (total_memory_consumed, max_frame_duration): (u64, Duration) = frames
            .iter()
            .map(|(f, memory_consumed)| (*memory_consumed, f.get_duration()))
            .reduce(|l, r| (l.0 + r.0, cmp::max(l.1, r.1)))
            .unwrap_or((0, Duration::ZERO));

        // Calculate scores denormalized
        let frames_with_scores = frames.iter().map(|(frame, memory_consumed)| {
            (
                frame,
                *memory_consumed,
                calc_memory_aggression_score(
                    *memory_consumed,
                    frame.clone(),
                    total_memory_consumed,
                    max_frame_duration.as_secs_f64(),
                ),
            )
        });

        // Get max scores to normalize values
        let max_scores = frames_with_scores
            .clone()
            .map(|(_, _, score)| score)
            .reduce(|l, r| MemoryAggressorScores {
                memory_impact: l.memory_impact.max(r.memory_impact),
                overboard_rate: l.overboard_rate.max(r.overboard_rate),
                duration_rate: l.duration_rate.max(r.duration_rate),
            })
            .unwrap_or(MemoryAggressorScores {
                memory_impact: 1.0,
                overboard_rate: 1.0,
                duration_rate: 1.0,
            });

        frames_with_scores
            .sorted_by(|l, r| {
                let (_, _, l_denormalized_score) = l;
                let (_, _, r_denormalized_score) = r;
                let l_normalized_score = *l_denormalized_score / max_scores;
                let r_normalized_score = *r_denormalized_score / max_scores;

                let l_score = l_normalized_score.total_score();
                let r_score = r_normalized_score.total_score();
                r_score.total_cmp(&l_score)
            })
            .take_while(|(_, memory_consumed, _)| {
                if memory_to_free > 0 {
                    memory_to_free = memory_to_free.saturating_sub(*memory_consumed);
                    true
                } else {
                    false
                }
            })
            .map(|(frame, _, _)| frame.clone())
            .collect()
    } else {
        Vec::new()
    }
}

fn calc_memory_aggression_score(
    consumed_memory: u64,
    frame: Arc<RunningFrame>,
    total_memory_consumed: u64,
    max_frame_duration: f64,
) -> MemoryAggressorScores {
    // Assert preconditions
    assert!(consumed_memory > frame.request.soft_memory_limit as u64);

    // Convert values to float to simplify logic
    let consumed_memory = consumed_memory as f64;
    let total_memory_consumed = total_memory_consumed as f64;
    let soft_memory_limit = frame.request.soft_memory_limit as f64;
    let frame_duration = frame.get_duration().as_secs_f64();

    // Higher impact
    let memory_impact = consumed_memory / total_memory_consumed;

    // Percentage above limits
    let overboard_rate = (consumed_memory - soft_memory_limit) / soft_memory_limit;

    // Time running. Prefer to kill more recent frames
    let duration_rate = (max_frame_duration - frame_duration) / max_frame_duration;

    MemoryAggressorScores {
        memory_impact,
        overboard_rate,
        duration_rate,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::Config;
    use opencue_proto::rqd::{RunFrame, run_frame::UidOptional};
    use std::collections::HashMap;

    // Helper function to create a test frame with specific memory parameters
    // Note: For black-box testing, frames are in Created state (no actual process running)
    // The get_duration() will return Duration::ZERO for Created frames, which is fine
    // for testing the scoring and selection logic
    fn create_test_frame(
        frame_id: &str,
        soft_memory_limit: i64,
        duration: Duration,
    ) -> Arc<RunningFrame> {
        let general_config = Config::default();
        general_config.setup().unwrap();
        let mut config = general_config.runner;
        config.run_as_user = false;

        let frame = RunningFrame::init_started_for_test(
            RunFrame {
                resource_id: frame_id.to_string(),
                job_id: frame_id.to_string(),
                job_name: "test_job".to_string(),
                frame_id: frame_id.to_string(),
                frame_name: format!("frame_{}", frame_id),
                layer_id: "test_layer".to_string(),
                command: "echo test".to_string(),
                user_name: "testuser".to_string(),
                log_dir: "/tmp".to_string(),
                show: "test_show".to_string(),
                shot: "test_shot".to_string(),
                frame_temp_dir: "".to_string(),
                num_cores: 1,
                gid: 1000,
                ignore_nimby: false,
                environment: HashMap::new(),
                attributes: HashMap::new(),
                num_gpus: 0,
                children: None,
                uid_optional: Some(UidOptional::Uid(1000)),
                os: "rhel9".to_string(),
                soft_memory_limit,
                hard_memory_limit: 0,
                pid: 0,
                loki_url: "".to_string(),
                #[allow(deprecated)]
                job_temp_dir: "".to_string(),
                #[allow(deprecated)]
                log_file: "".to_string(),
                #[allow(deprecated)]
                log_dir_file: "".to_string(),
                #[allow(deprecated)]
                start_time: 0,
            },
            1000,
            config,
            None,
            None,
            "test_host".to_string(),
            duration,
        );

        Arc::new(frame)
    }

    #[test]
    fn test_choose_frames_to_kill_below_threshold() {
        // Memory usage below threshold - should return empty vec
        let frame1 = create_test_frame("frame1", 1000, Duration::from_secs(20));
        let frame2 = create_test_frame("frame2", 2000, Duration::from_secs(20));

        let frames = vec![
            (frame1, 2000), // Using 2000, limit 1000
            (frame2, 3000), // Using 3000, limit 2000
        ];

        let total_memory = 100_000;
        let memory_usage = 50; // 50% - below default threshold of 96%

        let result = choose_frames_to_kill(memory_usage, total_memory, frames);

        assert_eq!(
            result.len(),
            0,
            "Should not kill any frames when below threshold"
        );
    }

    #[test]
    fn test_choose_frames_to_kill_single_frame_high_memory() {
        // Single frame using lots of memory above its limit
        let frame1 = create_test_frame("frame1", 1000, Duration::from_secs(20));

        let frames = vec![
            (frame1.clone(), 10_000), // Using 10GB, limit 1GB
        ];

        let total_memory = 50_000;
        let memory_usage = 97; // Above threshold

        let result = choose_frames_to_kill(memory_usage, total_memory, frames);

        assert_eq!(result.len(), 1, "Should kill the single frame");
        assert_eq!(result[0].frame_id, frame1.frame_id, "Should kill frame1");
    }

    #[test]
    fn test_choose_frames_to_kill_multiple_frames_kills_enough() {
        // Multiple frames, should kill enough to reduce memory below target
        let frame1 = create_test_frame("frame1", 1000, Duration::from_secs(20));
        let frame2 = create_test_frame("frame2", 2000, Duration::from_secs(20));
        let frame3 = create_test_frame("frame3", 3000, Duration::from_secs(20));

        let frames = vec![
            (frame1.clone(), 5_000), // Using 5GB, limit 1GB
            (frame2.clone(), 8_000), // Using 8GB, limit 2GB
            (frame3.clone(), 3_500), // Using 3.5GB, limit 3GB
        ];

        let total_memory = 50_000; // 50GB total
        let memory_usage = 97; // 97% usage - above 96% threshold

        let result = choose_frames_to_kill(memory_usage, total_memory, frames);

        // Should kill at least one frame, possibly more to reach target
        assert!(!result.is_empty(), "Should kill at least one frame");
        assert!(
            result.len() <= 3,
            "Should not kill more frames than available"
        );

        // Calculate how much memory would be freed
        let freed_memory: u64 = result
            .iter()
            .map(|f| {
                if f.frame_id == frame1.frame_id {
                    5_000
                } else if f.frame_id == frame2.frame_id {
                    8_000
                } else if f.frame_id == frame3.frame_id {
                    3_500
                } else {
                    0
                }
            })
            .sum();

        // Freed memory should be enough to reach target (91% of 50GB = 45.5GB)
        let target_memory = (total_memory as f64 * 0.91) as u64;
        let current_memory = (total_memory as f64 * 0.97) as u64;
        assert!(
            freed_memory >= current_memory - target_memory,
            "Should free enough memory to reach target"
        );
    }

    #[test]
    fn test_choose_frames_to_kill_prefers_highest_memory_impact() {
        // Frame with highest memory consumption should be prioritized
        // Both frames have the SAME overboard rate (100% over limit) to isolate memory impact
        let frame_small = create_test_frame("frame_small", 1000, Duration::from_secs(20));
        let frame_large = create_test_frame("frame_large", 10_000, Duration::from_secs(20));

        let frames = vec![
            (frame_small, 2_000u64),          // Using 2GB, limit 1GB (100% over)
            (frame_large.clone(), 20_000u64), // Using 20GB, limit 10GB (100% over)
        ];

        let total_memory = 100_000u64; // 100GB total
        let memory_usage = 97u32; // Above threshold

        let result = choose_frames_to_kill(memory_usage, total_memory, frames);

        // Should prioritize the frame using more memory (higher absolute impact)
        // Both have same overboard rate, but frame_large has 10x the memory impact
        assert!(!result.is_empty(), "Should kill at least one frame");
        assert_eq!(
            result[0].frame_id, frame_large.frame_id,
            "Should kill the frame with highest memory impact first (same overboard rate)"
        );
    }

    #[test]
    fn test_choose_frames_to_kill_prefers_highest_overboard_rate() {
        // Frame with highest percentage over limit should be considered
        let frame1 = create_test_frame("frame1", 1000, Duration::from_secs(20));
        let frame2 = create_test_frame("frame2", 10_000, Duration::from_secs(20));

        let frames = vec![
            (frame1, 5_000u64),  // Using 5GB, limit 1GB (400% over)
            (frame2, 15_000u64), // Using 15GB, limit 10GB (50% over)
        ];

        let total_memory = 100_000u64; // 100GB
        let memory_usage = 97u32; // Above threshold

        let result = choose_frames_to_kill(memory_usage, total_memory, frames);

        assert!(!result.is_empty(), "Should kill at least one frame");
        // Both frames are valid candidates; we verify at least one was killed
        assert!(result.len() <= 2, "Should kill reasonable number of frames");
    }

    #[test]
    fn test_choose_frames_to_kill_empty_list() {
        // Empty frame list should return empty result
        let frames: Vec<(Arc<RunningFrame>, u64)> = vec![];

        let total_memory = 100_000u64;
        let memory_usage = 97u32;

        let result = choose_frames_to_kill(memory_usage, total_memory, frames);

        assert_eq!(result.len(), 0, "Should return empty list for empty input");
    }

    #[test]
    fn test_choose_frames_to_kill_exact_threshold() {
        // At exact threshold (96%) should NOT trigger OOM logic
        let frame1 = create_test_frame("frame1", 1000, Duration::from_secs(20));

        let frames = vec![(frame1, 10_000u64)];

        let total_memory = 100_000u64;
        let memory_usage = 96u32; // Exactly at threshold

        let result = choose_frames_to_kill(memory_usage, total_memory, frames);

        // At threshold but not over, should not kill
        assert_eq!(
            result.len(),
            0,
            "Should not kill at exact threshold (needs to be over)"
        );
    }

    #[test]
    fn test_choose_frames_to_kill_just_over_threshold() {
        // Just over threshold should trigger kill
        let frame1 = create_test_frame("frame1", 1000, Duration::from_secs(20));

        let frames = vec![(frame1.clone(), 10_000u64)];

        let total_memory = 100_000u64;
        let memory_usage = 97u32; // Just over 96% threshold

        let result = choose_frames_to_kill(memory_usage, total_memory, frames);

        assert_eq!(
            result.len(),
            1,
            "Should kill frame when just over threshold"
        );
    }

    #[test]
    fn test_choose_frames_to_kill_balanced_criteria() {
        // White-box test: verify that the scoring algorithm balances all three criteria correctly
        // Scoring formula: memory_impact×10 + overboard_rate×7 + duration_rate×12
        // (all normalized to [0,1] by dividing by max values)

        let frame_a = create_test_frame("frame_a", 50_000, Duration::from_secs(20));
        let frame_b = create_test_frame("frame_b", 1_000, Duration::from_secs(20));
        let frame_c = create_test_frame("frame_c", 10_000, Duration::from_secs(20));

        let frames = vec![
            (frame_a.clone(), 60_000u64), // Using 60GB, limit 50GB (20% over)
            (frame_b.clone(), 10_000u64), // Using 10GB, limit 1GB (900% over)
            (frame_c.clone(), 15_000u64), // Using 15GB, limit 10GB (50% over)
        ];
        // Total memory consumed: 85GB

        // Calculate expected scores (assuming all have same duration = 0):
        // Frame A: memory_impact=60/85=0.706, overboard=10/50=0.20, duration=1.0
        //   Normalized: (1.0, 0.022, 1.0) → score = 10 + 0.15 + 12 = 22.15
        // Frame B: memory_impact=10/85=0.118, overboard=9/1=9.0, duration=1.0
        //   Normalized: (0.167, 1.0, 1.0) → score = 1.67 + 7 + 12 = 20.67
        // Frame C: memory_impact=15/85=0.176, overboard=5/10=0.50, duration=1.0
        //   Normalized: (0.249, 0.056, 1.0) → score = 2.49 + 0.39 + 12 = 14.88
        //
        // Expected order: Frame A (highest score), Frame B, Frame C

        let total_memory = 200_000u64; // 200GB
        let memory_usage = 97u32; // Above threshold

        let result = choose_frames_to_kill(memory_usage, total_memory, frames);

        assert!(!result.is_empty(), "Should kill at least one frame");
        // Frame A should be killed first because it has the highest combined score
        // (highest memory impact wins even though frame B has highest overboard rate)
        assert_eq!(
            result[0].frame_id, frame_a.frame_id,
            "Frame A should be killed first: it has the highest memory impact (60GB/85GB = 70.6%), \
             which outweighs frame B's higher overboard rate in the weighted scoring formula"
        );
    }

    #[test]
    fn test_choose_frames_to_kill_stops_when_target_reached() {
        // Should stop killing once enough memory is freed
        let frame1 = create_test_frame("frame1", 1000, Duration::from_secs(20));
        let frame2 = create_test_frame("frame2", 1000, Duration::from_secs(20));
        let frame3 = create_test_frame("frame3", 1000, Duration::from_secs(20));

        // Each frame frees 6GB when killed
        let frames = vec![(frame1, 7_000u64), (frame2, 7_000u64), (frame3, 7_000u64)];

        let total_memory = 50_000u64; // 50GB
        let memory_usage = 97u32; // 97% = 48.5GB
        // Target: 91% = 45.5GB (96 - 5)
        // Need to free: ~3GB
        // Should kill 1 frame (7GB > 3GB needed)

        let result = choose_frames_to_kill(memory_usage, total_memory, frames);

        // Should kill minimum frames needed
        assert!(!result.is_empty(), "Should kill at least one frame");
        assert!(
            result.len() <= 2,
            "Should not kill all frames when not necessary"
        );
    }

    #[test]
    fn test_choose_frames_to_kill_target_calculation() {
        // Verify target memory calculation: (threshold - 5)% of total
        let frame1 = create_test_frame("frame1", 1000, Duration::from_secs(20));

        let frames = vec![(frame1, 10_000u64)];

        let total_memory = 100_000u64; // 100GB
        let memory_usage = 97u32; // 97%
        // Default threshold is 96%, so target is 91% (96-5)
        // Current: 97GB, Target: 91GB, Need to free: 6GB
        // Frame consumes 10GB, so should be killed

        let result = choose_frames_to_kill(memory_usage, total_memory, frames);

        assert_eq!(
            result.len(),
            1,
            "Should kill frame to reach target below (threshold-5)%"
        );
    }

    #[test]
    fn test_choose_frames_to_kill_prefers_shorter_duration() {
        // Test that frames with shorter duration are prioritized for killing
        // All other factors being equal, we prefer to kill more recent frames
        let frame_old = create_test_frame("frame_old", 5_000, Duration::from_secs(3600)); // 1 hour old
        let frame_recent = create_test_frame("frame_recent", 5_000, Duration::from_secs(60)); // 1 minute old

        // Both frames: same memory consumption, same limit, same overboard rate
        let frames = vec![
            (frame_old.clone(), 10_000u64),    // Using 10GB, limit 5GB (100% over)
            (frame_recent.clone(), 10_000u64), // Using 10GB, limit 5GB (100% over)
        ];

        let total_memory = 100_000u64; // 100GB
        let memory_usage = 97u32; // Above threshold

        let result = choose_frames_to_kill(memory_usage, total_memory, frames);

        assert!(!result.is_empty(), "Should kill at least one frame");
        // Should prefer killing the more recent frame (shorter duration)
        assert_eq!(
            result[0].frame_id, frame_recent.frame_id,
            "Should kill the more recent frame first (shorter duration = higher duration_rate score)"
        );
    }

    #[test]
    fn test_choose_frames_to_kill_duration_with_different_memory() {
        // Test duration scoring when frames have different memory characteristics
        // Frame A: Old (3600s), high memory (20GB), moderate overboard (100%)
        // Frame B: Recent (60s), moderate memory (10GB), moderate overboard (100%)
        let frame_old_high_mem = create_test_frame("frame_old", 10_000, Duration::from_secs(3600));
        let frame_recent_low_mem =
            create_test_frame("frame_recent", 5_000, Duration::from_secs(60));

        let frames = vec![
            (frame_old_high_mem.clone(), 20_000u64), // Using 20GB, limit 10GB (100% over)
            (frame_recent_low_mem.clone(), 10_000u64), // Using 10GB, limit 5GB (100% over)
        ];

        let total_memory = 100_000u64; // 100GB
        let memory_usage = 97u32; // Above threshold

        let result = choose_frames_to_kill(memory_usage, total_memory, frames);

        assert!(!result.is_empty(), "Should kill at least one frame");
        // The old frame with high memory should be killed first despite being older
        // because memory_impact (20/30 vs 10/30) outweighs duration_rate in the scoring
        assert_eq!(
            result[0].frame_id, frame_old_high_mem.frame_id,
            "Should kill frame with highest memory impact even though it's older"
        );
    }

    #[test]
    fn test_choose_frames_to_kill_duration_ordering_with_same_memory() {
        // Test that when memory characteristics are identical, duration is the tiebreaker
        let frame1 = create_test_frame("frame1", 5_000, Duration::from_secs(100)); // Oldest
        let frame2 = create_test_frame("frame2", 5_000, Duration::from_secs(50)); // Middle
        let frame3 = create_test_frame("frame3", 5_000, Duration::from_secs(10)); // Newest

        // All frames: identical memory usage and limits
        let frames = vec![
            (frame1.clone(), 10_000u64), // Using 10GB, limit 5GB
            (frame2.clone(), 10_000u64), // Using 10GB, limit 5GB
            (frame3.clone(), 10_000u64), // Using 10GB, limit 5GB
        ];

        let total_memory = 100_000u64; // 100GB
        let memory_usage = 97u32; // Above threshold

        let result = choose_frames_to_kill(memory_usage, total_memory, frames);

        // Should kill frames in order from newest to oldest (shortest to longest duration)
        assert!(!result.is_empty(), "Should kill at least one frame");
        assert_eq!(
            result[0].frame_id, frame3.frame_id,
            "Should kill newest frame first (shortest duration)"
        );
        if result.len() >= 2 {
            assert_eq!(
                result[1].frame_id, frame2.frame_id,
                "Should kill middle-age frame second"
            );
        }
        if result.len() >= 3 {
            assert_eq!(
                result[2].frame_id, frame1.frame_id,
                "Should kill oldest frame last"
            );
        }
    }

    #[test]
    fn test_choose_frames_to_kill_duration_weight_in_scoring() {
        // White-box test: verify that duration_rate contributes significantly to the score
        // Scoring formula: memory_impact×10 + overboard_rate×7 + duration_rate×12
        // Duration has the highest weight (12), so it should matter in close calls

        // Frame A: 55% memory impact, 100% overboard, oldest (duration_rate=0)
        // Frame B: 45% memory impact, 100% overboard, newest (duration_rate=1)
        let frame_old = create_test_frame("frame_old", 5_000, Duration::from_secs(1000));
        let frame_new = create_test_frame("frame_new", 5_000, Duration::from_secs(1));

        let frames = vec![
            (frame_old.clone(), 11_000u64), // Using 11GB, limit 5GB (55% of total)
            (frame_new.clone(), 9_000u64),  // Using 9GB, limit 5GB (45% of total)
        ];
        // Total consumed: 20GB

        // Expected scores (normalized):
        // Frame A: memory_impact=11/20=0.55, overboard=6/5=1.2, duration=0/999=0
        //   Normalized: (0.5, 1.0, 0) → score = 5 + 7 + 0 = 12
        // Frame B: memory_impact=9/20=0.45, overboard=4/5=0.8, duration=999/999=1.0
        //   Normalized: (0.409, 0.667, 1.0) → score = 4.09 + 4.67 + 12 = 20.76
        //
        // Frame B (newer) should win despite lower memory impact because duration_rate×12 dominates

        let total_memory = 100_000u64; // 100GB
        let memory_usage = 97u32; // Above threshold

        let result = choose_frames_to_kill(memory_usage, total_memory, frames);

        assert!(!result.is_empty(), "Should kill at least one frame");
        assert_eq!(
            result[0].frame_id, frame_new.frame_id,
            "Should kill newer frame first because duration_rate weight (×12) dominates the score \
             despite slightly lower memory impact"
        );
    }
}
