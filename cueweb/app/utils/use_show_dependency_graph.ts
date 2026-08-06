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
 * Shared show/hide state for the inline Dependency Graph panel.
 *
 * Persisted in localStorage under `cueweb.jobs.showDependencyGraph` and
 * synchronised:
 *   - across components in the same tab via a CustomEvent dispatched on
 *     `window` (so the Cuetopia > View Job Graph menu item and the
 *     graph panel header stay in lockstep without prop drilling);
 *   - across tabs via the browser `storage` event.
 */

const STORAGE_KEY = "cueweb.jobs.showDependencyGraph";
export const SHOW_DEP_GRAPH_CHANGED_EVENT = "cueweb:show-dependency-graph-changed";

export function useShowDependencyGraph(): {
  show: boolean;
  set: (next: boolean) => void;
  toggle: () => void;
} {
  // Hydrate to false on first render so SSR and the first client paint
  // agree; the effect below upgrades it from localStorage right away.
  const [show, setShow] = React.useState<boolean>(false);

  React.useEffect(() => {
    if (typeof window === "undefined") return;
    setShow(window.localStorage.getItem(STORAGE_KEY) === "1");
  }, []);

  React.useEffect(() => {
    if (typeof window === "undefined") return;
    const onCustom = (e: Event) => {
      const detail = (e as CustomEvent<{ show: boolean }>).detail;
      if (typeof detail?.show === "boolean") setShow(detail.show);
    };
    const onStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) setShow(e.newValue === "1");
    };
    window.addEventListener(SHOW_DEP_GRAPH_CHANGED_EVENT, onCustom);
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener(SHOW_DEP_GRAPH_CHANGED_EVENT, onCustom);
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  const set = React.useCallback((next: boolean) => {
    if (typeof window === "undefined") {
      setShow(next);
      return;
    }
    window.localStorage.setItem(STORAGE_KEY, next ? "1" : "0");
    // Same-tab sync via CustomEvent. Other listeners pick it up
    // synchronously; cross-tab listeners use the storage event above.
    window.dispatchEvent(
      new CustomEvent(SHOW_DEP_GRAPH_CHANGED_EVENT, { detail: { show: next } }),
    );
    setShow(next);
  }, []);

  const toggle = React.useCallback(() => {
    set(!show);
  }, [set, show]);

  return { show, set, toggle };
}
