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

import {
    applyGroupReparent,
    applyJobReparent,
    canReparentGroup,
} from "@/components/group-tree/dnd-helpers";
import type { Group } from "@/app/utils/get_utils";
import type { Job } from "@/app/jobs/columns";

const mkGroup = (id: string, parentId: string): Group => ({
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
});

const mkJob = (id: string): Job => ({ id, name: id } as Job);

// Shared tree:
//   root
//   ├── a
//   │   └── c
//   │       └── d
//   └── b
const tree: Group[] = [
    mkGroup("root", ""),
    mkGroup("a", "root"),
    mkGroup("b", "root"),
    mkGroup("c", "a"),
    mkGroup("d", "c"),
];

describe("canReparentGroup", () => {
    it("rejects dropping a group onto itself", () => {
        expect(canReparentGroup(tree, "a", "a")).toBe(false);
    });

    it("rejects dropping a group onto an immediate descendant", () => {
        expect(canReparentGroup(tree, "a", "c")).toBe(false);
    });

    it("rejects dropping a group onto a deep descendant", () => {
        expect(canReparentGroup(tree, "a", "d")).toBe(false);
    });

    it("rejects dropping a group onto its current parent (no-op)", () => {
        expect(canReparentGroup(tree, "a", "root")).toBe(false);
    });

    it("allows dropping a group onto a sibling", () => {
        expect(canReparentGroup(tree, "a", "b")).toBe(true);
    });

    it("allows dropping a group onto its parent's sibling (uncle)", () => {
        expect(canReparentGroup(tree, "c", "b")).toBe(true);
    });

    it("rejects when the source group is missing", () => {
        expect(canReparentGroup(tree, "ghost", "a")).toBe(false);
    });

    it("rejects when the target group is missing", () => {
        expect(canReparentGroup(tree, "a", "ghost")).toBe(false);
    });

    it("terminates (no infinite loop) when parentIds form a cycle", () => {
        // x <-> y are each other's parent (cycle); the walk must still terminate.
        const cyclic: Group[] = [
            mkGroup("root", ""),
            { ...mkGroup("x", "y") },
            { ...mkGroup("y", "x") },
        ];
        // y is reachable as a descendant of x via the cycle -> reject.
        expect(canReparentGroup(cyclic, "x", "y")).toBe(false);
        // root is not in x's descendant set -> allowed, and still terminates.
        expect(canReparentGroup(cyclic, "x", "root")).toBe(true);
    });
});

describe("applyGroupReparent", () => {
    it("returns a new array with the matching group's parentId updated", () => {
        const next = applyGroupReparent(tree, "a", "b");
        const moved = next.find(g => g.id === "a");
        expect(moved?.parentId).toBe("b");
        // other groups untouched
        expect(next.find(g => g.id === "c")?.parentId).toBe("a");
        expect(next.find(g => g.id === "root")?.parentId).toBe("");
    });

    it("is a no-op when the group is missing", () => {
        const next = applyGroupReparent(tree, "ghost", "a");
        expect(next.map(g => ({ id: g.id, parentId: g.parentId }))).toEqual(
            tree.map(g => ({ id: g.id, parentId: g.parentId }))
        );
    });
});

describe("applyJobReparent", () => {
    const j1 = mkJob("j1");
    const j2 = mkJob("j2");
    const j3 = mkJob("j3");
    const baseState = (): Map<string, Job[] | "loading"> =>
        new Map<string, Job[] | "loading">([
            ["a", [j1, j2]],
            ["b", [j3]],
        ]);

    it("removes the job from source and appends to target when target is loaded", () => {
        const next = applyJobReparent(baseState(), "j1", "a", "b");
        expect(next.get("a")).toEqual([j2]);
        expect(next.get("b")).toEqual([j3, j1]);
    });

    it("removes from source but does not create a target entry when target is not loaded", () => {
        const next = applyJobReparent(baseState(), "j1", "a", "c");
        expect(next.get("a")).toEqual([j2]);
        expect(next.has("c")).toBe(false);
    });

    it("returns the same Map (referential equality) when fromGroupId equals toGroupId", () => {
        const state = baseState();
        const next = applyJobReparent(state, "j1", "a", "a");
        expect(next).toBe(state);
    });

    it("returns the same Map when the job is not in the source", () => {
        const state = baseState();
        const next = applyJobReparent(state, "j-ghost", "a", "b");
        expect(next).toBe(state);
    });

    it("returns the same Map when the source group is not loaded", () => {
        const state = baseState();
        const next = applyJobReparent(state, "j1", "unloaded", "b");
        expect(next).toBe(state);
    });
});
