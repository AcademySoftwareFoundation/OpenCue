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

import { buildTreeFromGroups, ZERO_STATS } from "@/components/group-tree/build-tree";
import type { Group, GroupStats } from "@/app/utils/get_utils";

// Helper to build a minimal Group with sane defaults. Only id, name, parentId
// (and optionally groupStats) matter to the tree builder + rollup.
const g = (id: string, parentId: string, groupStats?: GroupStats): Group => ({
    id,
    name: id,
    parentId,
    department: "",
    defaultJobPriority: -1,
    defaultJobMinCores: -1,
    defaultJobMaxCores: -1,
    minCores: 0,
    maxCores: -1,
    level: parentId ? 1 : 0,
    groupStats,
});

// Build a GroupStats with the named counters set; everything else stays 0.
const stats = (overrides: Partial<GroupStats>): GroupStats => ({
    ...ZERO_STATS,
    ...overrides,
});

describe("buildTreeFromGroups", () => {
    it("returns null for an empty list", () => {
        expect(buildTreeFromGroups([])).toBeNull();
    });

    it("returns a single-node tree when only the root group is present", () => {
        const root = g("root", "");
        const tree = buildTreeFromGroups([root]);
        expect(tree?.group).toEqual(root);
        expect(tree?.children).toEqual([]);
    });

    it("nests two children under their shared root", () => {
        const root = g("root", "");
        const childA = g("a", "root");
        const childB = g("b", "root");
        const tree = buildTreeFromGroups([root, childA, childB]);
        expect(tree?.group).toEqual(root);
        expect(tree?.children).toHaveLength(2);
        expect(tree?.children.map(c => c.group.id).sort()).toEqual(["a", "b"]);
        expect(tree?.children.every(c => c.children.length === 0)).toBe(true);
    });

    it("builds a three-level chain root → mid → leaf", () => {
        const root = g("root", "");
        const mid = g("mid", "root");
        const leaf = g("leaf", "mid");
        const tree = buildTreeFromGroups([root, mid, leaf]);
        expect(tree?.children).toHaveLength(1);
        expect(tree?.children[0].group.id).toBe("mid");
        expect(tree?.children[0].children).toHaveLength(1);
        expect(tree?.children[0].children[0].group.id).toBe("leaf");
    });

    it("drops orphan groups whose parentId references a missing group", () => {
        const root = g("root", "");
        const orphan = g("orphan", "ghost");
        const tree = buildTreeFromGroups([root, orphan]);
        expect(tree?.children).toHaveLength(0);
    });

    it("returns null when no root (parentId='') is present", () => {
        const a = g("a", "missing");
        const b = g("b", "also-missing");
        expect(buildTreeFromGroups([a, b])).toBeNull();
    });

    it("drops cycle-stranded groups without hanging", () => {
        // x <-> y are each other's parent (cycle); must terminate and exclude them.
        const root = g("root", "");
        const x = g("x", "y");
        const y = g("y", "x");
        const tree = buildTreeFromGroups([root, x, y]);
        expect(tree?.group.id).toBe("root");
        expect(tree?.children).toHaveLength(0);
    });
});

describe("buildTreeFromGroups rollup", () => {
    it("sets rolledUpStats to zeros for a leaf group with no own groupStats", () => {
        const root = g("root", "");
        const tree = buildTreeFromGroups([root]);
        expect(tree?.rolledUpStats).toEqual(ZERO_STATS);
    });

    it("uses own stats for a leaf group", () => {
        const root = g("root", "", stats({ pendingJobs: 3, runningFrames: 5 }));
        const tree = buildTreeFromGroups([root]);
        expect(tree?.rolledUpStats).toMatchObject({ pendingJobs: 3, runningFrames: 5 });
    });

    it("sums own stats with direct children stats", () => {
        const root = g("root", "", stats({ pendingJobs: 1, runningFrames: 2 }));
        const a = g("a", "root", stats({ pendingJobs: 3, runningFrames: 4 }));
        const b = g("b", "root", stats({ pendingJobs: 5, runningFrames: 6 }));
        const tree = buildTreeFromGroups([root, a, b]);
        expect(tree?.rolledUpStats).toMatchObject({
            pendingJobs: 1 + 3 + 5,
            runningFrames: 2 + 4 + 6,
        });
    });

    it("rolls up recursively across multiple levels", () => {
        const root = g("root", "", stats({ pendingJobs: 1 }));
        const mid = g("mid", "root", stats({ pendingJobs: 2 }));
        const leaf = g("leaf", "mid", stats({ pendingJobs: 4 }));
        const tree = buildTreeFromGroups([root, mid, leaf]);
        expect(tree?.rolledUpStats.pendingJobs).toBe(1 + 2 + 4);
        expect(tree?.children[0].rolledUpStats.pendingJobs).toBe(2 + 4);
        expect(tree?.children[0].children[0].rolledUpStats.pendingJobs).toBe(4);
    });

    it("treats missing groupStats as zero in mixed trees", () => {
        const root = g("root", "");
        const a = g("a", "root", stats({ pendingJobs: 5 }));
        const b = g("b", "root");
        const tree = buildTreeFromGroups([root, a, b]);
        expect(tree?.rolledUpStats.pendingJobs).toBe(5);
    });
});
