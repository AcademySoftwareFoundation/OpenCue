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

import type { Limit } from "@/app/utils/get_utils";

// Shared CustomEvent names + payload types for the Limits window dialogs,
// kept in one module so the row context menu, the dialogs, and the page agree
// on the contract (same pattern as host-/show-action-events).

export const OPEN_LIMIT_EDIT_MAX_VALUE_EVENT = "cueweb:open-limit-edit-max-value";
export const OPEN_LIMIT_RENAME_EVENT = "cueweb:open-limit-rename";
export const OPEN_LIMIT_DELETE_EVENT = "cueweb:open-limit-delete";

export type OpenLimitDetail = {
  limit: Limit;
};

// Fired after a limit changes (created, renamed, deleted, max value set) so
// the Limits page re-fetches.
export const LIMITS_CHANGED_EVENT = "cueweb:limits-changed";
