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

import { Job } from "@/app/jobs/columns";
import { Row } from "@tanstack/react-table";
import * as React from "react";
import { Frame } from "../frames/frame-columns";
import { Layer } from "../layers/layer-columns";
import { accessActionApi } from "./api_utils";
import { getJobForLayer, JobComment } from "./get_utils";
import { handleError, toastSuccess, toastWarning } from "./notify_utils";

/**************************************/
// Helper function for API calls
/**************************************/

export async function performAction(endpoint: string, bodyAr: string[], successMessage: string) {
  if (bodyAr.length === 0) return;

  try {
    const result = await accessActionApi(endpoint, bodyAr);
    if (result?.success) {
      toastSuccess(successMessage);
    } else {
      throw new Error(result.error);
    }
  } catch (error) {
    handleError(error, `Error performing action for: ${endpoint}`);
  }
}

/**************************************/
// Kill Jobs, Layers, and Frames
/**************************************/

export async function killJobs(jobs: Job[], username: string, reason: string) {
  const endpoint = "/api/job/action/kill";
  const bodyAr = jobs.map(job => JSON.stringify({
    job,
    username,
    reason
  }));
  await performAction(endpoint, bodyAr, `Killed ${jobs.length} job(s)`);
}

export async function killLayers(layers: Layer[], username: string, reason: string) {
  const endpoint = "/api/layer/action/kill";
  const bodyAr = layers.map(layer => JSON.stringify({
    layer,
    username,
    reason
  }));
  await performAction(endpoint, bodyAr, `Killed ${layers.length} layer(s)`);
}

export async function killFrames(frames: Frame[], username: string, reason: string) {
  const endpoint = "/api/frame/action/kill";
  const bodyAr = frames.map(frame => JSON.stringify({
    frame,
    username,
    reason
  }));
  await performAction(endpoint, bodyAr, `Killed ${frames.length} frame(s)`);
}


/**************************************/
// Eat Jobs, Layers, and Frames
/**************************************/

export async function eatJobsDeadFrames(jobs: Job[]) {
  const endpoint = "/api/job/action/eatframes";
  const bodyAr = jobs.map(job => JSON.stringify({
    job,
    req: { states: { frame_states: [5] } } // Only eat dead frames
  }));
  await performAction(endpoint, bodyAr, `Ate ${jobs.length} job(s)`);
}

export async function eatLayersFrames(layers: Layer[]) {
  const endpoint = "/api/layer/action/eatframes";
  const bodyAr = layers.map(layer => JSON.stringify({
    layer
  }));
  await performAction(endpoint, bodyAr, `Ate ${layers.length} layer(s)`);
}

export async function eatFrames(frames: Frame[]) {
  const endpoint = "/api/frame/action/eat";
  const bodyAr = frames.map(frame => JSON.stringify({
    frame
  }));
  await performAction(endpoint, bodyAr, `Ate ${frames.length} frame(s)`);
}

  
/**************************************/
// Retry Jobs, Layers, and Frames
/**************************************/
export async function retryJobsDeadFrames(jobs: Job[]) {
  const endpoint = "/api/job/action/retryframes";
  const bodyAr = jobs.map(job => JSON.stringify({
    job,
    req: { states: { frame_states: [5] } } // Retry dead frames
  }));
  await performAction(endpoint, bodyAr, `Retried ${jobs.length} job(s)`);
}

export async function retryLayersFrames(layers: Layer[]) {
  const endpoint = "/api/layer/action/retryframes";
  const bodyAr = layers.map(layer => JSON.stringify({
    layer
  }));
  await performAction(endpoint, bodyAr, `Retried ${layers.length} layer(s)`);
}

export async function retryLayersDeadFrames(layers: Layer[]) {
  const endpoint = "/api/job/action/retryframes";
  const bodyAr = [];

  for (const layer of layers) {
    const job = await getJobForLayer(layer);
    if (job) {
      bodyAr.push(JSON.stringify({
        job,
        req: {
          layers: [layer.name],
          states: { frame_states: [5] }
        }
      }));
    }
  }

  if (bodyAr.length > 0) {
    await performAction(endpoint, bodyAr, `Retried ${bodyAr.length} layer(s)`);
  }
}

export async function retryFrames(frames: Frame[]) {
  const endpoint = "/api/frame/action/retry";
  const bodyAr = frames.map(frame => JSON.stringify({
    frame
  }));
  await performAction(endpoint, bodyAr, `Retried ${frames.length} frame(s)`);
}


/**************************************/
// Job Comments
/**************************************/
export async function addJobComment(
  job: Job,
  username: string,
  subject: string,
  message: string,
) {
  const endpoint = "/api/job/action/addcomment";
  const body = JSON.stringify({
    job: { id: job.id, name: job.name },
    new_comment: {
      user: username,
      subject,
      message,
    },
  });
  await performAction(endpoint, [body], "Added comment");
}

export async function saveJobComment(comment: JobComment) {
  const endpoint = "/api/comment/action/save";
  const body = JSON.stringify({ comment });
  await performAction(endpoint, [body], "Saved comment");
}

