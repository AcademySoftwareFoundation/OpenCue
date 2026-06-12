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

import { handleError } from "@/app/utils/notify_utils";

/*****************************************************************/
// Utility functions for layers and frames, which include:
// - converting unix time to year-month-day hours-minutes format
// - converting memory amount to a string
// - converting seconds to hours, minutes, and seconds
// - converting seconds to hours and minutes
/*****************************************************************/

// Converts a Unix timestamp to a human-readable date in the format "YYYY-MM-DD HH:MM"
export const convertUnixToHumanReadableDate = (timestamp: number): string => {
  if (timestamp === 0) {
    return "";
  }
  
  const date = new Date(timestamp * 1000);
  const year = date.getFullYear();
  const month = (date.getMonth() + 1).toString().padStart(2, "0");
  const day = date.getDate().toString().padStart(2, "0");
  const hours = date.getHours().toString().padStart(2, "0");
  const minutes = date.getMinutes().toString().padStart(2, "0");

  return `${year}-${month}-${day} ${hours}:${minutes}`;
};

// Converts memory in kilobytes to a human-readable string (K, M, G)
// Logs a warning if the memory is NaN
export const convertMemoryToString = (kmem: number, object: string): string => {
  const k = 1024;

  if (kmem < k) {
    return `${kmem}K`;
  }

  if (kmem < k * k) {
    return `${Math.floor(kmem / k)}M`;
  }

  const mem = kmem / (k * k);
  if (isNaN(mem)) {
    handleError(`Memory is NaN\nFor object: ${object}`);
    return "";
  }

  return `${mem.toFixed(1)}G`;
};

// Parse a user-entered memory string into KB (the unit Cuebot stores layer
// min_memory in). Accepts an optional unit suffix - K/KB, M/MB, G/GB,
// T/TB (case-insensitive); a bare number is interpreted as GB, matching
// CueGUI's LayerDialog whose memory spinner is labelled in GB. Returns null
// when the input is blank, not a finite positive number, or carries an
// unrecognised unit, so callers can surface a validation error.
//
//   "4"     -> 4 GB  -> 4194304 KB
//   "512M"  -> 512 MB -> 524288 KB
//   "2.5gb" -> 2.5 GB -> 2621440 KB
export const parseMemoryToKb = (input: string): number | null => {
  const trimmed = input.trim();
  if (trimmed === "") return null;

  const match = trimmed.match(/^([0-9]*\.?[0-9]+)\s*([a-zA-Z]*)$/);
  if (!match) return null;

  const value = Number.parseFloat(match[1]);
  if (!Number.isFinite(value) || value <= 0) return null;

  const unit = match[2].toLowerCase();
  const multipliers: Record<string, number> = {
    "": 1024 * 1024, // bare number == GB (CueGUI parity)
    k: 1,
    kb: 1,
    m: 1024,
    mb: 1024,
    g: 1024 * 1024,
    gb: 1024 * 1024,
    t: 1024 * 1024 * 1024,
    tb: 1024 * 1024 * 1024,
  };
  if (!(unit in multipliers)) return null;

  return Math.round(value * multipliers[unit]);
};

// Format a KB amount as a GB string for editing (e.g. 4194304 -> "4"). Used
// to seed the memory input of the layer property dialog. Keeps up to two
// decimals and trims trailing zeros so common round values stay tidy.
export const formatKbToGbInput = (kb: number): string => {
  if (!Number.isFinite(kb) || kb <= 0) return "";
  const gb = kb / (1024 * 1024);
  return Number.parseFloat(gb.toFixed(2)).toString();
};

// Converts seconds to a string formatted as HH:MM:SS
export const secondsToHHMMSS = (sec: number): string => {
  // Floor the input so fractional inputs (e.g. (Date.now()/1000) deltas)
  // don't bleed micro-seconds into the seconds component.
  const total = Math.max(0, Math.floor(sec));
  const hours = Math.floor(total / 3600).toString().padStart(2, "0");
  const minutes = Math.floor((total % 3600) / 60).toString().padStart(2, "0");
  const seconds = (total % 60).toString().padStart(2, "0");

  return `${hours}:${minutes}:${seconds}`;
};

// Converts seconds to a string formatted as HHH:MM
export const secondsToHHHMM = (sec: number): string => {
  const hours = Math.floor(sec / 3600).toString().padStart(3, "0");
  const minutes = Math.floor((sec % 3600) / 60).toString().padStart(2, "0");

  return `${hours}:${minutes}`;
};

// Converts seconds to a human-readable age string (e.g., "2h 14m" or "3d 4h")
export const secondsToHumanAge = (sec: number): string => {
  if (sec < 0) {
    return "0m";
  }

  const days = Math.floor(sec / 86400);
  const hours = Math.floor((sec % 86400) / 3600);
  const minutes = Math.floor((sec % 3600) / 60);

  if (days > 0) {
    return `${days}d ${hours}h`;
  }

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }

  return `${minutes}m`;
};
