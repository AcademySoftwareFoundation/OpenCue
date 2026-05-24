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

import { PERMISSIONS, type PermissionString } from "./permissions";

// Built-in roles. Seeded on first launch and reseeded if any role row
// is missing from the DB. Custom roles created via the Admin UI live
// alongside these but have `builtin=0`.
export type BuiltinRoleSeed = {
  name: string;
  description: string;
  permissions: ReadonlyArray<PermissionString>;
};

export const BUILTIN_ROLES = {
  SITE_ADMIN: "site-admin",
  OPERATOR: "operator",
  VIEWER: "viewer",
} as const;

export const BUILTIN_ROLE_SEEDS: ReadonlyArray<BuiltinRoleSeed> = [
  {
    name: BUILTIN_ROLES.SITE_ADMIN,
    description:
      "Full access to every feature, including the Admin UI. Cannot be deleted.",
    permissions: [PERMISSIONS.WILDCARD],
  },
  {
    name: BUILTIN_ROLES.OPERATOR,
    description:
      "Day-to-day production operator: can kill, retry, pause, and eat on jobs/frames.",
    permissions: [
      PERMISSIONS.JOBS_VIEW,
      PERMISSIONS.JOBS_KILL,
      PERMISSIONS.JOBS_RETRY,
      PERMISSIONS.JOBS_PAUSE,
      PERMISSIONS.JOBS_EAT,
      PERMISSIONS.JOBS_SET_MAX_RETRIES,
      PERMISSIONS.JOBS_SET_AUTO_EAT,
      PERMISSIONS.JOBS_SET_PRIORITY,
      PERMISSIONS.LAYERS_VIEW,
      PERMISSIONS.LAYERS_KILL,
      PERMISSIONS.LAYERS_RETRY,
      PERMISSIONS.FRAMES_VIEW,
      PERMISSIONS.FRAMES_EAT,
      PERMISSIONS.FRAMES_RETRY,
      PERMISSIONS.FRAMES_KILL,
      PERMISSIONS.HOSTS_VIEW,
      PERMISSIONS.HOSTS_LOCK,
      PERMISSIONS.HOSTS_UNLOCK,
      PERMISSIONS.SHOWS_VIEW,
      PERMISSIONS.CUECOMMANDER_OPEN,
    ],
  },
  {
    name: BUILTIN_ROLES.VIEWER,
    description: "Read-only access to jobs, layers, frames, hosts, and shows.",
    permissions: [
      PERMISSIONS.JOBS_VIEW,
      PERMISSIONS.LAYERS_VIEW,
      PERMISSIONS.FRAMES_VIEW,
      PERMISSIONS.HOSTS_VIEW,
      PERMISSIONS.SHOWS_VIEW,
    ],
  },
];

export function isBuiltinRole(name: string): boolean {
  return BUILTIN_ROLE_SEEDS.some((r) => r.name === name);
}