export async function deleteJobComment(comment: JobComment) {
  const endpoint = "/api/comment/action/delete";
  const body = JSON.stringify({ comment });
  await performAction(endpoint, [body], "Deleted comment");
}

/**************************************/
// Pause/Unpause Jobs
/**************************************/
export async function pauseJobs(jobs: Job[]) {
  const endpoint = "/api/job/action/pause";
  const bodyAr = jobs.map(job => JSON.stringify({ job }));
  await performAction(endpoint, bodyAr, `Paused ${jobs.length} job(s)`);
}

export async function unpauseJobs(jobs: Job[]) {
  const endpoint = "/api/job/action/unpause";
  const bodyAr = jobs.map(job => JSON.stringify({ job }));
  await performAction(endpoint, bodyAr, `Unpaused ${jobs.length} job(s)`);
}

/**************************************/
// Priority / retries / auto-eat / depends (CueGUI parity)
/**************************************/

export async function setJobPriority(job: Job, priority: number) {
  const endpoint = "/api/job/action/setpriority";
  await performAction(endpoint, [JSON.stringify({ job, val: priority })], `Set priority ${priority} on ${job.name}`);
}

export async function setJobMaxRetries(job: Job, maxRetries: number) {
  const endpoint = "/api/job/action/setmaxretries";
  await performAction(endpoint, [JSON.stringify({ job, max_retries: maxRetries })], `Set max retries ${maxRetries} on ${job.name}`);
}

export async function setJobAutoEat(job: Job, value: boolean) {
  const endpoint = "/api/job/action/setautoeat";
  await performAction(endpoint, [JSON.stringify({ job, value })], `Auto-Eat ${value ? "ON" : "OFF"} on ${job.name}`);
}

export async function dropJobDepends(job: Job, target: "INTERNAL" | "EXTERNAL") {
  const endpoint = "/api/job/action/dropdepends";
  await performAction(endpoint, [JSON.stringify({ job, target })], `Dropped ${target.toLowerCase()} depends on ${job.name}`);
}

/**************************************/
/* Table header menu functions        */
/**************************************/

export function getItemFromLocalStorage(itemKey: string, initialItemValue: string) {
  const itemFromStorage = JSON.parse(localStorage.getItem(itemKey) || initialItemValue);
  return itemFromStorage;
};

export function setItemInLocalStorage(itemKey: string, item: string) {
  localStorage.setItem(itemKey, item);
};

export function getJobsFromSelectedRows(table: any): Job[] {
  const selectedRows: Row<Job>[] = table.getSelectedRowModel().rows;
  return selectedRows.map(row => row.original);
}

export function eatJobsDeadFramesFromSelectedRows(table: any) {
  const jobs = getJobsFromSelectedRows(table).filter(job => job.state !== "FINISHED");
  if (jobs.length === 0) {
    toastWarning("Please select unfinished jobs");
  } else {
    eatJobsDeadFrames(jobs);
  }
}

export function retryJobsDeadFramesFromSelectedRows(table: any) {
  const jobs = getJobsFromSelectedRows(table).filter(job => job.state !== "FINISHED");
  if (jobs.length === 0) {
    toastWarning("Please select unfinished jobs");
  } else {
    retryJobsDeadFrames(jobs);
  }
}

export function pauseJobsFromSelectedRows(table: any) {
  const jobs = getJobsFromSelectedRows(table).filter(job => job.state !== "FINISHED");
  if (jobs.length === 0) {
    toastWarning("Please select unfinished jobs");
  } else {
    pauseJobs(jobs);
  }
}

export function unpauseJobsFromSelectedRows(table: any) {
  const jobs = getJobsFromSelectedRows(table).filter(job => job.state !== "FINISHED");
  if (jobs.length === 0) {
    toastWarning("Please select unfinished jobs");
  } else {
    unpauseJobs(jobs);
  }
}

export function killJobFromSelectedRows(table: any, username: string) {
  const reason = `Manual job kill request in Cueweb's menu bar by ${username}`;
  const jobs = getJobsFromSelectedRows(table).filter(job => job.state !== "FINISHED");
  if (jobs.length === 0) {
    toastWarning("Please select unfinished jobs");
  } else {
    killJobs(jobs, username, reason);
  }
}

/***************************************************/
/* Context menu functions for Jobs, Layers, Frames */
/***************************************************/
export function unmonitorJobGivenRow(
  row: Row<any>, tableData: Job[], tableDataUnfiltered: Job[],
  rowSelection: { [key: number]: boolean },
  setTableData: React.Dispatch<React.SetStateAction<Job[]>>,
  setTableDataUnfiltered: React.Dispatch<React.SetStateAction<Job[]>>,
  setRowSelection: React.Dispatch<React.SetStateAction<{ [key: number]: boolean }>>,
  tableStorageName: string, unfilteredTableStorageName: string
) {
  const jobToUnmonitor = row.original;
  const updatedTableData = tableData.filter(job => job.id !== jobToUnmonitor.id);
  const updatedTableDataUnfiltered = tableDataUnfiltered.filter(job => job.id !== jobToUnmonitor.id);
  
  const updatedRowSelection = { ...rowSelection };
  if (row.original.id in updatedRowSelection) {
    delete updatedRowSelection[row.original.id];
  }

  setTableData(updatedTableData);
  setTableDataUnfiltered(updatedTableDataUnfiltered);
  setItemInLocalStorage(tableStorageName, JSON.stringify(updatedTableData));
  setItemInLocalStorage(unfilteredTableStorageName, JSON.stringify(updatedTableDataUnfiltered));
  setRowSelection(updatedRowSelection);
}

