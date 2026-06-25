"use client";

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

import type { Job } from "@/app/jobs/columns";

// Job "Booking Bar" (CueGUI ItemDelegate.JobBookingBarDelegate). A horizontal
// bar scaled to running + waiting frames: the left (running) portion is yellow,
// the remaining (waiting) portion sky-blue. Two vertical markers show the
// job's min-cores (cyan) and max-cores (red) targets, expressed in frames via
// the current cores-per-frame, exactly like CueGUI's Monitor Cue.
const RUNNING = "#c8c837"; // cuegui frame_state RUNNING [200,200,55]
const WAITING = "#87cfeb"; // cuegui frame_state WAITING [135,207,235]
const MIN_MARKER = "#3aa3d1"; // pause/cyan
const MAX_MARKER = "#ff0000"; // kill/red

export function JobBookingBar({ job }: { job: Job }) {
  const s = job.jobStats;
  const running = s?.runningFrames ?? 0;
  const waiting = s?.waitingFrames ?? 0;
  const reserved = s?.reservedCores ?? 0;
  const denom = running + waiting;

  if (denom <= 0) {
    return <div className="h-3.5 w-full rounded-sm bg-muted/20" aria-hidden="true" />;
  }

  // cores_per_frame = reserved / running (CueGUI falls back to 6 when nothing
  // is running yet), then min/max cores are converted to a frame count.
  const coresPerFrame = running > 0 ? reserved / running : 6;
  const jobMin = coresPerFrame > 0 ? Math.floor((job.minCores ?? 0) / coresPerFrame) : 0;
  const jobMax = coresPerFrame > 0 ? Math.floor((job.maxCores ?? 0) / coresPerFrame) : 0;

  const pct = (v: number) => `${Math.max(0, Math.min(1, v / denom)) * 100}%`;

  // Outer box height matches the text-row height so Monitor Cue job rows are no
  // taller than the show/group header rows; the min/max markers run top-to-bottom
  // of it and the running/waiting bar is a thin, vertically-centred, inset track.
  return (
    <div
      className="relative h-5 w-full min-w-[8rem] px-3"
      title={`Running ${running}, Waiting ${waiting} — cyan = min cores, red = max cores`}
    >
      <div className="relative h-full">
        {/* Waiting (sky-blue) track with the running (yellow) portion on the left. */}
        <div
          className="absolute inset-x-0 top-1/2 h-2 -translate-y-1/2 overflow-hidden rounded-sm"
          style={{ backgroundColor: WAITING }}
        >
          <div className="absolute inset-y-0 left-0" style={{ width: pct(running), backgroundColor: RUNNING }} />
        </div>
        {/* Full-height min-cores (cyan) and max-cores (red) target markers. */}
        <div className="absolute inset-y-0 w-px" style={{ left: pct(jobMin), backgroundColor: MIN_MARKER }} />
        <div className="absolute inset-y-0 w-px" style={{ left: pct(jobMax), backgroundColor: MAX_MARKER }} />
      </div>
    </div>
  );
}
