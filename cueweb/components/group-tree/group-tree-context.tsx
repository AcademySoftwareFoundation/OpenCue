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

import { createContext, useContext } from "react";
import type { JobsState } from "./dnd-helpers";

type TreeCtx = {
  expanded: Set<string>;
  onToggle: (groupId: string, open: boolean) => void;
  jobsByGroup: JobsState;
  requestJobsFor: (groupId: string) => void;
  // True when the in-progress drag could legally drop on this group.
  isValidDropTarget: (groupId: string) => boolean;
};

const GroupTreeContext = createContext<TreeCtx | null>(null);

export const GroupTreeProvider = GroupTreeContext.Provider;

export function useGroupTree(): TreeCtx {
  const ctx = useContext(GroupTreeContext);
  if (!ctx) {
    throw new Error("useGroupTree must be used inside a GroupTreeProvider");
  }
  return ctx;
}
