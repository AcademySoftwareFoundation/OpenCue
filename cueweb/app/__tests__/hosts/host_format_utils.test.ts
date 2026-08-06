import { kbStringToHuman, kbStringToNumber, idleRatio } from "@/app/hosts/host_format_utils";

describe("host_format_utils", () => {
  describe("kbStringToNumber", () => {
    it("parses a numeric KB string", () => {
      expect(kbStringToNumber("6815744")).toBe(6815744);
    });
    it("returns 0 for non-numeric or empty input", () => {
      expect(kbStringToNumber("")).toBe(0);
      expect(kbStringToNumber("abc")).toBe(0);
      expect(kbStringToNumber(undefined as unknown as string)).toBe(0);
    });
  });

  describe("kbStringToHuman", () => {
    it("formats KB strings to a human unit", () => {
      expect(kbStringToHuman("6815744")).toBe("6.5G");
      expect(kbStringToHuman("512")).toBe("512K");
    });
    it("renders a dash for non-numeric input", () => {
      expect(kbStringToHuman("abc")).toBe("-");
      expect(kbStringToHuman("")).toBe("-");
    });
  });

  describe("idleRatio", () => {
    it("returns idle / total as a 0..1 ratio", () => {
      expect(idleRatio(4, 8)).toBe(0.5);
    });
    it("returns 0 when total is 0 to avoid divide-by-zero", () => {
      expect(idleRatio(0, 0)).toBe(0);
    });
  });
});
