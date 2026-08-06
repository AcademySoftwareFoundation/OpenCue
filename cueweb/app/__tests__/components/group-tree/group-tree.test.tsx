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

import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { useRouter, usePathname, useSearchParams } from "next/navigation";
import type { Group } from "@/app/utils/get_utils";
import type { Job } from "@/app/jobs/columns";
import { getShowGroups, getGroupJobs } from "@/app/utils/get_utils";
import { reparentGroups, reparentJobs } from "@/app/utils/action_utils";
import { toastWarning } from "@/app/utils/notify_utils";
import { GroupTree } from "@/components/group-tree/group-tree";

// Capture the dnd handlers so a test can fire a synthetic drop without simulating
// real pointer drags (jsdom has no layout). DragDropProvider passes them through;
// assertions check the downstream optimistic-update / persist / rollback effects,
// not the event we echo back — so this is a seam, not a tautology.
const mockDnd: { onDragEnd?: (e: any) => void; onDragStart?: (e: any) => void } = {};
jest.mock("@dnd-kit/react", () => ({
  DragDropProvider: ({ children, onDragStart, onDragEnd }: any) => {
    mockDnd.onDragStart = onDragStart;
    mockDnd.onDragEnd = onDragEnd;
    return children;
  },
  DragOverlay: () => null,
  useDraggable: () => ({ ref: () => {}, handleRef: () => {}, isDragSource: false }),
  useDroppable: () => ({ ref: () => {}, isDropTarget: false }),
}));

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
  usePathname: jest.fn(),
  useSearchParams: jest.fn(),
}));

// next/link needs App Router context; passthrough <a> keeps the test scoped.
jest.mock("next/link", () => ({
  __esModule: true,
  default: ({ children, ...props }: { children: React.ReactNode }) =>
    require("react").createElement("a", props, children),
}));

// Factory mocks avoid loading the real modules' transitive imports (incl. react-toastify).
jest.mock("@/app/utils/get_utils", () => ({
  getShowGroups: jest.fn(),
  getGroupJobs: jest.fn(),
}));
jest.mock("@/app/utils/action_utils", () => ({
  reparentGroups: jest.fn(),
  reparentJobs: jest.fn(),
}));
jest.mock("@/app/utils/notify_utils", () => ({
  toastWarning: jest.fn(),
  toastSuccess: jest.fn(),
  handleError: jest.fn(),
}));

const mockGetShowGroups = getShowGroups as jest.Mock;
const mockGetGroupJobs = getGroupJobs as jest.Mock;
const mockReparentGroups = reparentGroups as jest.Mock;
const mockReparentJobs = reparentJobs as jest.Mock;
const mockToastWarning = toastWarning as jest.Mock;
const replaceMock = jest.fn();

