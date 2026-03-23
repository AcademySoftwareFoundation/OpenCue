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

//! Frame range parsing and manipulation for OpenCue job queue.
//!
//! This module provides functionality for parsing and manipulating frame ranges
//! commonly used in render farm job specifications. It supports various frame
//! range syntaxes including simple ranges, stepped ranges, inverse steps, and
//! interleaved patterns.
//!
//! # Frame Range Syntax
//!
//! The following syntax patterns are supported:
//!
//! - **Single frame**: `"5"` → `[5]`
//! - **Simple range**: `"1-10"` → `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]`
//! - **Stepped range**: `"1-10x2"` → `[1, 3, 5, 7, 9]`
//! - **Inverse stepped**: `"1-10y3"` → `[2, 3, 5, 6, 8, 9]` (excludes every 3rd frame)
//! - **Negative step**: `"10-1x-2"` → `[10, 8, 6, 4, 2]`
//! - **Interleaved**: `"1-10:5"` → `[1, 6, 3, 5, 7, 9, 2, 4, 8, 10]`
//!
//! # Frame Set Syntax
//!
//! Multiple frame ranges can be combined with commas:
//! - `"1-5,10-15"` → `[1, 2, 3, 4, 5, 10, 11, 12, 13, 14, 15]`
//! - `"1-10x2,20,25-30"` → `[1, 3, 5, 7, 9, 20, 25, 26, 27, 28, 29, 30]`
//!
//! # Examples
//!
//! ```rust,ignore
//! use scheduler::pipeline::dispatcher::frame_set::{FrameRange, FrameSet};
//!
//! // Parse a simple frame range
//! let range = FrameRange::new("1-10x2")?;
//! assert_eq!(range.get_all(), &[1, 3, 5, 7, 9]);
//!
//! // Parse a complex frame set
//! let frame_set = FrameSet::new("1-5,10-15x2")?;
//! assert_eq!(frame_set.get_all(), &[1, 2, 3, 4, 5, 10, 12, 14]);
//!
//! // Get a chunk for job distribution
//! let chunk = frame_set.get_chunk(2, 3)?; // Starting at index 2, size 3
//! assert_eq!(chunk, "3-5");
//! ```

use indexmap::IndexSet;
use miette::{miette, Context, IntoDiagnostic, Result};
use regex::Regex;

/// Represents a sequence of image frames parsed from a frame range specification.
///
/// A `FrameRange` represents a single contiguous or patterned sequence of frame numbers.
/// It supports various syntaxes including simple ranges, stepped ranges, inverse steps,
/// and interleaved patterns.
///
/// This is a direct port of the Java `FrameRange` class from OpenCue's codebot.
///
/// # Supported Syntax
///
/// - **Single frame**: `"42"` produces `[42]`
/// - **Simple range**: `"1-10"` produces `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]`
/// - **Stepped range (x)**: `"1-10x3"` produces `[1, 4, 7, 10]` (every 3rd frame)
/// - **Inverse stepped (y)**: `"1-10y3"` produces `[2, 3, 5, 6, 8, 9]` (all except every 3rd)
/// - **Negative step**: `"10-1x-2"` produces `[10, 8, 6, 4, 2]` (backwards with step)
/// - **Interleaved (:)**: `"1-10:5"` produces interleaved pattern for render optimization
///
/// # Validation Rules
///
/// - Step size cannot be zero
/// - For positive steps, end frame must be >= start frame
/// - For negative steps, end frame must be <= start frame
/// - Step size and interleave size cannot be combined
///
/// # Examples
///
/// ```rust,ignore
/// // Basic usage
/// let range = FrameRange::new("1-10x2")?;
/// assert_eq!(range.size(), 5);
/// assert_eq!(range.get(0), Some(1));
/// assert_eq!(range.get_all(), &[1, 3, 5, 7, 9]);
///
/// // Inverse stepping
/// let inverse = FrameRange::new("1-10y3")?;
/// assert_eq!(inverse.get_all(), &[2, 3, 5, 6, 8, 9]);
/// ```
#[derive(Debug, Clone, PartialEq)]
#[allow(dead_code)]
pub struct FrameRange {
    frame_list: Vec<i32>,
}

