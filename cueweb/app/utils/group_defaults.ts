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

import type { Group } from "@/app/utils/get_utils";

// Cuebot encodes "no default" as -1, so only surface values that differ from it.
const FEATURE_DISABLED = -1;

// Compact summary of the defaults a group applies on reparent, e.g.
// "Dept: comp · Priority: 100 · Cores: 1–8"; "" when nothing is set. (GPU
// defaults omitted — the Group type has no GPU fields yet.)
export function formatGroupDefaults(group: Group): string {
  const parts: string[] = [];

  if (group.department) {
    parts.push(`Dept: ${group.department}`);
  }

  if (group.defaultJobPriority !== FEATURE_DISABLED) {
    parts.push(`Priority: ${group.defaultJobPriority}`);
  }

  const hasMin = group.defaultJobMinCores !== FEATURE_DISABLED;
  const hasMax = group.defaultJobMaxCores !== FEATURE_DISABLED;
  if (hasMin && hasMax) {
    parts.push(`Cores: ${group.defaultJobMinCores}–${group.defaultJobMaxCores}`);
  } else if (hasMin) {
    parts.push(`Cores: ≥${group.defaultJobMinCores}`);
  } else if (hasMax) {
    parts.push(`Cores: ≤${group.defaultJobMaxCores}`);
  }

  return parts.join(" · ");
}
