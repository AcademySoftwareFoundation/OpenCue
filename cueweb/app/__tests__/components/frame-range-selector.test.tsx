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

import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { Frame } from "@/app/frames/frame-columns";
import { eatFrames, killFrames, retryFrames } from "@/app/utils/action_utils";
import { FrameRangeSelector } from "@/components/ui/frame-range-selector";

// Mock the action layer so the test asserts the selected subset that gets
// handed off, not the network behavior (which has its own coverage).
jest.mock("@/app/utils/action_utils", () => ({
  retryFrames: jest.fn(),
  eatFrames: jest.fn(),
  killFrames: jest.fn(),
}));

// The safety flag hook reads localStorage + window events; stub it "enabled".
jest.mock("@/app/utils/use_disable_job_interaction", () => ({
  useDisableJobInteraction: () => ({ disabled: false, setDisabled: jest.fn(), toggle: jest.fn() }),
}));

function makeFrame(number: number, state = "DEAD"): Frame {
  return {
    id: `frame-${number}`,
    name: `${number}-layer`,
    layerName: "layer",
    number,
    state,
    retryCount: 0,
    exitStatus: 0,
    dispatchOrder: number,
    startTime: 0,
    stopTime: 0,
    maxRss: "0",
    usedMemory: "0",
    reservedMemory: "0",
    reservedGpuMemory: "0",
    lastResource: "/",
    checkpointState: "",
    checkpointCount: 0,
    totalCoreTime: 0,
    lluTime: 0,
    totalGpuTime: 0,
    maxGpuMemory: "0",
    usedGpuMemory: "0",
    frameStateDisplayOverride: "",
  };
}

const FRAMES = [1, 2, 3, 4, 5].map((n) => makeFrame(n));

function cell(number: number): HTMLElement {
  const el = document.querySelector(`[data-frame-number="${number}"]`);
  if (!el) throw new Error(`cell #${number} not found`);
  return el as HTMLElement;
}

beforeEach(() => {
  jest.clearAllMocks();
});

describe("FrameRangeSelector", () => {
  it("drag selects a contiguous range and feeds it into Retry", async () => {
    render(<FrameRangeSelector frames={FRAMES} username="tester" />);

    // Drag from frame #2 to frame #4 -> selects {2,3,4}.
    fireEvent.mouseDown(cell(2));
    fireEvent.mouseEnter(cell(3));
    fireEvent.mouseEnter(cell(4));
    fireEvent.mouseUp(window);

    expect(screen.getByText(/Selected 3 frames \(#2–#4\)/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    // Confirm in the dialog (there are two "Retry" buttons now; pick the
    // one inside the dialog).
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Retry" }));

    await waitFor(() => expect(retryFrames).toHaveBeenCalledTimes(1));
    const handed = (retryFrames as jest.Mock).mock.calls[0][0] as Frame[];
    expect(handed.map((f) => f.number).sort((a, b) => a - b)).toEqual([2, 3, 4]);
    expect(eatFrames).not.toHaveBeenCalled();
    expect(killFrames).not.toHaveBeenCalled();
  });

  it("shift-click extends the selection from the anchor", async () => {
    render(<FrameRangeSelector frames={FRAMES} username="tester" />);

    // Anchor at #2 (single click), then shift-click #5 -> {2,3,4,5}.
    fireEvent.mouseDown(cell(2));
    fireEvent.mouseUp(window);
    fireEvent.mouseDown(cell(5), { shiftKey: true });

    expect(screen.getByText(/Selected 4 frames \(#2–#5\)/)).toBeInTheDocument();
  });

  it("routes Kill through a destructive confirm with the selected subset", async () => {
    render(<FrameRangeSelector frames={FRAMES} username="tester" />);

    fireEvent.mouseDown(cell(1));
    fireEvent.mouseEnter(cell(2));
    fireEvent.mouseUp(window);

    fireEvent.click(screen.getByRole("button", { name: "Kill" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Kill" }));

    await waitFor(() => expect(killFrames).toHaveBeenCalledTimes(1));
    const [handed, username, reason] = (killFrames as jest.Mock).mock.calls[0];
    expect((handed as Frame[]).map((f) => f.number)).toEqual([1, 2]);
    expect(username).toBe("tester");
    expect(reason).toMatch(/frame range selector/i);
  });

  it("Clear removes the current selection", () => {
    render(<FrameRangeSelector frames={FRAMES} username="tester" />);

    fireEvent.mouseDown(cell(1));
    fireEvent.mouseEnter(cell(3));
    fireEvent.mouseUp(window);
    expect(screen.getByText(/Selected 3 frames/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Clear" }));
    expect(screen.getByText(/Drag to select a range of 5 frames/)).toBeInTheDocument();
  });
});
