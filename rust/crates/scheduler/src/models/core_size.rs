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

/// A module to handle two different units used to represent cores:
/// `CoreSize` and `CoreSizeWithMultiplier`.
///
/// In OpenCue's database, core counts are stored with a multiplier (typically 100,
/// configurable in the CueBot config file). For example, 1 core might be stored as 100.
///
/// To simplify booking calculations, this multiplier is often ignored to avoid partial
/// bookings (fractions of a single core). However, mixing values with and without the
/// multiplier can lead to bugs in calculations.
///
/// This module provides two distinct types that can be converted between each other
/// but cannot be directly used together in operations, preventing accidental mixing
/// of multiplied and non-multiplied values.
///
use core::fmt;
use std::{
    cmp,
    fmt::Display,
    ops::{Add, Sub},
};

use serde::{Deserialize, Serialize};

use crate::config::CONFIG;

/// Size of a processing unit (# cores without multiplier)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct CoreSize(pub i32);

/// Size of a processing unit with a multiplier (# cores with multiplier)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct CoreSizeWithMultiplier(pub i32);

impl CoreSize {
    /// Returns the raw core count value without multiplier.
    ///
    /// # Returns
    ///
    /// * `i32` - Number of cores
    pub fn value(self) -> i32 {
        self.0
    }

    /// Converts this CoreSize to CoreSizeWithMultiplier by applying the configured multiplier.
    ///
    /// # Returns
    ///
    /// * `CoreSizeWithMultiplier` - Core count with multiplier applied
    #[allow(dead_code)]
    pub fn with_multiplier(self) -> CoreSizeWithMultiplier {
        self.into()
    }

    /// Creates a CoreSize from a raw integer value that includes the multiplier.
    ///
    /// # Arguments
    ///
    /// * `size_with_multiplier` - Core count with multiplier already applied
    ///
    /// # Returns
    ///
    /// * `CoreSize` - Core count without multiplier
    pub fn from_multiplied(size_with_multiplier: i32) -> CoreSize {
        Self(size_with_multiplier / CONFIG.queue.core_multiplier as i32)
    }
}

impl CoreSizeWithMultiplier {
    /// Returns the raw core count value with multiplier applied.
    ///
    /// # Returns
    ///
    /// * `i32` - Number of cores multiplied by the configured multiplier
    pub fn value(self) -> i32 {
        self.0
    }
}

impl From<CoreSize> for CoreSizeWithMultiplier {
    fn from(value: CoreSize) -> Self {
        CoreSizeWithMultiplier(value.value() * CONFIG.queue.core_multiplier as i32)
    }
}

impl From<CoreSizeWithMultiplier> for CoreSize {
    fn from(value: CoreSizeWithMultiplier) -> Self {
        CoreSize(value.value() / CONFIG.queue.core_multiplier as i32)
    }
}

impl Add for CoreSize {
    type Output = CoreSize;

    fn add(self, rhs: Self) -> Self::Output {
        Self(rhs.value() + self.value())
    }
}

impl Add for CoreSizeWithMultiplier {
    type Output = CoreSizeWithMultiplier;

    fn add(self, rhs: Self) -> Self::Output {
        Self(rhs.value() + self.value())
    }
}

impl Sub for CoreSize {
    type Output = CoreSize;

    fn sub(self, rhs: Self) -> Self::Output {
        Self(self.value() - rhs.value())
    }
}

impl Sub for CoreSizeWithMultiplier {
    type Output = CoreSizeWithMultiplier;

    fn sub(self, rhs: Self) -> Self::Output {
        Self(self.value() - rhs.value())
    }
}

impl cmp::Ord for CoreSize {
    fn cmp(&self, other: &Self) -> cmp::Ordering {
        self.0.cmp(&other.0)
    }
}

impl cmp::PartialOrd for CoreSize {
    fn partial_cmp(&self, other: &Self) -> Option<cmp::Ordering> {
        Some(self.cmp(other))
    }
}

impl Display for CoreSize {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}