impl FrameRange {
    /// Constructs a new `FrameRange` by parsing a frame range specification.
    ///
    /// # Arguments
    ///
    /// * `frame_range` - A string specification following the frame range syntax
    ///
    /// # Returns
    ///
    /// * `Ok(FrameRange)` - Successfully parsed frame range
    /// * `Err(String)` - Parse error with description
    ///
    /// # Examples
    ///
    /// ```rust,ignore
    /// let range = FrameRange::new("1-10x2")?;
    /// let single = FrameRange::new("42")?;
    /// let inverse = FrameRange::new("1-10y3")?;
    /// ```
    ///
    /// # Errors
    ///
    /// Returns an error if:
    /// - The syntax is invalid or unrecognized
    /// - Step size is zero
    /// - Step direction conflicts with range direction
    /// - Frame numbers cannot be parsed as integers
    #[allow(dead_code)]
    pub fn new(frame_range: &str) -> Result<Self> {
        let frame_list = Self::parse_frame_range(frame_range)?;
        Ok(FrameRange { frame_list })
    }

    /// Gets the number of frames contained in this sequence.
    ///
    /// # Returns
    ///
    /// The total count of frames in the range.
    ///
    /// # Example
    ///
    /// ```rust,ignore
    /// let range = FrameRange::new("1-10x2")?;
    /// assert_eq!(range.size(), 5); // [1, 3, 5, 7, 9]
    /// ```
    #[allow(dead_code)]
    pub fn size(&self) -> usize {
        self.frame_list.len()
    }

    /// Gets an individual frame number by its position in the sequence.
    ///
    /// # Arguments
    ///
    /// * `idx` - Zero-based index into the frame sequence
    ///
    /// # Returns
    ///
    /// * `Some(frame_number)` - If the index is valid
    /// * `None` - If the index is out of bounds
    ///
    /// # Example
    ///
    /// ```rust,ignore
    /// let range = FrameRange::new("1-10x2")?;
    /// assert_eq!(range.get(0), Some(1));
    /// assert_eq!(range.get(2), Some(5));
    /// assert_eq!(range.get(10), None);
    /// ```
    #[allow(dead_code)]
    pub fn get(&self, idx: usize) -> Option<i32> {
        self.frame_list.get(idx).copied()
    }

    /// Finds the index of a specific frame number in the sequence.
    ///
    /// # Arguments
    ///
    /// * `frame` - The frame number to search for
    ///
    /// # Returns
    ///
    /// * `Some(index)` - Zero-based index if the frame is found
    /// * `None` - If the frame is not in the sequence
    ///
    /// # Example
    ///
    /// ```rust,ignore
    /// let range = FrameRange::new("1-10x2")?;
    /// assert_eq!(range.index(5), Some(2));
    /// assert_eq!(range.index(4), None); // 4 is not in [1,3,5,7,9]
    /// ```
    #[allow(dead_code)]
    pub fn index(&self, frame: i32) -> Option<usize> {
        self.frame_list.iter().position(|&x| x == frame)
    }

    /// Gets a reference to the complete frame sequence as a slice.
    ///
    /// # Returns
    ///
    /// A slice containing all frame numbers in order.
    ///
    /// # Example
    ///
    /// ```rust,ignore
    /// let range = FrameRange::new("1-5")?;
    /// assert_eq!(range.get_all(), &[1, 2, 3, 4, 5]);
    /// ```
    #[allow(dead_code)]
    pub fn get_all(&self) -> &[i32] {
        &self.frame_list
    }

