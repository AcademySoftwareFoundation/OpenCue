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

// Matches the cuesubmit "<label> ___________" section header style.
// The horizontal rule continues from the label to the right edge.
export function SectionHeader({ label }: { label: string }) {
  return (
    <div className="flex items-baseline gap-3 mt-6 mb-3">
      <span className="text-sm font-medium text-foreground/70">{label}</span>
      <span className="flex-1 border-b border-foreground/20" />
    </div>
  );
}
