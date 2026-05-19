import type { Job } from "@/app/jobs/columns";

const JOB_PROGRESS_STATES = [
  { key: "succeededFrames", label: "Succeeded", color: "#4CC417" },
  { key: "runningFrames", label: "Running", color: "#F8E473" },
  { key: "waitingFrames", label: "Waiting", color: "#ADD8E6" },
  { key: "dependFrames", label: "Depend", color: "#9118C4" },
  { key: "deadFrames", label: "Dead", color: "tomato" },
] as const;

const getFramePercentage = (count: number, totalFrames: number) => {
  if (totalFrames <= 0) {
    return 0;
  }

  return (count / totalFrames) * 100;
};

export const getJobProgressSegments = (job: Job) => {
  return JOB_PROGRESS_STATES.map((state) => {
    const count = job.jobStats[state.key];
    return {
      percentage: `${getFramePercentage(count, job.jobStats.totalFrames)}%`,
      color: state.color,
    };
  });
};

export const getJobProgressTooltipRows = (job: Job) => {
  return JOB_PROGRESS_STATES.map((state) => {
    const count = job.jobStats[state.key];
    const percentage = getFramePercentage(count, job.jobStats.totalFrames);
    return {
      label: state.label,
      count,
      percentage: `${percentage.toFixed(1)}%`,
    };
  });
};