    /// Parses a frame range specification string into a vector of frame numbers.
    ///
    /// This is the core parsing logic that handles all supported syntax patterns.
    /// It uses regex patterns to identify and parse different frame range formats.
    fn parse_frame_range(frame_range: &str) -> Result<Vec<i32>> {
        let single_frame_pattern = Regex::new(r"^(-?\d+)$").unwrap();
        let simple_range_pattern = Regex::new(r"^(?P<sf>-?\d+)-(?P<ef>-?\d+)$").unwrap();
        let step_pattern =
            Regex::new(r"^(?P<sf>-?\d+)-(?P<ef>-?\d+)(?P<stepSep>[xy])(?P<step>-?\d+)$").unwrap();
        let interleave_pattern =
            Regex::new(r"^(?P<sf>-?\d+)-(?P<ef>-?\d+):(?P<step>-?\d+)$").unwrap();

        if let Some(caps) = single_frame_pattern.captures(frame_range) {
            let frame: i32 = caps
                .get(1)
                .unwrap()
                .as_str()
                .parse()
                .into_diagnostic()
                .wrap_err(format!("Invalid frame number: {}", frame_range))?;
            return Ok(vec![frame]);
        }

        if let Some(caps) = simple_range_pattern.captures(frame_range) {
            let start_frame: i32 = caps
                .name("sf")
                .unwrap()
                .as_str()
                .parse()
                .into_diagnostic()
                .wrap_err("Invalid start frame".to_string())?;
            let end_frame: i32 = caps
                .name("ef")
                .unwrap()
                .as_str()
                .parse()
                .into_diagnostic()
                .wrap_err("Invalid end frame".to_string())?;
            let step = if end_frame >= start_frame { 1 } else { -1 };
            return Self::get_int_range(start_frame, end_frame, step);
        }

        if let Some(caps) = step_pattern.captures(frame_range) {
            let start_frame: i32 = caps
                .name("sf")
                .unwrap()
                .as_str()
                .parse()
                .into_diagnostic()
                .wrap_err("Invalid start frame".to_string())?;
            let end_frame: i32 = caps
                .name("ef")
                .unwrap()
                .as_str()
                .parse()
                .into_diagnostic()
                .wrap_err("Invalid end frame".to_string())?;
            let step: i32 = caps
                .name("step")
                .unwrap()
                .as_str()
                .parse()
                .into_diagnostic()
                .wrap_err("Invalid step".to_string())?;
            let step_sep = caps.name("stepSep").unwrap().as_str();
            let inverse_step = step_sep == "y";
            return Self::get_stepped_range(start_frame, end_frame, step, inverse_step);
        }

        if let Some(caps) = interleave_pattern.captures(frame_range) {
            let start_frame: i32 = caps
                .name("sf")
                .unwrap()
                .as_str()
                .parse()
                .into_diagnostic()
                .wrap_err("Invalid start frame".to_string())?;
            let end_frame: i32 = caps
                .name("ef")
                .unwrap()
                .as_str()
                .parse()
                .into_diagnostic()
                .wrap_err("Invalid end frame".to_string())?;
            let step: i32 = caps
                .name("step")
                .unwrap()
                .as_str()
                .parse()
                .into_diagnostic()
                .wrap_err("Invalid step".to_string())?;
            return Self::get_interleaved_range(start_frame, end_frame, step);
        }

        Err(miette!("Unrecognized frame range syntax: {}", frame_range))
    }

    /// Generates an integer range with the specified start, end, and step values.
    ///
    /// This method handles the core logic for generating frame sequences, including
    /// support for negative steps and proper filtering based on step intervals.
    fn get_int_range(start: i32, end: i32, step: i32) -> Result<Vec<i32>> {
        let (stream_start, stream_end) = if step < 0 { (end, start) } else { (start, end) };
        let stream_step = step.abs();

        let mut result = Vec::new();
        let mut current = stream_start;

        while current <= stream_end {
            if (current - start) % stream_step == 0 {
                result.push(current);
            }
            current += 1;
        }

        if step < 0 {
            result.reverse();
        }

        Ok(result)
    }

    /// Generates a stepped range, optionally with inverse stepping.
    ///
    /// For normal stepping (x syntax), returns frames at the specified intervals.
    /// For inverse stepping (y syntax), returns all frames EXCEPT those at the intervals.
    ///
    /// # Arguments
    /// * `start` - Starting frame number
    /// * `end` - Ending frame number
    /// * `step` - Step interval
    /// * `inverse_step` - If true, excludes stepped frames instead of including them
    fn get_stepped_range(start: i32, end: i32, step: i32, inverse_step: bool) -> Result<Vec<i32>> {
        Self::validate_step_sign(start, end, step)?;
        let stepped_range = Self::get_int_range(start, end, step)?;

        if inverse_step {
            let full_range = Self::get_int_range(start, end, if step < 0 { -1 } else { 1 })?;
            let stepped_set: std::collections::HashSet<_> = stepped_range.into_iter().collect();
            let result: Vec<i32> = full_range
                .into_iter()
                .filter(|x| !stepped_set.contains(x))
                .collect();
            Ok(result)
        } else {
            Ok(stepped_range)
        }
    }

