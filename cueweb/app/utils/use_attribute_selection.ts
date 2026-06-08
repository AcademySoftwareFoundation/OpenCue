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

"use client";

import * as React from "react";

/**
 * Shared "what is currently being inspected" state for the Attributes
 * panel (CueGUI parity - Views/Plugins > Other > Attributes).
 *
 * Single source of truth lives in a module-scoped variable + a CustomEvent
 * for same-tab sync. Not persisted; selection is transient per session.
 *
 * Producers (e.g. the jobs table row click handler) call `setSelection()`
 * from anywhere. Consumers (the AttributesPanel) subscribe via the hook.
 */

export type AttributeSelectionType = "job" | "layer" | "frame" | "host";

export interface AttributeSelection {
  type: AttributeSelectionType;
  id: string;
  name: string;
  /** Raw entity payload - used by the panel to derive the attribute tree. */
  data: Record<string, unknown>;
}

const CHANGE_EVENT = "cueweb:attribute-selection-changed";

let _selection: AttributeSelection | null = null;

function dispatchChange(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
}

export function setAttributeSelection(
  next: AttributeSelection | null,
): void {
  _selection = next;
  dispatchChange();
}

export function clearAttributeSelection(): void {
  setAttributeSelection(null);
}

export function useAttributeSelection(): {
  selection: AttributeSelection | null;
  setSelection: (next: AttributeSelection | null) => void;
  clearSelection: () => void;
} {
  const [selection, setSelectionState] =
    React.useState<AttributeSelection | null>(_selection);

  React.useEffect(() => {
    const handler = () => setSelectionState(_selection);
    window.addEventListener(CHANGE_EVENT, handler);
    return () => window.removeEventListener(CHANGE_EVENT, handler);
  }, []);

  return {
    selection,
    setSelection: setAttributeSelection,
    clearSelection: clearAttributeSelection,
  };
}
