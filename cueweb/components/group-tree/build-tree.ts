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

export type TreeNode = {
  group: Group;
  children: TreeNode[];
};

// Converts the flat list returned by ShowInterface.GetGroups into a nested tree
// rooted at the show's root group (parentId === ""). Orphan groups whose parentId
// references a missing group are dropped. Returns null if no root is present.
export function buildTreeFromGroups(groups: Group[]): TreeNode | null {
  if (groups.length === 0) return null;

  const byId = new Map<string, TreeNode>();
  for (const g of groups) {
    byId.set(g.id, { group: g, children: [] });
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
  return root;
}
