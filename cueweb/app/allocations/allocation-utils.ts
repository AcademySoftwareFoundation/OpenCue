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

import { Allocation, Host } from "@/app/utils/get_utils";

// Allocation row enriched with the host-state columns CueGUI's Allocations
// window derives from the host list (AllocationStats does not expose them):
//   - downCores / repairCores: cores on this allocation's DOWN / REPAIR hosts
//   - repairHosts: count of this allocation's hosts in REPAIR
export type AllocationRow = Allocation & {
  downCores: number;
  repairCores: number;
  repairHosts: number;
};

export type AllocationHostStats = {
  downCores: number;
  repairCores: number;
  repairHosts: number;
};

// Aggregate the host list into per-allocation host-state stats keyed by the
// host's allocName (which matches Allocation.name). Pure + exported for tests.
export function computeAllocationHostStats(
  hosts: Host[],
): Record<string, AllocationHostStats> {
  const acc: Record<string, AllocationHostStats> = {};
  for (const h of hosts) {
    const key = h.allocName;
    if (!key) continue;
    if (!acc[key]) acc[key] = { downCores: 0, repairCores: 0, repairHosts: 0 };
    if (h.state === "DOWN") acc[key].downCores += h.cores;
    if (h.state === "REPAIR") {
      acc[key].repairCores += h.cores;
      acc[key].repairHosts += 1;
    }
  }
  return acc;
}

// Build the enriched rows the table renders from the allocations + host stats.
export function buildAllocationRows(
  allocations: Allocation[],
  hostStats: Record<string, AllocationHostStats>,
): AllocationRow[] {
  return allocations.map((a) => {
    const s = hostStats[a.name] ?? { downCores: 0, repairCores: 0, repairHosts: 0 };
    return { ...a, ...s };
  });
}
