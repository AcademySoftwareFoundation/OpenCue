import { secondsToHumanAge } from "@/app/utils/layers_frames_utils";

describe("layers_frames_utils", () => {
  describe("secondsToHumanAge", () => {
    it("formats durations under an hour as minutes", () => {
      expect(secondsToHumanAge(0)).toBe("0m");
      expect(secondsToHumanAge(59)).toBe("0m");
      expect(secondsToHumanAge(60)).toBe("1m");
    });

    it("formats durations under a day as hours and minutes", () => {
      expect(secondsToHumanAge(2 * 3600 + 14 * 60)).toBe("2h 14m");
      expect(secondsToHumanAge(23 * 3600 + 59 * 60)).toBe("23h 59m");
    });

    it("formats durations of at least a day as days and hours", () => {
      expect(secondsToHumanAge(3 * 86400 + 4 * 3600 + 59 * 60)).toBe("3d 4h");
    });

    it("does not return negative ages", () => {
      expect(secondsToHumanAge(-60)).toBe("0m");
    });
  });
});
