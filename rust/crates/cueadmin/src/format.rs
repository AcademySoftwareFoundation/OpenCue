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

//! Formatting helpers for table cells.

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

/// Formats seconds as `HH:MM:SS`. Hours grow past two digits as needed.
pub fn format_duration(seconds: i64) -> String {
    let seconds = seconds.max(0);
    format!(
        "{:02}:{:02}:{:02}",
        seconds / 3600,
        seconds % 3600 / 60,
        seconds % 60
    )
}

/// Formats seconds as `DD:HH`, for long spans such as uptime.
pub fn format_long_duration(seconds: i64) -> String {
    let hours = seconds.max(0) / 3600;
    format!("{:02}:{:02}", hours / 24, hours % 24)
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

/// Truncates `s` to at most `len` characters, marking the cut with `..`.
pub fn cutoff(s: &str, len: usize) -> String {
    if s.chars().count() <= len {
        return s.to_string();
    }
    let kept: String = s.chars().take(len.saturating_sub(2)).collect();
    format!("{kept}..")
}

/// Formats a bool the way the Python tool did, so scripts parsing the output keep working.
pub fn py_bool(value: bool) -> &'static str {
    if value {
        "True"
    } else {
        "False"
    }
}

/// Formats a float the way Python's `str()` does for simple values: `16.0`, `0.5`.
pub fn py_float(value: f64) -> String {
    if value.fract() == 0.0 && value.abs() < 1e15 {
        format!("{value:.1}")
    } else {
        value.to_string()
    }
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
        assert_eq!(format_duration(0), "00:00:00");
        assert_eq!(format_duration(3_723), "01:02:03");
        assert_eq!(format_duration(360_000), "100:00:00");
        assert_eq!(format_duration(-5), "00:00:00");
        assert_eq!(format_long_duration(90_000), "01:01");
        assert_eq!(format_long_duration(3_599), "00:00");
    }

    #[test]
    fn memory() {
        assert_eq!(format_mem(512), "512K");
        assert_eq!(format_mem(1024), "1M");
        assert_eq!(format_mem(307_200), "300M");
        assert_eq!(format_mem(1_572_864), "1.5G");
    }

    #[test]
    fn truncation() {
        assert_eq!(cutoff("short", 10), "short");
        assert_eq!(cutoff("exactly10!", 10), "exactly10!");
        assert_eq!(cutoff("a_long_job_name", 10), "a_long_j..");
        assert_eq!(cutoff("día_de_render", 6), "día_..");
    }

    #[test]
    fn python_style_values() {
        assert_eq!(py_bool(true), "True");
        assert_eq!(py_float(16.0), "16.0");
        assert_eq!(py_float(0.5), "0.5");
    }
}
