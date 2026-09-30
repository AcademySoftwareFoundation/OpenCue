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

// Persisted preference: should every triggered keyboard shortcut fire a
// toast? Default true so the user discovers them quickly; can be opted out
// via the "Other" menu in either the header or the sidebar.
const STORAGE_KEY = "cueweb.shortcutNotifications";
const CHANGE_EVENT = "cueweb:shortcut-notifications-changed";
const DEFAULT_VALUE = true;

function readFromStorage(): boolean {
  if (typeof window === "undefined") return DEFAULT_VALUE;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw === null) return DEFAULT_VALUE;
    const parsed = JSON.parse(raw);
    return typeof parsed === "boolean" ? parsed : DEFAULT_VALUE;
  } catch {
    return DEFAULT_VALUE;
  }
}

function writeToStorage(value: boolean): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  } catch {
    // Quota / private mode; ignore.
  }
}

/**
 * Imperative read used by the keyboard handler (which fires the toast).
 * Avoids subscribing to state updates from the hook below in callsites that
 * don't render anything based on the pref.
 */
export function getShortcutNotificationsEnabled(): boolean {
  return readFromStorage();
}

/**
 * React hook with cross-tab sync. Use in menu items that show the current
 * checked state and let the user flip it.
 */
export function useShortcutNotifications() {
  const [enabled, setEnabledState] = React.useState<boolean>(DEFAULT_VALUE);

  React.useEffect(() => {
    // Sync after mount so SSR (which can't read localStorage) still renders.
    setEnabledState(readFromStorage());
    const refresh = () => setEnabledState(readFromStorage());
    const storage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) refresh();
    };
    window.addEventListener(CHANGE_EVENT, refresh);
    window.addEventListener("storage", storage);
    return () => {
      window.removeEventListener(CHANGE_EVENT, refresh);
      window.removeEventListener("storage", storage);
    };
  }, []);

  const setEnabled = React.useCallback((value: boolean) => {
    writeToStorage(value);
    setEnabledState(value);
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
    }
  }, []);

  const toggle = React.useCallback(() => {
    setEnabled(!readFromStorage());
  }, [setEnabled]);

  return { enabled, setEnabled, toggle };
}