const mkGroup = (id: string, name: string, parentId: string): Group => ({
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

// root → GroupA, GroupB (siblings). A and B are both non-root, so A is draggable
// and B is a legal drop target (canReparentGroup(_, "A", "B") === true).
const groups: Group[] = [
  mkGroup("root", "Root", ""),
  mkGroup("A", "GroupA", "root"),
  mkGroup("B", "GroupB", "root"),
];

const job: Job = {
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
    deadFrames: 0,
    pendingFrames: 3,
  },
} as unknown as Job;

const groupDrop = {
  canceled: false,
  operation: { source: { id: "A", data: { type: "group" } }, target: { id: "B" } },
};

function renderTree(search = "") {
  (useSearchParams as jest.Mock).mockReturnValue(new URLSearchParams(search));
  return render(<GroupTree showId="s1" />);
}

describe("GroupTree orchestration", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useRouter as jest.Mock).mockReturnValue({ replace: replaceMock });
    (usePathname as jest.Mock).mockReturnValue("/shows/s1");
    mockGetShowGroups.mockResolvedValue(groups);
    mockGetGroupJobs.mockResolvedValue([]);
  });

  it("persists a group reparent and refetches on success", async () => {
    mockReparentGroups.mockResolvedValue(true);
    renderTree();
    await waitFor(() => expect(mockGetShowGroups).toHaveBeenCalledTimes(1));

    await act(async () => {
      mockDnd.onDragEnd!(groupDrop);
    });

    await waitFor(() => expect(mockReparentGroups).toHaveBeenCalledWith("B", ["A"]));
    // Initial load + post-success refetch.
    await waitFor(() => expect(mockGetShowGroups).toHaveBeenCalledTimes(2));
  });

  it("ignores a second reparent while one is already in flight", async () => {
    mockReparentGroups.mockResolvedValue(true);
    renderTree();
    await waitFor(() => expect(mockGetShowGroups).toHaveBeenCalledTimes(1));

    await act(async () => {
      mockDnd.onDragEnd!(groupDrop);
      mockDnd.onDragEnd!(groupDrop); // blocked by the in-flight guard
    });

    // Only the first drop reaches the backend; the second is rejected with a toast.
    await waitFor(() => expect(mockReparentGroups).toHaveBeenCalledTimes(1));
    expect(mockToastWarning).toHaveBeenCalled();
  });

  it("rolls back and does not refetch when the group reparent fails", async () => {
    mockReparentGroups.mockResolvedValue(false);
    renderTree();
    await waitFor(() => expect(mockGetShowGroups).toHaveBeenCalledTimes(1));

    await act(async () => {
      mockDnd.onDragEnd!(groupDrop);
    });

    await waitFor(() => expect(mockReparentGroups).toHaveBeenCalledWith("B", ["A"]));
    // Failure path returns before the refetch, and the tree is restored.
    expect(mockGetShowGroups).toHaveBeenCalledTimes(1);
    expect(screen.queryByText("GroupA")).not.toBeNull();
    expect(screen.queryByText("GroupB")).not.toBeNull();
  });

  it("keeps the tree when the post-success refetch returns empty (no blank-out)", async () => {
    // A real show always returns its root group, so [] means the refetch failed.
    mockGetShowGroups.mockResolvedValueOnce(groups).mockResolvedValueOnce([]);
    mockReparentGroups.mockResolvedValue(true);
    renderTree();
    await waitFor(() => expect(mockGetShowGroups).toHaveBeenCalledTimes(1));

    await act(async () => {
      mockDnd.onDragEnd!(groupDrop);
    });

    await waitFor(() => expect(mockGetShowGroups).toHaveBeenCalledTimes(2));
    // The optimistic state is retained instead of blanking to the empty state.
    // (GroupB stays under the always-open root; GroupA is now nested under the
    // still-collapsed GroupB, so we assert on the row that remains visible.)
    expect(screen.queryByText("No groups in this show.")).toBeNull();
    expect(screen.queryByText("GroupB")).not.toBeNull();
  });

  it("rolls back a job reparent when it fails", async () => {
    mockGetGroupJobs.mockImplementation((id: string) =>
      Promise.resolve(id === "A" ? [job] : []),
    );
    mockReparentJobs.mockResolvedValue(false);
    renderTree("expanded=A");
    await waitFor(() => expect(screen.queryByText(job.name)).not.toBeNull());

    await act(async () => {
      mockDnd.onDragEnd!({
        canceled: false,
        operation: {
          source: { id: job.id, data: { type: "job", fromGroupId: "A" } },
          target: { id: "B" },
        },
      });
    });

    await waitFor(() => expect(mockReparentJobs).toHaveBeenCalledWith("B", [job.id]));
    // Rolled back: the job is still listed under its original group.
    await waitFor(() => expect(screen.queryByText(job.name)).not.toBeNull());
  });

  it("renders the group named in the expanded URL param as open", async () => {
    renderTree("expanded=B");
    // Expanding a group requests its jobs; root is always open, B only when expanded.
    await waitFor(() => expect(mockGetGroupJobs).toHaveBeenCalledWith("B"));
  });

  it("writes the toggled group id to the expanded URL param", async () => {
    renderTree();
    await waitFor(() => expect(screen.queryByText("GroupA")).not.toBeNull());

    fireEvent.click(screen.getByText("GroupA"));

    await waitFor(() => expect(replaceMock).toHaveBeenCalled());
    const url = replaceMock.mock.calls[replaceMock.mock.calls.length - 1][0];
    expect(url).toContain("expanded=A");
  });
});
