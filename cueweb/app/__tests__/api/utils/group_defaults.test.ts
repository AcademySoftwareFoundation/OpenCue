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
import { formatGroupDefaults } from "@/app/utils/group_defaults";

// Baseline group: every default disabled (-1), no department.
const group = (overrides: Partial<Group>): Group =>
  ({
    id: "g",
    name: "g",
    department: "",
    defaultJobPriority: -1,
    defaultJobMinCores: -1,
    defaultJobMaxCores: -1,
    minCores: 0,
    maxCores: -1,
    level: 0,
    parentId: "",
    ...overrides,
  }) as Group;

describe("formatGroupDefaults", () => {
  it("returns an empty string when nothing is set", () => {
    expect(formatGroupDefaults(group({}))).toBe("");
  });

  it("includes the department when present", () => {
    expect(formatGroupDefaults(group({ department: "comp" }))).toBe("Dept: comp");
  });

  it("includes priority only when set", () => {
    expect(formatGroupDefaults(group({ defaultJobPriority: 100 }))).toBe("Priority: 100");
  });

  it("renders both core bounds as a range", () => {
    expect(formatGroupDefaults(group({ defaultJobMinCores: 1, defaultJobMaxCores: 8 }))).toBe(
      "Cores: 1–8",
    );
  });

  it("renders a one-sided minimum as ≥", () => {
    expect(formatGroupDefaults(group({ defaultJobMinCores: 2 }))).toBe("Cores: ≥2");
  });

  it("renders a one-sided maximum as ≤", () => {
    expect(formatGroupDefaults(group({ defaultJobMaxCores: 8 }))).toBe("Cores: ≤8");
  });

  it("combines department, priority, and cores in order", () => {
    expect(
      formatGroupDefaults(
        group({
          department: "comp",
          defaultJobPriority: 100,
          defaultJobMinCores: 1,
          defaultJobMaxCores: 8,
        }),
      ),
    ).toBe("Dept: comp · Priority: 100 · Cores: 1–8");
  });
});
