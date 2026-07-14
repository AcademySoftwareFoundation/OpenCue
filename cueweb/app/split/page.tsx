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

import { SplitView } from "@/components/ui/split-view";

/**
 * Multi-pane workspace route: `/split?left=/jobs&right=/hosts/server-01`.
 * SplitView reads the pane targets from the query string, so it's wrapped in a
 * Suspense boundary (required for `useSearchParams`).
 */
export default function SplitPage() {
  return (
    <React.Suspense fallback={null}>
      <SplitView />
    </React.Suspense>
  );
}