    /// Generates an interleaved frame sequence for render optimization.
    ///
    /// The interleaved pattern distributes frames across the range to provide
    /// better early feedback during rendering. The algorithm progressively
    /// halves the step size to fill in gaps.
    ///
    /// Example: "1-10:5" produces [1, 6, 3, 5, 7, 9, 2, 4, 8, 10]
    fn get_interleaved_range(start: i32, end: i32, mut step: i32) -> Result<Vec<i32>> {
        Self::validate_step_sign(start, end, step)?;
        let mut interleaved_frames = IndexSet::new();

        while step.abs() > 0 {
            let range = Self::get_int_range(start, end, step)?;
            for frame in range {
                interleaved_frames.insert(frame);
            }
            step /= 2;
        }

        Ok(interleaved_frames.into_iter().collect())
    }

    /// Validates that the step direction is compatible with the range direction.
    ///
    /// Ensures that positive steps are only used with ascending ranges and
    /// negative steps are only used with descending ranges. Step size zero is invalid.
    fn validate_step_sign(start: i32, end: i32, step: i32) -> Result<()> {
        if step > 1 {
            if end < start {
                Err(miette!(
                    "End frame may not be less than start frame when using a positive step"
                ))
            } else {
                Ok(())
            }
        } else if step == 0 {
            Err(miette!("Step cannot be zero"))
        } else if step < 0 && end >= start {
            Err(miette!(
                "End frame may not be greater than start frame when using a negative step"
            ))
        } else {
            Ok(())
        }
    }
}

/// Represents an ordered sequence of FrameRanges combined into a single frame list.
///
/// A `FrameSet` allows combining multiple frame range specifications using comma-separated
/// syntax. Each section is parsed as a `FrameRange` and the results are concatenated.
///
/// This is a direct port of the Java `FrameSet` class from OpenCue's codebot.
///
/// # Syntax
///
/// Frame sets use comma-separated frame range specifications:
/// - `"1-10"` - Simple range: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
/// - `"1-5,10-15"` - Multiple ranges: [1, 2, 3, 4, 5, 10, 11, 12, 13, 14, 15]
/// - `"1-10x2,20,25-30"` - Mixed syntax: [1, 3, 5, 7, 9, 20, 25, 26, 27, 28, 29, 30]
/// - `"1-5x2, 10-15, 20"` - Whitespace is trimmed automatically
///
/// # Job Distribution
///
/// FrameSet provides chunking functionality for distributing frames across render nodes:
///
/// ```rust,ignore
/// let frame_set = FrameSet::new("1-100")?;
/// let chunk1 = frame_set.get_chunk(0, 10)?;   // "1-10"
/// let chunk2 = frame_set.get_chunk(10, 10)?;  // "11-20"
/// ```
///
/// Chunks are returned as compact string representations that can be parsed by render nodes.
///
/// # Examples
///
/// ```rust,ignore
/// // Basic frame set
/// let frames = FrameSet::new("1-5,10-12")?;
/// assert_eq!(frames.get_all(), &[1, 2, 3, 4, 5, 10, 11, 12]);
/// assert_eq!(frames.size(), 8);
///
/// // Complex frame set with different syntaxes
/// let complex = FrameSet::new("1-10x2,15,20-25")?;
/// assert_eq!(complex.get_all(), &[1, 3, 5, 7, 9, 15, 20, 21, 22, 23, 24, 25]);
///
/// // Chunking for job distribution
/// let chunk = complex.get_chunk(0, 3)?; // First 3 frames
/// // Returns compact representation like "1-5x2,15"
/// ```
#[derive(Debug, Clone, PartialEq)]
#[allow(dead_code)]
pub struct FrameSet {
    frame_list: Vec<i32>,
}

