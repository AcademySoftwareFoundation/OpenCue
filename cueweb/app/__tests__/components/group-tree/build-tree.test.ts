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

import { buildTreeFromGroups } from "@/components/group-tree/build-tree";
import type { Group } from "@/app/utils/get_utils";

// Helper to build a minimal Group with sane defaults. Only id, name, parentId matter to the tree builder.
const g = (id: string, parentId: string, name = id): Group => ({
    id,
    name,
    parentId,
    department: "",
    defaultJobPriority: -1,
    defaultJobMinCores: -1,
    defaultJobMaxCores: -1,
    minCores: 0,
    maxCores: -1,
    level: parentId ? 1 : 0,
});

describe("buildTreeFromGroups", () => {
    it("returns null for an empty list", () => {
        expect(buildTreeFromGroups([])).toBeNull();
    });

    it("returns a single-node tree when only the root group is present", () => {
        const root = g("root", "");
        const tree = buildTreeFromGroups([root]);
        expect(tree).toEqual({ group: root, children: [] });
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
});
