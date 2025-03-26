"use client";

import { Job } from "@/app/jobs/columns";
import ProgressBar from "./progressbar";

const getProgressBarSuccess = (job: Job) => {
  const successfulFramePercent = (job.jobStats.succeededFrames / job.jobStats.totalFrames) * 100;
  return `${successfulFramePercent}%`;
};
const getProgressBarRunning = (job: Job) => {
  const runningFramePercent = (job.jobStats.runningFrames / job.jobStats.totalFrames) * 100;
  return `${runningFramePercent}%`;
};
const getProgressBarWaiting = (job: Job) => {
  const waitingFramePercent = (job.jobStats.waitingFrames / job.jobStats.totalFrames) * 100;
  return `${waitingFramePercent}%`;
};
const getProgressBarDepend = (job: Job) => {
  const dependFramePercent = (job.jobStats.dependFrames / job.jobStats.totalFrames) * 100;
  return `${dependFramePercent}%`;
};
const getProgressBarDead = (job: Job) => {
  const deadFramePercent = (job.jobStats.deadFrames / job.jobStats.totalFrames) * 100;
  return `${deadFramePercent}%`;
};

type JobProgressBarProps = {
  job: Job;
};

export function JobProgressBar({ job }: JobProgressBarProps) {
  return (
    <ProgressBar
      visualParts={[
        {
          // green portion to show % succeeded frames
          percentage: getProgressBarSuccess(job),
          color: "#4CC417",
        },
        {
          // yellow portion to show % running frames
          percentage: getProgressBarRunning(job),
          color: "#F8E473",
        },
        {
          // blue portion to show % waiting frames
          percentage: getProgressBarWaiting(job),
          color: "#ADD8E6",
        },
        {
          // purple portion to show % dependent frames
          percentage: getProgressBarDepend(job),
          color: "#9118C4",
        },
        {
          // red portion to show % dead frames
          percentage: getProgressBarDead(job),
          color: "tomato",
        },
      ]}
    />
  );
}
