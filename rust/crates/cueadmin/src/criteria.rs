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

//! Parsing of user supplied search ranges and burst values.

use std::str::FromStr;

/// A numeric filter given on the command line: `MIN-MAX`, `gtVALUE`, `ltVALUE` or `VALUE`
/// (same as `gtVALUE`).
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum RangeFilter {
    AtLeast(f64),
    AtMost(f64),
    Between(f64, f64),
}

impl RangeFilter {
    /// Returns the inclusive `(min, max)` bounds after scaling by `factor`, clamping open ends
    /// to `0` and `i32::MAX`.
    pub fn bounds(&self, factor: f64) -> (i64, i64) {
        let scale = |v: f64| (v * factor) as i64;
        match *self {
            RangeFilter::AtLeast(v) => (scale(v), i32::MAX as i64),
            RangeFilter::AtMost(v) => (0, scale(v)),
            RangeFilter::Between(min, max) => (scale(min), scale(max)),
        }
    }
}

impl FromStr for RangeFilter {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let number = |v: &str| {
            v.trim()
                .parse::<f64>()
                .ok()
                .filter(|n| n.is_finite() && *n >= 0.0)
                .ok_or_else(|| format!("'{v}' is not a non-negative number"))
        };
        let s = s.trim();
        if let Some(v) = s.strip_prefix("gt") {
            return Ok(RangeFilter::AtLeast(number(v)?));
        }
        if let Some(v) = s.strip_prefix("lt") {
            return Ok(RangeFilter::AtMost(number(v)?));
        }
        if let Some((min, max)) = s.split_once('-') {
            let (min, max) = (number(min)?, number(max)?);
            if min > max {
                return Err(format!("range minimum {min} is above maximum {max}"));
            }
            return Ok(RangeFilter::Between(min, max));
        }
        Ok(RangeFilter::AtLeast(number(s)?))
    }
}

/// A subscription burst: an absolute core count, or a percentage of the subscription size to
/// add on top of it.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Burst {
    Cores(f32),
    Percent(f32),
}

impl Burst {
    /// Returns the burst in core units (cores * 100) for a subscription of `size_units`.
    pub fn to_core_units(self, size_units: i32) -> i32 {
        match self {
            Burst::Cores(cores) => cores_to_units(cores),
            Burst::Percent(percent) => {
                (size_units as f64 * (1.0 + percent as f64 / 100.0)).round() as i32
            }
        }
    }
}

impl FromStr for Burst {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let (value, percent) = match s.trim().strip_suffix('%') {
            Some(v) => (v, true),
            None => (s.trim(), false),
        };
        let value: f32 = value
            .parse()
            .ok()
            .filter(|n: &f32| n.is_finite() && *n >= 0.0)
            .ok_or_else(|| format!("'{s}' is not a core count or a percentage"))?;
        Ok(if percent {
            Burst::Percent(value)
        } else {
            Burst::Cores(value)
        })
    }
}

/// Converts cores into Cuebot core units, which are hundredths of a core.
pub fn cores_to_units(cores: f32) -> i32 {
    (cores as f64 * 100.0).round() as i32
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_ranges() {
        assert_eq!("gt4".parse(), Ok(RangeFilter::AtLeast(4.0)));
        assert_eq!("4".parse(), Ok(RangeFilter::AtLeast(4.0)));
        assert_eq!("lt0.5".parse(), Ok(RangeFilter::AtMost(0.5)));
        assert_eq!("3.5-4.5".parse(), Ok(RangeFilter::Between(3.5, 4.5)));
        assert!("4-3".parse::<RangeFilter>().is_err());
        assert!("gtx".parse::<RangeFilter>().is_err());
        assert!("".parse::<RangeFilter>().is_err());
    }

    #[test]
    fn scales_bounds() {
        let gb_to_kb = 1024.0 * 1024.0;
        assert_eq!(
            RangeFilter::Between(1.0, 2.0).bounds(gb_to_kb),
            (1048576, 2097152)
        );
        assert_eq!(RangeFilter::AtMost(1.5).bounds(3600.0), (0, 5400));
        assert_eq!(
            RangeFilter::AtLeast(1.0).bounds(3600.0),
            (3600, i32::MAX as i64)
        );
    }

    #[test]
    fn parses_burst() {
        assert_eq!("120".parse(), Ok(Burst::Cores(120.0)));
        assert_eq!("20%".parse(), Ok(Burst::Percent(20.0)));
        assert!("abc%".parse::<Burst>().is_err());
        assert!("-1".parse::<Burst>().is_err());
    }

    #[test]
    fn burst_to_core_units() {
        assert_eq!(Burst::Cores(12.5).to_core_units(0), 1250);
        // 100 cores plus 20%.
        assert_eq!(Burst::Percent(20.0).to_core_units(10000), 12000);
    }
}