export function pauseJobGivenRow(row: Row<any>) {
    const jobs = [row.original];
    pauseJobs(jobs);
}

export function retryJobsDeadFramesGivenRow(row: Row<any>) {
    const jobs = [row.original];
    retryJobsDeadFrames(jobs);
}

export function eatJobsDeadFramesGivenRow(row: Row<any>) {
    const jobs = [row.original];
    eatJobsDeadFrames(jobs);
}

export function killJobGivenRow(row: Row<any>, username: string) {
    const jobs = [row.original]
    const reason = `Manual job kill request in Cueweb's context menu by ${username}`;
    killJobs(jobs, username, reason);
}

/********************************/
/* Layer context menu functions */
/********************************/

export function killLayerGivenRow(row: Row<any>, username: string) {
    const layers = [row.original]
    const reason = `Manual layer kill request in Cueweb's context menu by ${username}`;
    killLayers(layers, username, reason);
}

export function eatLayerFramesGivenRow(row: Row<any>) {
    const layers = [row.original]
    eatLayersFrames(layers);
}

export function retryLayerFramesGivenRow(row: Row<any>) {
    const layers = [row.original]
    retryLayersFrames(layers);
}

export function retryLayerDeadFramesGivenRow(row: Row<any>) {
    const layers = [row.original]
    retryLayersDeadFrames(layers);
}

/********************************/
/* Frame context menu functions */
/********************************/

export function retryFrameGivenRow(row: Row<any>) {
    const frames = [row.original];
    retryFrames(frames);
}

export function killFrameGivenRow(row: Row<any>, username: string) {
    const frames = [row.original];
    const reason = `Manual frame kill request in Cueweb's context menu by ${username}`;
    killFrames(frames, username, reason);
}

export function eatFrameGivenRow(row: Row<any>) {
    const frames = [row.original];
    eatFrames(frames);
}

/**********************************************/
/* Per-row wrappers for the expanded job menu */
/**********************************************/

export function unpauseJobGivenRow(row: Row<any>) {
  unpauseJobs([row.original]);
}

export function autoEatOnGivenRow(row: Row<any>) {
  setJobAutoEat(row.original, true);
}

export function autoEatOffGivenRow(row: Row<any>) {
  setJobAutoEat(row.original, false);
}

export function dropExternalDependsGivenRow(row: Row<any>) {
  dropJobDepends(row.original, "EXTERNAL");
}

export function dropInternalDependsGivenRow(row: Row<any>) {
  dropJobDepends(row.original, "INTERNAL");
}

// Prompt-driven wrappers. CueGUI's MenuActions uses Qt input dialogs; we
// reuse window.prompt for parity in this round. A native shadcn dialog
// replacement is a follow-up.
export function setPriorityGivenRow(row: Row<any>) {
  const job = row.original as Job;
  const raw = window.prompt(`Set priority for ${job.name}`, String(job.priority ?? 100));
  if (raw === null) return;
  const value = Number.parseInt(raw, 10);
  if (Number.isNaN(value)) {
    toastWarning("Priority must be an integer");
    return;
  }
  setJobPriority(job, value);
}

export function setMaxRetriesGivenRow(row: Row<any>) {
  const job = row.original as Job;
  const raw = window.prompt(`Set max retries for ${job.name}`, "3");
  if (raw === null) return;
  const value = Number.parseInt(raw, 10);
  if (Number.isNaN(value) || value < 0) {
    toastWarning("Max retries must be a non-negative integer");
    return;
  }
  setJobMaxRetries(job, value);
}

// Pure-client clipboard helpers; surface a toast on success/failure so the
// user gets the same feedback as for back-end actions.
export async function copyJobNameGivenRow(row: Row<any>) {
  const job = row.original as Job;
  try {
    await navigator.clipboard.writeText(job.name);
    toastSuccess(`Copied job name: ${job.name}`);
  } catch (err) {
    handleError(err, "Could not copy job name to clipboard");
  }
}

export async function copyLogDirGivenRow(row: Row<any>) {
  const job = row.original as Job;
  if (!job.logDir) {
    toastWarning("Job has no logDir set");
    return;
  }
  try {
    await navigator.clipboard.writeText(job.logDir);
    toastSuccess(`Copied log directory: ${job.logDir}`);
  } catch (err) {
    handleError(err, "Could not copy log directory to clipboard");
  }
}