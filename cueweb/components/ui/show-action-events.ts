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

import type { Show } from "@/app/utils/get_utils";

// Shared CustomEvent names + payload types for the Shows window dialogs,
// kept in one module so the row context menu, the dialogs, and the page
// agree on the contract (same pattern as host-action-events.ts).

// Opens the Show Properties dialog (ShowPropertiesDialog).
export const OPEN_SHOW_PROPERTIES_EVENT = "cueweb:open-show-properties";
export type OpenShowPropertiesDetail = {
  show: Show;
};

// Opens the Create Subscription dialog (CreateSubscriptionDialog). The show
// is optional - the dialog pre-selects it when present, otherwise the user
// picks from the show dropdown.
export const OPEN_CREATE_SUBSCRIPTION_EVENT = "cueweb:open-create-subscription";
export type OpenCreateSubscriptionDetail = {
  show?: Show;
};

// Fired after a show changes (properties saved, subscription created) so the
// shows page can re-fetch.
export const SHOWS_CHANGED_EVENT = "cueweb:shows-changed";
