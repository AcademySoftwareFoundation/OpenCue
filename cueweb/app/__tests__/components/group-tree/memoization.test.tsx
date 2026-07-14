/**
 * @jest-environment jsdom
 */

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

import { render } from "@testing-library/react";
import type { Job } from "@/app/jobs/columns";
import type { Group } from "@/app/utils/get_utils";
import { ZERO_STATS, type TreeNode } from "@/components/group-tree/build-tree";
import * as progressUtils from "@/app/utils/job_progress_utils";
import * as groupDefaultsUtils from "@/app/utils/group_defaults";
import { GroupTreeProvider } from "@/components/group-tree/group-tree-context";
import { JobLeaf } from "@/components/group-tree/job-leaf";
import { GroupNode } from "@/components/group-tree/group-node";

// dnd-kit hooks are inert here — we're validating our memoization, not dnd.
jest.mock("@dnd-kit/react", () => ({
  useDraggable: () => ({ ref: () => {}, handleRef: () => {}, isDragSource: false }),
  useDroppable: () => ({ ref: () => {}, isDropTarget: false }),
}));

// next/link needs App Router context; passthrough <a> keeps the test scoped.
jest.mock("next/link", () => ({
  __esModule: true,
  default: ({ children, ...props }: { children: React.ReactNode }) =>
    require("react").createElement("a", props, children),
}));

const makeJob = (): Job =>
  ({
    id: "job-1",
    name: "show-shot-user_job",
    state: "RUNNING",
    isPaused: false,
    jobStats: {
      totalFrames: 10,
      succeededFrames: 4,
      runningFrames: 2,
      waitingFrames: 1,
      dependFrames: 2,
      deadFrames: 1,
      pendingFrames: 3,
    },
  }) as unknown as Job;

const makeGroup = (): Group => ({
  id: "group-1",
  name: "childA",
  department: "comp",
  defaultJobPriority: 100,
  defaultJobMinCores: 1,
  defaultJobMaxCores: 8,
  minCores: 0,
  maxCores: -1,
  level: 0,
  parentId: "",
});

const makeNode = (group: Group): TreeNode => ({
  group,
  children: [],
  rolledUpStats: ZERO_STATS,
});

// Minimal context so GroupNode can call useGroupTree().
const ctx = {
  expanded: new Set<string>(),
  onToggle: () => {},
  jobsByGroup: new Map<string, Job[] | "loading">(),
  requestJobsFor: () => {},
  isValidDropTarget: () => false,
};

describe("group-tree memoization", () => {
  afterEach(() => jest.restoreAllMocks());

  // JobLeaf calls getJobProgressSegments once per render → spy count = renders.
  it("JobLeaf skips re-render when its parent re-renders with identical props", () => {
    const spy = jest.spyOn(progressUtils, "getJobProgressSegments");
    const job = makeJob();
    function Harness({ depth }: { depth: number }) {
      return <JobLeaf job={job} depth={depth} fromGroupId="g" />;
    }

    const { rerender } = render(<Harness depth={1} />);
    const baseline = spy.mock.calls.length;
    expect(baseline).toBeGreaterThan(0);

    // Parent re-renders; child props are referentially identical -> memo bails.
    rerender(<Harness depth={1} />);
    expect(spy.mock.calls.length).toBe(baseline);

    // Positive control: a changed prop must still re-render.
    rerender(<Harness depth={2} />);
    expect(spy.mock.calls.length).toBe(baseline + 1);
  });

  // GroupNode calls formatGroupDefaults once per render.
  it("GroupNode skips re-render when its parent re-renders with identical props", () => {
    const spy = jest.spyOn(groupDefaultsUtils, "formatGroupDefaults");
    const node = makeNode(makeGroup());
    function Harness({ n }: { n: TreeNode }) {
      return (
        <GroupTreeProvider value={ctx}>
          <GroupNode node={n} depth={0} />
        </GroupTreeProvider>
      );
    }

    const { rerender } = render(<Harness n={node} />);
    const baseline = spy.mock.calls.length;
    expect(baseline).toBeGreaterThan(0);

    // Same node reference -> memo bails.
    rerender(<Harness n={node} />);
    expect(spy.mock.calls.length).toBe(baseline);

    // Positive control: a new node object must still re-render the node.
    rerender(<Harness n={makeNode(makeGroup())} />);
    expect(spy.mock.calls.length).toBe(baseline + 1);
  });
});
