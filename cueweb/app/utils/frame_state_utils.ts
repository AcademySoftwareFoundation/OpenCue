import type { Frame } from "@/app/frames/frame-columns";

export const FRAME_STATE_FILTERS = ["WAITING", "RUNNING", "SUCCEEDED", "DEAD", "EATEN", "DEPEND"];

export const filterFramesByStates = (frames: Frame[], selectedStates: string[]) => {
  if (selectedStates.length === 0) {
    return frames;
  }

  const selectedStateSet = new Set(selectedStates.map((state) => state.toUpperCase()));
  return frames.filter((frame) => selectedStateSet.has(frame.state.toUpperCase()));
};

export const getFrameStateCounts = (frames: Frame[]) => {
  return FRAME_STATE_FILTERS.reduce(
    (counts, state) => {
      counts[state] = frames.filter((frame) => frame.state.toUpperCase() === state).length;
      return counts;
    },
    {} as Record<string, number>,
  );
};
