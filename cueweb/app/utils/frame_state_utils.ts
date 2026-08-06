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
