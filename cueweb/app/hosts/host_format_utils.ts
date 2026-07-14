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

import { convertMemoryToString } from "@/app/utils/layers_frames_utils";

// The gateway sends memory / mcp sizes as KB strings (e.g. "6815744").
// Non-numeric input becomes 0 so callers never get NaN.
export function kbStringToNumber(kb: string): number {
  const n = Number(kb);
  return Number.isFinite(n) ? n : 0;
}

export function kbStringToHuman(kb: string): string {
  const n = Number(kb);
  // Number("") === 0 (finite), so guard "" explicitly to show "-" not "0K".
  if (kb === "" || !Number.isFinite(n)) {
    return "-";
  }
  return convertMemoryToString(n, "host");
}

// Guards divide-by-zero; used as a numeric sort key.
export function idleRatio(idle: number, total: number): number {
  if (!total) return 0;
  return idle / total;
}
