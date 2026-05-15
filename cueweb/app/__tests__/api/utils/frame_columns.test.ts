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
