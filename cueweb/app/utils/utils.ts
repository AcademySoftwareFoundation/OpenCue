// *** Helper functions ** //

import path from "path";
import { Frame } from "../frames/frame-columns";
import { Job } from "../jobs/columns";
import * as Sentry from "@sentry/nextjs";

export const convertUnixToHumanReadableDate = (timestamp: number) => {
  if (timestamp == 0) {
    return "";
  }
  const milliseconds = timestamp * 1000;
  const date = new Date(milliseconds);
  const year = date.getFullYear();
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const hours = date.getHours();
  // ensuring that minutes are always represented as two digits
  const minutes = date.getMinutes().toString().padStart(2, "0");

  const humanReadableDate = `${year}-${month}-${day} ${hours}:${minutes}`;
  return humanReadableDate;
};

// logic can be found in cuegui.cuegui.Utils.memoryToString
export const convertMemoryToString = (kmem: number, object: string) => {
  // Returns an amount of memory in a human-friendly string
  // if kmem is not a valid number (i.e NaN), then this function returns an empty string
  // and a message is logged in Sentry
  const k = 1024;
  if (kmem < k) {
    return `${kmem}K`;
  }
  if (kmem < Math.pow(k, 2)) {
    return `${Math.floor(kmem / k)}M`;
  }

  const mem = kmem / Math.pow(k, 2);
  if (isNaN(mem)) {
    Sentry.captureMessage(`Memory is NaN\nFor object: ${object}`, "log");
    return "";
  }
  return `${mem.toFixed(1)}G`;
};

export const secondsToHHMMSS = (sec: number) => {
  // Returns the number of seconds as a formatted string HH:MM:SS
  const hours = Math.floor(sec / 3600);
  const remainingTime = sec - hours * 3600;
  const minutes = Math.floor(remainingTime / 60);
  const seconds = remainingTime - minutes * 60;
  // prettier-ignore
  return `
  ${hours.toString().padStart(2, "0")}:` +
  `${minutes.toString().padStart(2, "0")}:` +
  `${seconds.toString().padStart(2, "0")}
  `;
};

export const secondsToHHHMM = (sec: number) => {
  // Returns the number of seconds as a formatted string HHH:MM
  const hours = Math.floor(sec / 3600);
  const remainingTime = sec - hours * 3600;
  const minutes = Math.floor(remainingTime / 60);
  return `${hours.toString().padStart(3, "0")}:${minutes.toString().padStart(2, "0")}`;
};

// logic in cuegui.Utils.getFrameLogDir
export const getFrameLogDir = (job: Job, frame: Frame) => {
  return path.join(job.logDir, `${job.name}.${frame.name}.rqlog`);
};

export async function getFrame(body: string) {
  const response = await fetch("/api/frame", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: body,
  });
  const res = await response.json();
  if (res.error) {
    alert("Failed to fetch frame from /api/frame");
    return [];
  }
  return res.data;
}

export async function getJob(body: string) {
  const response = await fetch("/api/job", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: body,
  });
  const res = await response.json();
  if (res.error) {
    alert("Failed to fetch job from /api/job");
    return [];
  }
  return res.data;
}

export async function getJobs(body: string) {
  const response = await fetch("/api/jobs", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: body,
  });
  const res = await response.json();
  if (res.error) {
    alert("Failed to fetch jobs from /api/jobs");
    return [];
  }
  return res.data;
}

export async function getLayers(body: string) {
  const response = await fetch("/api/layers", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: body,
  });
  const res = await response.json();
  if (res.error) {
    alert("Failed to fetch layers from /api/layers");
    return [];
  }
  return res.data;
}

export async function getFrames(body: string) {
  const response = await fetch("/api/frames", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: body,
  });
  const res = await response.json();
  if (res.error) {
    alert("Failed to fetch frames from /api/frames");
    return [];
  }
  return res.data;
}

export async function getJobsForUser(user: string) {
  const body = { r: { include_finished: true, users: [`${user}`] } };
  return getJobs(JSON.stringify(body));
}

export async function getJobsForShow(show: string) {
  const body = { r: { include_finished: true, shows: [`${show}`] } };
  return getJobs(JSON.stringify(body));
}

export async function getLayersForJob(job: Job) {
  const body = { job: { id: `${job.id}` } };
  return getLayers(JSON.stringify(body));
}

export async function getFramesForJob(job: Job) {
  const body = {
    job: { id: `${job.id}`, name: `${job.name}` },
    req: { include_finished: true, page: 1, limit: 500 },
  };
  return getFrames(JSON.stringify(body));
}
