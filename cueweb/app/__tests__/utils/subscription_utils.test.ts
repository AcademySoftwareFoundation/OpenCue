/**
 * @jest-environment jsdom
 */
import {
  JobSubscription,
  addSubscription,
  getSubscription,
  getSubscriptions,
  markNotified,
  pickEntriesToNotify,
  removeSubscription,
} from "@/app/utils/subscription_utils";

describe("subscription_utils", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe("getSubscriptions defensive parsing", () => {
    it("returns {} when storage contains an empty string", () => {
      localStorage.setItem("cueweb:job-subscriptions", "");
      expect(getSubscriptions()).toEqual({});
    });

    it("returns {} when storage contains malformed JSON", () => {
      localStorage.setItem("cueweb:job-subscriptions", "{bad-json");
      expect(getSubscriptions()).toEqual({});
    });

    it("returns {} when storage contains a JSON null", () => {
      localStorage.setItem("cueweb:job-subscriptions", "null");
      expect(getSubscriptions()).toEqual({});
    });

    it("returns {} when storage contains a JSON primitive", () => {
      localStorage.setItem("cueweb:job-subscriptions", "42");
      expect(getSubscriptions()).toEqual({});
    });

    it("returns {} when storage contains a JSON array", () => {
      localStorage.setItem("cueweb:job-subscriptions", "[1,2,3]");
      expect(getSubscriptions()).toEqual({});
    });
  });

  describe("CRUD", () => {
    it("getSubscriptions returns {} when storage is empty", () => {
      expect(getSubscriptions()).toEqual({});
    });

    it("addSubscription persists with notifiedAt=null", () => {
      addSubscription("job-1", "render_test");
      const entry = getSubscription("job-1");
      expect(entry).toBeDefined();
      expect(entry?.jobId).toBe("job-1");
      expect(entry?.jobName).toBe("render_test");
      expect(entry?.notifiedAt).toBeNull();
      expect(typeof entry?.subscribedAt).toBe("number");
    });

    it("addSubscription is idempotent (preserves the original entry on duplicate jobId)", () => {
      addSubscription("job-1", "first_name");
      const first = getSubscription("job-1");
      addSubscription("job-1", "second_name");
      const second = getSubscription("job-1");
      expect(second?.jobName).toBe("first_name");
      expect(second?.subscribedAt).toBe(first?.subscribedAt);
    });

    it("getSubscription returns undefined for unknown jobId", () => {
      expect(getSubscription("nonexistent")).toBeUndefined();
    });

    it("removeSubscription deletes the entry", () => {
      addSubscription("job-1", "render_test");
      expect(getSubscription("job-1")).toBeDefined();
      removeSubscription("job-1");
      expect(getSubscription("job-1")).toBeUndefined();
    });

    it("removeSubscription is a no-op when the entry does not exist", () => {
      expect(() => removeSubscription("nonexistent")).not.toThrow();
    });

    it("markNotified sets notifiedAt without removing the entry", () => {
      addSubscription("job-1", "render_test");
      markNotified("job-1");
      const entry = getSubscription("job-1");
      expect(entry).toBeDefined();
      expect(entry?.notifiedAt).not.toBeNull();
      expect(typeof entry?.notifiedAt).toBe("number");
    });

    it("markNotified is a no-op when the entry does not exist", () => {
      expect(() => markNotified("nonexistent")).not.toThrow();
      expect(getSubscription("nonexistent")).toBeUndefined();
    });
  });

  describe("pickEntriesToNotify", () => {
    const makeEntry = (overrides: Partial<JobSubscription> = {}): JobSubscription => ({
      jobId: "job-1",
      jobName: "render_test",
      subscribedAt: 1000,
      notifiedAt: null,
      ...overrides,
    });

    it("returns FINISHED entries that have not been notified", () => {
      const entry = makeEntry();
      const result = pickEntriesToNotify({ "job-1": entry }, { "job-1": "FINISHED" });
      expect(result).toHaveLength(1);
      expect(result[0].jobId).toBe("job-1");
    });

    it("skips entries already notified", () => {
      const entry = makeEntry({ notifiedAt: 2000 });
      const result = pickEntriesToNotify({ "job-1": entry }, { "job-1": "FINISHED" });
      expect(result).toEqual([]);
    });

    it("skips entries with non-FINISHED state", () => {
      const entry = makeEntry();
      for (const state of ["RUNNING", "PENDING", "PAUSED"]) {
        expect(pickEntriesToNotify({ "job-1": entry }, { "job-1": state })).toEqual([]);
      }
    });

    it("skips entries when fetchedStates is missing the jobId", () => {
      const entry = makeEntry();
      const result = pickEntriesToNotify({ "job-1": entry }, { "job-2": "FINISHED" });
      expect(result).toEqual([]);
    });

    it("returns empty when the store is empty", () => {
      expect(pickEntriesToNotify({}, { "job-1": "FINISHED" })).toEqual([]);
    });

    it("returns multiple entries when multiple are eligible", () => {
      const result = pickEntriesToNotify(
        {
          "job-1": makeEntry({ jobId: "job-1" }),
          "job-2": makeEntry({ jobId: "job-2" }),
          "job-3": makeEntry({ jobId: "job-3", notifiedAt: 5000 }),
        },
        {
          "job-1": "FINISHED",
          "job-2": "FINISHED",
          "job-3": "FINISHED",
        },
      );
      expect(result).toHaveLength(2);
      expect(result.map((e) => e.jobId).sort()).toEqual(["job-1", "job-2"]);
    });
  });
});
