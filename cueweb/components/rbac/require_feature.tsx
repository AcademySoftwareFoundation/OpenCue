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

import { useFeature, useIsAdmin } from "./use_roles";

/**
 * Renders `children` only when the current session holds the named
 * feature. The default `fallback` is `null` (the menu / button just
 * disappears) to match the CueGUI behavior of "you don't see what you
 * can't use." Pass a custom `fallback` for read-only previews.
 */
export function RequireFeature({
  name,
  children,
  fallback = null,
}: {
  name: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}): React.ReactElement | null {
  const allowed = useFeature(name);
  return <>{allowed ? children : fallback}</>;
}

export function RequireAdmin({
  children,
  fallback = null,
}: {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}): React.ReactElement | null {
  const isAdmin = useIsAdmin();
  return <>{isAdmin ? children : fallback}</>;
}
