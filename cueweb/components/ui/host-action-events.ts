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

import type { Host } from "@/app/utils/get_utils";

// Shared CustomEvent names + payload types for the Monitor Hosts row
// actions (lock/unlock, reboot). Kept in one module so the dialogs that
// dispatch these events and the hosts page that reconciles them agree on
// the contract, without importing across sibling dialog components.

// Opens the lock/unlock confirmation dialog (HostLockDialog).
export const OPEN_HOST_LOCK_EVENT = "cueweb:open-host-lock";
export type HostLockAction = "lock" | "unlock";
export type OpenHostLockDetail = {
  hosts: Host[];
  action: HostLockAction;
};

// Opens the immediate-reboot confirmation dialog (HostRebootDialog).
export const OPEN_HOST_REBOOT_EVENT = "cueweb:open-host-reboot";
export type OpenHostRebootDetail = {
  hosts: Host[];
};

// Opens the tag editor dialog (EditHostTagsDialog).
export const OPEN_HOST_TAGS_EVENT = "cueweb:open-host-tags";
export type OpenHostTagsDetail = {
  hosts: Host[];
};

// Opens the host comments dialog (HostCommentsDialog).
export const OPEN_HOST_COMMENTS_EVENT = "cueweb:open-host-comments";
export type OpenHostCommentsDetail = {
  hosts: Host[];
};

// Opens the rename-tag dialog (HostRenameTagDialog).
export const OPEN_HOST_RENAME_TAG_EVENT = "cueweb:open-host-rename-tag";
export type OpenHostRenameTagDetail = {
  hosts: Host[];
};

// Opens the change-allocation dialog (HostChangeAllocationDialog).
export const OPEN_HOST_ALLOCATION_EVENT = "cueweb:open-host-allocation";
export type OpenHostAllocationDetail = {
  hosts: Host[];
};

// Opens the delete-host confirmation dialog (HostDeleteDialog).
export const OPEN_HOST_DELETE_EVENT = "cueweb:open-host-delete";
export type OpenHostDeleteDetail = {
  hosts: Host[];
};

// Opens the take-ownership confirmation dialog (HostTakeOwnershipDialog).
export const OPEN_HOST_TAKE_OWNERSHIP_EVENT = "cueweb:open-host-take-ownership";
export type OpenHostTakeOwnershipDetail = {
  hosts: Host[];
};

// Drives the bottom Proc monitor panel ("View Procs"): the host panel asks
// the proc panel to load procs for these host names.
export const VIEW_HOST_PROCS_EVENT = "cueweb:view-host-procs";
export type ViewHostProcsDetail = {
  hostNames: string[];
};

// Fired after a host action so the open hosts table can update the
// affected rows immediately (optimistic) instead of waiting for the 30s
// poll. The page applies `patch` to every row whose id is in hostIds,
// then re-fetches to reconcile with Cuebot.
export const HOSTS_CHANGED_EVENT = "cueweb:hosts-changed";
export type HostsChangedDetail = {
  hostIds: string[];
  patch: Partial<Pick<Host, "lockState" | "state" | "tags" | "allocName">>;
};
