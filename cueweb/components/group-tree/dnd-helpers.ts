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
import type { Job } from "@/app/jobs/columns";

export type JobsState = Map<string, Job[] | "loading">;

// True when groupId may move under targetGroupId; rejects self, descendant
// (cycle), current parent (no-op), and missing groups.
export function canReparentGroup(
  groups: Group[],
  groupId: string,
  targetGroupId: string,
): boolean {
  if (groupId === targetGroupId) return false;

  const source = groups.find(g => g.id === groupId);
  if (!source) return false;

  const targetExists = groups.some(g => g.id === targetGroupId);
  if (!targetExists) return false;

  if (source.parentId === targetGroupId) return false;

  // BFS from groupId; if we reach targetGroupId via children, it's a descendant.
  const childrenOf = new Map<string, string[]>();
  for (const g of groups) {
    if (!g.parentId) continue;
    const arr = childrenOf.get(g.parentId) ?? [];
    arr.push(g.id);
    childrenOf.set(g.parentId, arr);
  }

  // `seen` guards against cycles in the parentId data (would otherwise spin).
  const stack = [groupId];
  const seen = new Set<string>();
  while (stack.length) {
    const id = stack.pop()!;
    if (seen.has(id)) continue;
    seen.add(id);
    const kids = childrenOf.get(id) ?? [];
    for (const kid of kids) {
      if (kid === targetGroupId) return false;
      stack.push(kid);
    }
  }

  return true;
}

// Returns a new groups array with groupId's parentId updated (no-op if missing).
export function applyGroupReparent(
  groups: Group[],
  groupId: string,
  newParentId: string,
): Group[] {
  return groups.map(g => (g.id === groupId ? { ...g, parentId: newParentId } : g));
}

// Moves a job between groups' cached lists. Appends to the target only if it's
// already loaded; returns the same Map reference on a no-op.
export function applyJobReparent(
  jobsByGroup: JobsState,
  jobId: string,
  fromGroupId: string,
  toGroupId: string,
): JobsState {
  if (fromGroupId === toGroupId) return jobsByGroup;

  const fromJobs = jobsByGroup.get(fromGroupId);
  if (!Array.isArray(fromJobs)) return jobsByGroup;

  const movedJob = fromJobs.find(j => j.id === jobId);
  if (!movedJob) return jobsByGroup;

  const next: JobsState = new Map(jobsByGroup);
  next.set(fromGroupId, fromJobs.filter(j => j.id !== jobId));

  const toJobs = jobsByGroup.get(toGroupId);
  if (Array.isArray(toJobs)) {
    next.set(toGroupId, [...toJobs, movedJob]);
  }

  return next;
}