impl FrameSet {
    /// Constructs a new `FrameSet` by parsing a comma-separated frame range specification.
    ///
    /// # Arguments
    ///
    /// * `frame_range` - Comma-separated frame range specifications
    ///
    /// # Returns
    ///
    /// * `Ok(FrameSet)` - Successfully parsed frame set
    /// * `Err(String)` - Parse error with description
    ///
    /// # Examples
    ///
    /// ```rust,ignore
    /// let simple = FrameSet::new("1-10")?;
    /// let multi = FrameSet::new("1-5,10-15")?;
    /// let complex = FrameSet::new("1-10x2, 20, 25-30")?;
    /// ```
    pub fn new(frame_range: &str) -> Result<Self> {
        let frame_list = Self::parse_frame_range(frame_range)?;
        Ok(FrameSet { frame_list })
    }

    /// Gets the total number of frames in this frame set.
    ///
    /// # Returns
    ///
    /// The total count of frames across all ranges.
    #[allow(dead_code)]
    pub fn size(&self) -> usize {
        self.frame_list.len()
    }

    /// Gets an individual frame number by its position in the sequence.
    ///
    /// # Arguments
    ///
    /// * `idx` - Zero-based index into the frame sequence
    ///
    /// # Returns
    ///
    /// * `Some(frame_number)` - If the index is valid
    /// * `None` - If the index is out of bounds
    #[allow(dead_code)]
    pub fn get(&self, idx: usize) -> Option<i32> {
        self.frame_list.get(idx).copied()
    }

    /// Gets last individual frame number.
    ///
    /// # Returns
    ///
    /// * `Some(frame_number)` - If set not empty
    /// * `None` - Otherwise
    pub fn last(&self) -> Option<i32> {
        self.frame_list.last().cloned()
    }

    /// Finds the index of a specific frame number in the sequence.
    ///
    /// # Arguments
    ///
    /// * `frame` - The frame number to search for
    ///
    /// # Returns
    ///
    /// * `Some(index)` - Zero-based index if found
    /// * `None` - If the frame is not in the set
    pub fn index(&self, frame: i32) -> Option<usize> {
        self.frame_list.iter().position(|&x| x == frame)
    }

    /// Gets a reference to the complete frame sequence as a slice.
    ///
    /// # Returns
    ///
    /// A slice containing all frame numbers in the order they were specified.
    #[allow(dead_code)]
    pub fn get_all(&self) -> &[i32] {
        &self.frame_list
    }

    /// Returns a sub-FrameSet as a compact string representation for job distribution.
    ///
    /// This method is used to divide frame sets into smaller chunks for distribution
    /// across render nodes. The returned string uses the most compact frame range
    /// representation possible.
    ///
    /// # Arguments
    ///
    /// * `start_frame_index` - Zero-based index of the first frame to include
    /// * `chunk_size` - Maximum number of frames to include in the chunk
    ///
    /// # Returns
    ///
    /// * `Ok(String)` - Compact frame range representation (e.g., "1-10", "1,3,5", "10-20x2")
    /// * `Err(String)` - If start_frame_index is out of bounds
    ///
    /// # Examples
    ///
    /// ```rust,ignore
    /// let frames = FrameSet::new("1-20")?;
    /// assert_eq!(frames.get_chunk(0, 5)?, "1-5");
    /// assert_eq!(frames.get_chunk(5, 5)?, "6-10");
    ///
    /// let stepped = FrameSet::new("1-10x2")?; // [1, 3, 5, 7, 9]
    /// assert_eq!(stepped.get_chunk(1, 3)?, "3-7x2"); // [3, 5, 7]
    /// ```
    ///
    /// # Errors
    ///
    /// Returns an error if `start_frame_index` is greater than or equal to the
    /// total number of frames in the set.
    pub fn get_chunk(&self, start_frame_index: usize, chunk_size: usize) -> Result<String> {
        if self.frame_list.len() <= start_frame_index {
            Err(miette!(
                "startFrameIndex {} is not in range 0-{}",
                start_frame_index,
                self.frame_list.len() - 1
            ))?;
        }

        if chunk_size == 1 {
            return Ok(self.frame_list[start_frame_index].to_string());
        }

        let final_frame_index = self.frame_list.len() - 1;
        let mut end_frame_index = start_frame_index + chunk_size - 1;
        if end_frame_index > final_frame_index {
            end_frame_index = final_frame_index;
        }

        let subset = &self.frame_list[start_frame_index..=end_frame_index];
        Ok(Self::frames_to_frame_ranges(subset))
    }

