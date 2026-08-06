/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

// Frame-spec validator that mirrors what cuebot itself accepts. Built
// from FileSequence / FrameSet behavior in OpenCue.
//
// Accepted forms (separated by commas):
//   5            single frame
//   1-10         inclusive range
//   1-10x2       range with step
//   1-10y2       range with reverse step (every Nth dropped)
//   1-10:2       interleave
// Examples:
//   "1-5"
//   "1-100x2,200,300-310"

const SEGMENT_RE = /^\d+(-\d+([xy:]\d+)?)?$/;

export function isValidFrameSpec(value: string): boolean {
  if (!value) return false;
  const trimmed = value.trim();
  if (!trimmed) return false;
  const segments = trimmed.split(",").map((s) => s.trim());
  if (segments.length === 0) return false;
  for (const segment of segments) {
    if (!SEGMENT_RE.test(segment)) return false;
    // Range sanity: start must be <= end (cuebot rejects "10-1").
    const rangeMatch = /^(\d+)-(\d+)([xy:]\d+)?$/.exec(segment);
    if (rangeMatch) {
      const start = Number(rangeMatch[1]);
      const end = Number(rangeMatch[2]);
      if (start > end) return false;
      // Reject zero step values (e.g. "1-10x0" / "1-10:0"). Cuebot
      // would otherwise be asked to divide by zero when expanding the
      // range; the form should fail validation up front.
      if (rangeMatch[3]) {
        const step = Number(rangeMatch[3].slice(1));
        if (step === 0) return false;
      }
    }
  }
  return true;
}

/**
 * Returns the first frame number from a frame spec, or null when the
 * spec is empty / invalid. Used by command builders that need a
 * concrete start frame (rare; cuebot substitutes #FRAME_START# at
 * dispatch).
 */
export function firstFrame(value: string): number | null {
  if (!isValidFrameSpec(value)) return null;
  const firstSegment = value.split(",")[0].trim();
  const m = /^(\d+)/.exec(firstSegment);
  return m ? Number(m[1]) : null;
}

/**
 * Returns true when the spec is a single simple range like "1-10".
 * Blender's `-a` flag needs this distinction (it renders the range in
 * one process instead of one frame at a time).
 */
export function isSimpleRange(value: string): boolean {
  return /^\d+-\d+$/.test(value.trim());
}
