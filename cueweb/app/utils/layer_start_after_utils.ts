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

// Helpers for a layer's start-after gate: the time before which no frame of
// the layer may start. Set by an operator (Set Start After...) or written
// automatically by Cuebot's exit-status backoff, e.g. a license shortage.

// startAfter as a plain number, tolerating the gateway's int64-as-string
// marshalling and a missing field on an older Cuebot. 0 means "no delay".
export function layerStartAfterSeconds(layer: Layer): number {
  const value = Number(layer?.startAfter ?? 0);
  return Number.isFinite(value) ? value : 0;
}

// True while the layer's start-after gate is still in the future.
export function isLayerDelayed(layer: Layer): boolean {
  return layerStartAfterSeconds(layer) > Date.now() / 1000;
}

// Row tint for a delayed layer (CueGUI COLOR_LAYER_DELAYED_BACKGROUND).
// Self-clearing: once the deadline passes, the next table render drops the
// tint. Returns a Tailwind class for SimpleDataTable's getRowClassName hook.
//
// The hover variants are required, not decorative: TableRow carries
// `hover:bg-muted/50`, and a bare `bg-amber-100` loses to it on hover - so the
// tint would disappear at exactly the moment the operator hovers the row to
// read the Start After reason. Restating it under `hover:` keeps the row
// legible as delayed while pointed at (twMerge drops the base hover rule).
export function layerRowClassName(layer: Layer): string | undefined {
  return isLayerDelayed(layer)
    ? "bg-amber-100 hover:bg-amber-200 dark:bg-amber-950/40 dark:hover:bg-amber-900/50"
    : undefined;
}