    /// Parses a comma-separated frame range specification into a vector of frame numbers.
    ///
    /// Each comma-separated section is parsed as an individual FrameRange and the
    /// results are concatenated in order.
    fn parse_frame_range(frame_range: &str) -> Result<Vec<i32>> {
        let mut result = Vec::new();
        for frame_range_section in frame_range.split(',') {
            let section_frames = FrameRange::parse_frame_range(frame_range_section.trim())?;
            result.extend(section_frames);
        }
        Ok(result)
    }

    /// Builds a compact string representation for a frame range part.
    ///
    /// Returns the most compact representation:
    /// - Single frame: "5"
    /// - Consecutive frames: "1-10"
    /// - Stepped frames: "1-10x2"
    fn build_frame_part(start_frame: i32, end_frame: i32, step: i32) -> String {
        if start_frame == end_frame {
            start_frame.to_string()
        } else if step == 1 {
            format!("{}-{}", start_frame, end_frame)
        } else {
            format!("{}-{}x{}", start_frame, end_frame, step)
        }
    }

    /// Converts a list of frame numbers back to the most compact frame range representation.
    ///
    /// This method analyzes the frame sequence to detect patterns and produces
    /// the most compact string representation possible. It's adapted from the
    /// Python Fileseq library approach used in the original Java implementation.
    ///
    /// # Arguments
    ///
    /// * `frames` - Slice of frame numbers in ascending order
    ///
    /// # Returns
    ///
    /// Compact frame range string (e.g., "1-10", "1-10x2", "1,3,5,10-15")
    fn frames_to_frame_ranges(frames: &[i32]) -> String {
        let l = frames.len();
        if l == 0 {
            return String::new();
        } else if l == 1 {
            return frames[0].to_string();
        }

        let mut result_parts = Vec::new();
        let mut curr_count = 1;
        let mut curr_step = 0;
        let mut curr_start = frames[0];
        let mut last_frame = frames[0];

        for &curr_frame in frames.iter().skip(1) {
            if curr_step == 0 {
                curr_step = curr_frame - curr_start;
            }
            let new_step = curr_frame - last_frame;

            if curr_step == new_step {
                last_frame = curr_frame;
                curr_count += 1;
            } else if curr_count == 2 && curr_step != 1 {
                result_parts.push(curr_start.to_string());
                curr_step = 0;
                curr_start = last_frame;
                last_frame = curr_frame;
            } else {
                result_parts.push(Self::build_frame_part(curr_start, last_frame, curr_step));
                curr_step = 0;
                curr_start = curr_frame;
                last_frame = curr_frame;
                curr_count = 1;
            }
        }

        if curr_count == 2 && curr_step != 1 {
            result_parts.push(curr_start.to_string());
            result_parts.push(frames[frames.len() - 1].to_string());
        } else {
            result_parts.push(Self::build_frame_part(
                curr_start,
                frames[frames.len() - 1],
                curr_step,
            ));
        }

        result_parts.join(",")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Basic functionality tests
    #[test]
    fn test_single_frame() {
        let frame_range = FrameRange::new("5").unwrap();
        assert_eq!(frame_range.get_all(), &[5]);
    }

    #[test]
    fn test_single_frame_negative() {
        let frame_range = FrameRange::new("-5").unwrap();
        assert_eq!(frame_range.get_all(), &[-5]);
    }

    #[test]
    fn test_simple_range() {
        let frame_range = FrameRange::new("1-5").unwrap();
        assert_eq!(frame_range.get_all(), &[1, 2, 3, 4, 5]);
    }

    #[test]
    fn test_simple_range_negative() {
        let frame_range = FrameRange::new("-5--1").unwrap();
        assert_eq!(frame_range.get_all(), &[-5, -4, -3, -2, -1]);
    }

    // Stepped range tests (x syntax)
    #[test]
    fn test_stepped_range_basic() {
        let frame_range = FrameRange::new("1-10x2").unwrap();
        assert_eq!(frame_range.get_all(), &[1, 3, 5, 7, 9]);
    }

    #[test]
    fn test_stepped_range_documented_example() {
        let frame_range = FrameRange::new("1-10x3").unwrap();
        assert_eq!(frame_range.get_all(), &[1, 4, 7, 10]);
    }

    #[test]
    fn test_stepped_range_step_of_one() {
        let frame_range = FrameRange::new("1-5x1").unwrap();
        assert_eq!(frame_range.get_all(), &[1, 2, 3, 4, 5]);
    }

    #[test]
    fn test_stepped_range_large_step() {
        let frame_range = FrameRange::new("1-10x5").unwrap();
        assert_eq!(frame_range.get_all(), &[1, 6]);
    }

    // Negative stepped range tests
    #[test]
    fn test_negative_stepped_range() {
        let frame_range = FrameRange::new("10-1x-1").unwrap();
        assert_eq!(frame_range.get_all(), &[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]);
    }

    #[test]
    fn test_negative_stepped_range_with_step() {
        let frame_range = FrameRange::new("10-1x-2").unwrap();
        assert_eq!(frame_range.get_all(), &[10, 8, 6, 4, 2]);
    }

    // Inverse stepped range tests (y syntax)
    #[test]
    fn test_inverse_stepped_range_documented_example() {
        let frame_range = FrameRange::new("1-10y3").unwrap();
        assert_eq!(frame_range.get_all(), &[2, 3, 5, 6, 8, 9]);
    }

    #[test]
    fn test_inverse_stepped_range_step_2() {
        let frame_range = FrameRange::new("1-10y2").unwrap();
        assert_eq!(frame_range.get_all(), &[2, 4, 6, 8, 10]);
    }

    #[test]
    fn test_inverse_stepped_range_step_1() {
        let frame_range = FrameRange::new("1-5y1").unwrap();
        assert_eq!(frame_range.get_all(), &[] as &[i32]);
    }

    // Interleaved range tests (: syntax)
    #[test]
    fn test_interleaved_range_documented_example() {
        let frame_range = FrameRange::new("1-10:5").unwrap();
        // Actual output from our implementation
        assert_eq!(frame_range.get_all(), &[1, 6, 3, 5, 7, 9, 2, 4, 8, 10]);
    }

    #[test]
    fn test_interleaved_range_step_2() {
        let frame_range = FrameRange::new("1-8:2").unwrap();
        assert_eq!(frame_range.get_all(), &[1, 3, 5, 7, 2, 4, 6, 8]);
    }

    #[test]
    fn test_interleaved_range_step_4() {
        let frame_range = FrameRange::new("1-8:4").unwrap();
        // Actual output from our implementation
        assert_eq!(frame_range.get_all(), &[1, 5, 3, 7, 2, 4, 6, 8]);
    }

    // Error cases and validation
    #[test]
    fn test_step_zero_error() {
        let result = FrameRange::new("1-10x0");
        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("Step cannot be zero"));
    }

