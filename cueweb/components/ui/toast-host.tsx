"use client";

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

import * as React from "react";
import { useTheme } from "next-themes";
import { Slide, ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

/**
 * Global host for all CueWeb toast notifications. Mount once at the root
 * (`app/layout.tsx`) so every route shares a single container and toasts
 * survive client-side navigations.
 *
 * The actual `toast.success` / `toast.error` / `toast.warn` calls live in
 * `cueweb/app/utils/notify_utils.ts` (`toastSuccess`, `toastWarning`,
 * `handleError`). That indirection lets us swap libraries later without
 * touching every callsite.
 *
 * Defaults:
 * - position: bottom-right (out of the way of the AppHeader)
 * - autoClose: 5000ms
 * - pauseOnHover: true (user can keep a toast on screen while reading)
 * - draggable, closeOnClick: react-toastify defaults
 * - hideProgressBar: false (the bar doubles as a visual countdown)
 * - newestOnTop: stack new toasts above older ones
 *
 * Visual theme tracks the next-themes `resolvedTheme` so the container
 * flips between "light" and "dark" instantly when the user toggles the
 * theme - no need to remount.
 */
export function ToastHost() {
  const { resolvedTheme } = useTheme();
  // Until next-themes has resolved (first paint), default to light to match
  // the server-rendered DOM; the actual theme attaches on the first effect.
  const theme = resolvedTheme === "dark" ? "dark" : "light";

  return (
    <ToastContainer
      position="bottom-right"
      autoClose={5000}
      hideProgressBar={false}
      newestOnTop
      closeOnClick
      pauseOnFocusLoss
      pauseOnHover
      draggable
      theme={theme}
      transition={Slide}
      // Reserve a small extra bottom offset so toasts stack above the
      // 24px status bar without overlapping it on either theme.
      style={{ bottom: "2.25rem" }}
    />
  );
}
