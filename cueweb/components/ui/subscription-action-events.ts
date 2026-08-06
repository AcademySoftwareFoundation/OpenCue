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

import type { Subscription } from "@/app/utils/get_utils";

// Shared CustomEvent names + payload types for the Subscriptions page dialogs,
// kept in one module so the row context menu, the dialogs, and the page agree
// on the contract (same pattern as show-action-events.ts).

// Opens the Edit Subscription Size dialog.
export const OPEN_EDIT_SUBSCRIPTION_SIZE_EVENT = "cueweb:open-edit-subscription-size";
// Opens the Edit Subscription Burst dialog.
export const OPEN_EDIT_SUBSCRIPTION_BURST_EVENT = "cueweb:open-edit-subscription-burst";
// Opens the Delete Subscription confirmation dialog.
export const OPEN_DELETE_SUBSCRIPTION_EVENT = "cueweb:open-delete-subscription";

export type OpenSubscriptionDetail = {
  subscription: Subscription;
};

// Fired after a subscription is changed (size/burst edited or deleted) so the
// Subscriptions page can re-fetch the current show's subscriptions.
export const SUBSCRIPTIONS_CHANGED_EVENT = "cueweb:subscriptions-changed";