    #[test]
    fn test_positive_step_with_descending_range_error() {
        let result = FrameRange::new("10-1x2");
        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("End frame may not be less than start frame when using a positive step"));
    }

    #[test]
    fn test_negative_step_with_ascending_range_error() {
        let result = FrameRange::new("1-10x-2");
        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("End frame may not be greater than start frame when using a negative step"));
    }

    #[test]
    fn test_invalid_syntax_error() {
        let result = FrameRange::new("1-10z2");
        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("Unrecognized frame range syntax"));
    }

    #[test]
    fn test_malformed_range_error() {
        let result = FrameRange::new("abc");
        assert!(result.is_err());
    }

    // FrameSet tests
    #[test]
    fn test_frame_set_simple() {
        let frame_set = FrameSet::new("1-3,5-7").unwrap();
        assert_eq!(frame_set.get_all(), &[1, 2, 3, 5, 6, 7]);
    }

    #[test]
    fn test_frame_set_mixed_syntax() {
        let frame_set = FrameSet::new("1-5x2,10,15-20").unwrap();
        assert_eq!(frame_set.get_all(), &[1, 3, 5, 10, 15, 16, 17, 18, 19, 20]);
    }

    #[test]
    fn test_frame_set_with_spaces() {
        let frame_set = FrameSet::new("1-3, 5-7, 10").unwrap();
        assert_eq!(frame_set.get_all(), &[1, 2, 3, 5, 6, 7, 10]);
    }

    #[test]
    fn test_frame_set_single_frame() {
        let frame_set = FrameSet::new("42").unwrap();
        assert_eq!(frame_set.get_all(), &[42]);
    }

    // Chunk tests
    #[test]
    fn test_frame_set_get_chunk() {
        let frame_set = FrameSet::new("1-10").unwrap();
        let chunk = frame_set.get_chunk(0, 3).unwrap();
        assert_eq!(chunk, "1-3");
    }

    #[test]
    fn test_frame_set_get_chunk_single() {
        let frame_set = FrameSet::new("1-10").unwrap();
        let chunk = frame_set.get_chunk(2, 1).unwrap();
        assert_eq!(chunk, "3");
    }

    #[test]
    fn test_frame_set_get_chunk_end_of_range() {
        let frame_set = FrameSet::new("1-10").unwrap();
        let chunk = frame_set.get_chunk(7, 5).unwrap(); // Should only get frames 8,9,10
        assert_eq!(chunk, "8-10");
    }

    #[test]
    fn test_frame_set_get_chunk_out_of_bounds() {
        let frame_set = FrameSet::new("1-5").unwrap();
        let result = frame_set.get_chunk(10, 3);
        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("startFrameIndex 10 is not in range 0-4"));
    }

    #[test]
    fn test_frame_set_get_chunk_stepped_frames() {
        let frame_set = FrameSet::new("1-10x2").unwrap(); // [1, 3, 5, 7, 9]
        let chunk = frame_set.get_chunk(1, 3).unwrap(); // Should get [3, 5, 7]
        assert_eq!(chunk, "3-7x2");
    }

    // Frame range reconstruction tests
    #[test]
    fn test_frames_to_frame_ranges_simple() {
        let frames = &[1, 2, 3, 5, 6, 7];
        let result = FrameSet::frames_to_frame_ranges(frames);
        assert_eq!(result, "1-3,5-7");
    }

    #[test]
    fn test_frames_to_frame_ranges_stepped() {
        let frames = &[1, 3, 5, 7, 9];
        let result = FrameSet::frames_to_frame_ranges(frames);
        assert_eq!(result, "1-9x2");
    }

    #[test]
    fn test_frames_to_frame_ranges_single_frame() {
        let frames = &[42];
        let result = FrameSet::frames_to_frame_ranges(frames);
        assert_eq!(result, "42");
    }

    #[test]
    fn test_frames_to_frame_ranges_empty() {
        let frames = &[];
        let result = FrameSet::frames_to_frame_ranges(frames);
        assert_eq!(result, "");
    }

    #[test]
    fn test_frames_to_frame_ranges_mixed() {
        let frames = &[1, 3, 5, 10, 11, 12];
        let result = FrameSet::frames_to_frame_ranges(frames);
        assert_eq!(result, "1-5x2,10-12");
    }

    #[test]
    fn test_frames_to_frame_ranges_single_gaps() {
        let frames = &[1, 3, 5];
        let result = FrameSet::frames_to_frame_ranges(frames);
        assert_eq!(result, "1-5x2");
    }

    // Edge cases
    #[test]
    fn test_frame_range_single_element_range() {
        let frame_range = FrameRange::new("5-5").unwrap();
        assert_eq!(frame_range.get_all(), &[5]);
    }

    #[test]
    fn test_frame_range_backwards_single_step() {
        let frame_range = FrameRange::new("5-1").unwrap();
        assert_eq!(frame_range.get_all(), &[5, 4, 3, 2, 1]);
    }

    #[test]
    fn test_complex_frame_set() {
        let frame_set = FrameSet::new("1-5x2,10-15,20-30x3,50").unwrap();
        let expected = [1, 3, 5, 10, 11, 12, 13, 14, 15, 20, 23, 26, 29, 50];
        assert_eq!(frame_set.get_all(), &expected);
    }
}
