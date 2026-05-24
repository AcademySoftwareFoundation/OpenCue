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

// Canonical permission strings. UI components and API route handlers
// gate on these. The "*" wildcard implicitly grants every permission;
// only built-in roles should hold it.
export const PERMISSIONS = {
  WILDCARD: "*",

  // Jobs
  JOBS_VIEW: "jobs.view",
  JOBS_KILL: "jobs.kill",
  JOBS_RETRY: "jobs.retry",
  JOBS_PAUSE: "jobs.pause",
  JOBS_EAT: "jobs.eat",
  JOBS_SET_MAX_RETRIES: "jobs.set_max_retries",
  JOBS_SET_AUTO_EAT: "jobs.set_auto_eat",
  JOBS_SET_PRIORITY: "jobs.set_priority",

  // Layers
  LAYERS_VIEW: "layers.view",
  LAYERS_KILL: "layers.kill",
  LAYERS_RETRY: "layers.retry",

  // Frames
  FRAMES_VIEW: "frames.view",
  FRAMES_EAT: "frames.eat",
  FRAMES_RETRY: "frames.retry",
  FRAMES_KILL: "frames.kill",

  // Hosts
  HOSTS_VIEW: "hosts.view",
  HOSTS_LOCK: "hosts.lock",
  HOSTS_UNLOCK: "hosts.unlock",
  HOSTS_REBOOT: "hosts.reboot",

  // Shows / subscriptions
  SHOWS_VIEW: "shows.view",
  SHOWS_EDIT: "shows.edit",

  // High-level UI surfaces
  CUECOMMANDER_OPEN: "cuecommander.open",
} as const;

export type PermissionString = (typeof PERMISSIONS)[keyof typeof PERMISSIONS];

// All known permissions, used to populate the Admin UI "Permissions"
// tab as a read-only catalog.
export const PERMISSION_CATALOG: ReadonlyArray<{
  key: PermissionString;
  description: string;
}> = [
  { key: PERMISSIONS.WILDCARD, description: "All permissions (super-admin)" },

  { key: PERMISSIONS.JOBS_VIEW, description: "View jobs in the Jobs table" },
  { key: PERMISSIONS.JOBS_KILL, description: "Kill jobs" },
  { key: PERMISSIONS.JOBS_RETRY, description: "Retry dead frames on jobs" },
  { key: PERMISSIONS.JOBS_PAUSE, description: "Pause and unpause jobs" },
  { key: PERMISSIONS.JOBS_EAT, description: "Eat dead frames on jobs" },
  { key: PERMISSIONS.JOBS_SET_MAX_RETRIES, description: "Set per-job max retries" },
  { key: PERMISSIONS.JOBS_SET_AUTO_EAT, description: "Toggle per-job auto-eat" },
  { key: PERMISSIONS.JOBS_SET_PRIORITY, description: "Adjust per-job dispatch priority (1-100)" },

  { key: PERMISSIONS.LAYERS_VIEW, description: "View layers" },
  { key: PERMISSIONS.LAYERS_KILL, description: "Kill layers" },
  { key: PERMISSIONS.LAYERS_RETRY, description: "Retry frames on layers" },

  { key: PERMISSIONS.FRAMES_VIEW, description: "View frames" },
  { key: PERMISSIONS.FRAMES_EAT, description: "Eat individual frames" },
  { key: PERMISSIONS.FRAMES_RETRY, description: "Retry individual frames" },
  { key: PERMISSIONS.FRAMES_KILL, description: "Kill individual frames" },

  { key: PERMISSIONS.HOSTS_VIEW, description: "View hosts" },
  { key: PERMISSIONS.HOSTS_LOCK, description: "Lock hosts" },
  { key: PERMISSIONS.HOSTS_UNLOCK, description: "Unlock hosts" },
  { key: PERMISSIONS.HOSTS_REBOOT, description: "Reboot hosts" },

  { key: PERMISSIONS.SHOWS_VIEW, description: "View shows" },
  { key: PERMISSIONS.SHOWS_EDIT, description: "Edit show settings" },

  {
    key: PERMISSIONS.CUECOMMANDER_OPEN,
    description: "Access the CueCommander menu and pages",
  },
];

/**
 * Returns true if the holder's permissions list covers the requested permission.
 * The "*" wildcard satisfies any check.
 */
export function hasPermission(
  held: ReadonlyArray<string>,
  required: string,
): boolean {
  if (held.includes(PERMISSIONS.WILDCARD)) return true;
  return held.includes(required);
}

/**
 * Returns true if the holder has every permission in `required`.
 */
export function hasAllPermissions(
  held: ReadonlyArray<string>,
  required: ReadonlyArray<string>,
): boolean {
  if (held.includes(PERMISSIONS.WILDCARD)) return true;
  for (const r of required) {
    if (!held.includes(r)) return false;
  }
  return true;
}
