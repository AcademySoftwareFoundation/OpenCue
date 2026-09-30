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
 * Persisted "Disable Job Interaction" safety flag - the CueGUI File menu
 * equivalent (`cuegui/cuegui/MainWindow.py`). When true, destructive
 * actions across CueWeb should disable themselves and a banner is shown.
 *
 * Single source of truth is `localStorage[STORAGE_KEY]`. Consumers stay in
 * sync via:
 *   - a `cueweb:disable-job-interaction-changed` CustomEvent (same-tab)
 *   - the browser's built-in `storage` event (cross-tab)
 */

export const STORAGE_KEY = "cueweb.safety.disable-job-interaction";
const CHANGE_EVENT = "cueweb:disable-job-interaction-changed";

function readFromStorage(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw === null) return false;
    return JSON.parse(raw) === true;
  } catch {
    return false;
  }
}

function writeToStorage(value: boolean): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  } catch {
    // ignore (private mode / quota)
  }
}

export function useDisableJobInteraction(): {
  disabled: boolean;
  setDisabled: (value: boolean) => void;
  toggle: () => void;
} {
  // SSR-safe: start `false` on the server and on the first client render so
  // hydration matches. Reconcile from localStorage in an effect.
  const [disabled, setDisabledState] = React.useState<boolean>(false);

  React.useEffect(() => {
    setDisabledState(readFromStorage());

    const handler = () => setDisabledState(readFromStorage());
    const storageHandler = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) setDisabledState(readFromStorage());
    };

    window.addEventListener(CHANGE_EVENT, handler);
    window.addEventListener("storage", storageHandler);
    return () => {
      window.removeEventListener(CHANGE_EVENT, handler);
      window.removeEventListener("storage", storageHandler);
    };
  }, []);

  const setDisabled = React.useCallback((value: boolean) => {
    writeToStorage(value);
    setDisabledState(value);
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
    }
  }, []);

  const toggle = React.useCallback(() => {
    setDisabled(!readFromStorage());
  }, [setDisabled]);

  return { disabled, setDisabled, toggle };
}
