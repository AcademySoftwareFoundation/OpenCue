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

// Per-field history for CueSubmit autocomplete. Mirrors what the
// standalone cuesubmit Python app does with its on-disk cache: when
// you submit a job, the values you typed into Job Name / Shot / Layer
// Name are remembered and offered back the next time you start typing
// in the same field.
//
// Each field gets its own localStorage key. We cap each list at
// HISTORY_MAX to keep storage small, and dedupe new entries by
// case-insensitive match so "test-Job" doesn't shadow "test-job".

const HISTORY_KEY_PREFIX = "cueweb.cuesubmit.history.";
const HISTORY_MAX = 25;

export type HistoryField = "jobName" | "shot" | "layerName";

function keyFor(field: HistoryField): string {
  return `${HISTORY_KEY_PREFIX}${field}`;
}

export function loadHistory(field: HistoryField): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(keyFor(field));
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((v): v is string => typeof v === "string");
  } catch {
    return [];
  }
}

/**
 * Push a new value to the front of the field's history, deduped
 * case-insensitively. No-op when the value is empty or when running
 * in SSR.
 */
export function rememberHistory(field: HistoryField, value: string): void {
  if (typeof window === "undefined") return;
  const trimmed = value.trim();
  if (!trimmed) return;
  try {
    const current = loadHistory(field);
    const lower = trimmed.toLowerCase();
    const deduped = current.filter((v) => v.toLowerCase() !== lower);
    deduped.unshift(trimmed);
    localStorage.setItem(
      keyFor(field),
      JSON.stringify(deduped.slice(0, HISTORY_MAX)),
    );
  } catch {
    // private mode / quota - silently drop
  }
}

/**
 * Convenience: remember every history field touched by a successful
 * submit in one call. Called from the submit handler.
 */
export function rememberSubmission(values: {
  jobName: string;
  shot: string;
  layers: ReadonlyArray<{ name: string }>;
}): void {
  rememberHistory("jobName", values.jobName);
  rememberHistory("shot", values.shot);
  for (const layer of values.layers) {
    rememberHistory("layerName", layer.name);
  }
}
