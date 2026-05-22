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
import { filterFramesByStates, getFrameStateCounts } from "@/app/utils/frame_state_utils";

const frame = (state: string): Frame =>
  ({
    id: state,
    name: state,
    layerName: "layer",
    number: 1,
    state,
  }) as Frame;

describe("frame-columns", () => {
  describe("getFrameStateCounts", () => {
    it("counts frames by supported state", () => {
      expect(getFrameStateCounts([frame("WAITING"), frame("RUNNING"), frame("RUNNING"), frame("DEPEND")])).toEqual({
        WAITING: 1,
        RUNNING: 2,
        SUCCEEDED: 0,
        DEAD: 0,
        EATEN: 0,
        DEPEND: 1,
      });
    });
  });

  describe("filterFramesByStates", () => {
    it("returns every frame when no states are selected", () => {
      const frames = [frame("WAITING"), frame("DEAD")];

      expect(filterFramesByStates(frames, [])).toBe(frames);
    });

    it("combines selected states with OR semantics", () => {
      const frames = [frame("WAITING"), frame("RUNNING"), frame("DEAD")];

      expect(filterFramesByStates(frames, ["WAITING", "DEAD"])).toEqual([frames[0], frames[2]]);
    });
  });
});
