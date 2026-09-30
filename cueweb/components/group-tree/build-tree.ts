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

import type { Group, GroupStats } from "@/app/utils/get_utils";

export type TreeNode = {
  group: Group;
  children: TreeNode[];
  rolledUpStats: GroupStats;
};

export const ZERO_STATS: GroupStats = {
  runningFrames: 0,
  deadFrames: 0,
  dependFrames: 0,
  waitingFrames: 0,
  pendingJobs: 0,
  reservedCores: 0,
  reservedGpus: 0,
};

function addStats(a: GroupStats, b: GroupStats): GroupStats {
  return {
    runningFrames: a.runningFrames + b.runningFrames,
    deadFrames: a.deadFrames + b.deadFrames,
    dependFrames: a.dependFrames + b.dependFrames,
    waitingFrames: a.waitingFrames + b.waitingFrames,
    pendingJobs: a.pendingJobs + b.pendingJobs,
    reservedCores: a.reservedCores + b.reservedCores,
    reservedGpus: a.reservedGpus + b.reservedGpus,
  };
}

// Post-order: each node's rolledUpStats = own stats + children's rolled-up stats.
function computeRollup(node: TreeNode): GroupStats {
  const own = node.group.groupStats ?? ZERO_STATS;
  const summed = node.children.reduce(
    (acc, child) => addStats(acc, computeRollup(child)),
    own,
  );
  node.rolledUpStats = summed;
  return summed;
}

// Flat group list -> tree rooted at the show's root (parentId === ""). Orphans
// (parent missing/unreachable) are dropped; null if there's no root.
export function buildTreeFromGroups(groups: Group[]): TreeNode | null {
  if (groups.length === 0) return null;

  const byId = new Map<string, TreeNode>();
  for (const g of groups) {
    byId.set(g.id, { group: g, children: [], rolledUpStats: ZERO_STATS });
  }

  let root: TreeNode | null = null;
  for (const g of groups) {
    const node = byId.get(g.id)!;
    if (!g.parentId) {
      if (!root) root = node;
      continue;
    }
    const parent = byId.get(g.parentId);
    if (parent) parent.children.push(node);
  }

  if (root) computeRollup(root);
  return root;
}
