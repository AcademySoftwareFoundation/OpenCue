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

import type { Layer } from "@/app/layers/layer-columns";

// Shared CustomEvent names + payload types for the Layer row actions. Kept
// in one module so the dialog that dispatches/handles these events and the
// page that reconciles them agree on the contract, without importing across
// sibling components. Mirrors host-action-events.ts.

// Opens the layer property editor (EditLayerPropertiesDialog).
export const OPEN_LAYER_PROPERTIES_EVENT = "cueweb:open-layer-properties";
export type OpenLayerPropertiesDetail = {
  layer: Layer;
};

// Fired after a layer property edit so the open layers table can update the
// affected row immediately (optimistic) instead of waiting for the next 5s
// poll. The page applies `patch` to every row whose id is in layerIds, then
// the poll reconciles with Cuebot.
export const LAYERS_CHANGED_EVENT = "cueweb:layers-changed";
export type LayersChangedDetail = {
  layerIds: string[];
  patch: Partial<Pick<Layer, "minMemory" | "minCores" | "tags">>;
};
