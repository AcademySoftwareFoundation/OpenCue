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

import {
  getDefaultEnabledPluginNames,
  getEnabledPluginNames,
  PLUGIN_MENU_CHANGED_EVENT,
  PLUGIN_MENU_STORAGE_KEY,
  setPluginMenuEnabled,
} from "@/lib/plugins";

/**
 * Which plugins appear in the Plugins menu (sidebar + header). Persisted to
 * `localStorage` and synced across components via a CustomEvent (same tab) and
 * the browser `storage` event (cross-tab) — the same pattern as
 * `useCuebotFacility`.
 *
 * SSR-safe: the initial render uses the manifest defaults (no `localStorage`),
 * matching the server-rendered DOM, then reconciles from storage on mount.
 */
export function useEnabledPlugins(): {
  enabled: Set<string>;
  isEnabled: (name: string) => boolean;
  setEnabled: (name: string, enabled: boolean) => void;
} {
  const [enabled, setEnabledState] = React.useState<Set<string>>(
    () => new Set(getDefaultEnabledPluginNames()),
  );

  React.useEffect(() => {
    const read = () => setEnabledState(new Set(getEnabledPluginNames()));
    read();

    const onStorage = (event: StorageEvent) => {
      if (event.key === PLUGIN_MENU_STORAGE_KEY) read();
    };
    window.addEventListener(PLUGIN_MENU_CHANGED_EVENT, read);
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener(PLUGIN_MENU_CHANGED_EVENT, read);
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  const isEnabled = React.useCallback((name: string) => enabled.has(name), [enabled]);
  const setEnabled = React.useCallback((name: string, value: boolean) => {
    setPluginMenuEnabled(name, value);
  }, []);

  return { enabled, isEnabled, setEnabled };
}
