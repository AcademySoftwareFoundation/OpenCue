import type { Job } from "@/app/jobs/columns";
import { getJobProgressSegments, getJobProgressTooltipRows } from "@/app/utils/job_progress_utils";

const job = (stats: Partial<Job["jobStats"]>): Job =>
  ({
    jobStats: {
      totalFrames: 10,
      succeededFrames: 4,
      runningFrames: 2,
      waitingFrames: 1,
      dependFrames: 2,
      deadFrames: 1,
      ...stats,
    },
  }) as Job;

describe("job_progress_utils", () => {
  it("returns progress segment percentages", () => {
    expect(getJobProgressSegments(job({})).map((segment) => segment.percentage)).toEqual([
      "40%",
      "20%",
      "10%",
      "20%",
      "10%",
    ]);
  });

  it("returns tooltip rows with counts and rounded percentages", () => {
    expect(getJobProgressTooltipRows(job({ totalFrames: 12, succeededFrames: 5 }))[0]).toEqual({
      label: "Succeeded",
      count: 5,
      percentage: "41.7%",
    });
  });

  it("uses zero percentages when total frame count is zero", () => {
    expect(getJobProgressTooltipRows(job({ totalFrames: 0, succeededFrames: 5 }))[0].percentage).toBe("0.0%");
    expect(getJobProgressSegments(job({ totalFrames: 0, succeededFrames: 5 }))[0].percentage).toBe("0%");
  });
});
