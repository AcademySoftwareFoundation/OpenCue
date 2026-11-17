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

//! Formatting helpers for human-readable table cells.

use chrono::{Local, TimeZone};

/// Formats an epoch timestamp as local `MM/DD HH:MM`, or `--/-- --:--` when unset.
pub fn format_time(epoch: i64) -> String {
    if epoch <= 0 {
        return "--/-- --:--".to_string();
    }
    match Local.timestamp_opt(epoch, 0).single() {
        Some(time) => time.format("%m/%d %H:%M").to_string(),
        None => "--/-- --:--".to_string(),
    }
}

/// Formats seconds with its two largest units: `45s`, `12m 05s`, `1h 02m`, `3d 4h`.
pub fn format_duration(seconds: i64) -> String {
    let s = seconds.max(0);
    let (days, hours, minutes) = (s / 86_400, s % 86_400 / 3600, s % 3600 / 60);
    if days > 0 {
        format!("{days}d {hours}h")
    } else if hours > 0 {
        format!("{hours}h {minutes:02}m")
    } else if minutes > 0 {
        format!("{minutes}m {:02}s", s % 60)
    } else {
        format!("{s}s")
    }
}

/// Formats an amount of memory given in KB with the closest unit: `512K`, `300M`, `1.5G`.
pub fn format_mem(kb: i64) -> String {
    const K: i64 = 1024;
    if kb < K {
        format!("{kb}K")
    } else if kb < K * K {
        format!("{}M", kb / K)
    } else {
        format!("{:.1}G", kb as f64 / (K * K) as f64)
    }
}

/// Formats a number with at most two decimals and no trailing zeros: `16`, `4.5`, `0.33`.
pub fn format_num(value: f64) -> String {
    let fixed = format!("{value:.2}");
    let trimmed = fixed.trim_end_matches('0').trim_end_matches('.');
    if trimmed == "-0" {
        "0".to_string()
    } else {
        trimmed.to_string()
    }
}

/// Draws `ratio` (0 to 1, clamped) as a bar `width` characters long: `██░░░░░░`.
pub fn usage_bar(ratio: f64, width: usize) -> String {
    let ratio = if ratio.is_finite() {
        ratio.clamp(0.0, 1.0)
    } else {
        0.0
    };
    let filled = (ratio * width as f64).round() as usize;
    format!("{}{}", "█".repeat(filled), "░".repeat(width - filled))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn time() {
        assert_eq!(format_time(0), "--/-- --:--");
        assert_eq!(format_time(1_700_000_000).len(), "11/14 22:13".len());
    }

    #[test]
    fn durations() {
        assert_eq!(format_duration(-5), "0s");
        assert_eq!(format_duration(45), "45s");
        assert_eq!(format_duration(725), "12m 05s");
        assert_eq!(format_duration(3_723), "1h 02m");
        assert_eq!(format_duration(273_600), "3d 4h");
        assert_eq!(format_duration(360_000), "4d 4h");
    }

    #[test]
    fn memory() {
        assert_eq!(format_mem(512), "512K");
        assert_eq!(format_mem(1024), "1M");
        assert_eq!(format_mem(307_200), "300M");
        assert_eq!(format_mem(1_572_864), "1.5G");
    }

    #[test]
    fn numbers() {
        assert_eq!(format_num(16.0), "16");
        assert_eq!(format_num(4.5), "4.5");
        assert_eq!(format_num(1.0 / 3.0), "0.33");
        assert_eq!(format_num(0.001), "0");
        assert_eq!(format_num(-0.001), "0");
    }

    #[test]
    fn bars() {
        assert_eq!(usage_bar(0.25, 8), "██░░░░░░");
        assert_eq!(usage_bar(1.5, 4), "████");
        assert_eq!(usage_bar(f64::NAN, 4), "░░░░");
    }
}
