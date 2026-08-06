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
 * Persisted "Immersive" (full-screen) layout flag - the CueGUI Toggle
 * Full-Screen equivalent (`cuegui/cuegui/MainWindow.py`). When true, the
 * global header, sidebar and status bar are hidden so the active table gets
 * the full viewport height for a clean, dense view.
 *
 * Single source of truth is `localStorage[STORAGE_KEY]`. Consumers stay in
 * sync via:
 *   - a `cueweb:immersive-changed` CustomEvent (same-tab)
 *   - the browser's built-in `storage` event (cross-tab)
 *
 * Mirrors `use_disable_job_interaction.ts` so all CueWeb boolean prefs behave
 * identically (SSR-safe hydration + same-tab + cross-tab sync).
 */

export const STORAGE_KEY = "cueweb.layout.immersive";
const CHANGE_EVENT = "cueweb:immersive-changed";

export function readImmersiveFromStorage(): boolean {
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

export function useImmersiveMode(): {
  immersive: boolean;
  setImmersive: (value: boolean) => void;
  toggle: () => void;
} {
  // SSR-safe: start `false` on the server and on the first client render so
  // hydration matches. Reconcile from localStorage in an effect.
  const [immersive, setImmersiveState] = React.useState<boolean>(false);

  React.useEffect(() => {
    setImmersiveState(readImmersiveFromStorage());

    // Same-tab sync across the several useImmersiveMode() instances (app-shell,
    // app-header, shortcuts-overlay): trust the value carried on the event
    // rather than re-reading storage, so a failed/blocked localStorage write
    // (private mode, quota) can't immediately revert the toggle.
    const handler = (event: Event) => {
      if (event instanceof CustomEvent && typeof event.detail === "boolean") {
        setImmersiveState(event.detail);
        return;
      }
      setImmersiveState(readImmersiveFromStorage());
    };
    // Cross-tab sync: another tab's write is authoritative, so read it back.
    const storageHandler = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) setImmersiveState(readImmersiveFromStorage());
    };

    window.addEventListener(CHANGE_EVENT, handler);
    window.addEventListener("storage", storageHandler);
    return () => {
      window.removeEventListener(CHANGE_EVENT, handler);
      window.removeEventListener("storage", storageHandler);
    };
  }, []);

  const setImmersive = React.useCallback((value: boolean) => {
    writeToStorage(value);
    setImmersiveState(value);
    if (typeof window !== "undefined") {
      window.dispatchEvent(
        new CustomEvent<boolean>(CHANGE_EVENT, { detail: value }),
      );
    }
  }, []);

  // Flip based on the current in-memory state (kept fresh by the listeners
  // above) instead of re-reading storage, so toggling stays reliable even when
  // the previous write didn't persist.
  const toggle = React.useCallback(() => {
    setImmersive(!immersive);
  }, [immersive, setImmersive]);

  return { immersive, setImmersive, toggle };
}
