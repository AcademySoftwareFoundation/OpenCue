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

import { memo, useEffect, useMemo, useState } from "react";
import { useDraggable, useDroppable } from "@dnd-kit/react";
import { ChevronRight, Folder, GripVertical } from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import type { TreeNode } from "./build-tree";
import { JobLeaf } from "./job-leaf";
import { useGroupTree } from "./group-tree-context";
import { formatGroupDefaults } from "@/app/utils/group_defaults";

const INDENT_PER_LEVEL_REM = 1.25;
const BASE_PADDING_REM = 0.25;

type Props = {
  node: TreeNode;
  depth: number;
};

function GroupNodeBase({ node, depth }: Props) {
  const isRoot = depth === 0;
  const { expanded, onToggle, jobsByGroup, requestJobsFor, isValidDropTarget } =
    useGroupTree();
  const isOpen = isRoot || expanded.has(node.group.id);

  // Stable refs: dnd-kit's `data` identity affects isDragSource across renders.
  const dragData = useMemo(
    () => ({ type: "group" as const, name: node.group.name }),
    [node.group.name],
  );
  const dropData = useMemo(() => ({ type: "group" as const }), []);

  const { ref: dragRef, handleRef, isDragSource } = useDraggable({
    id: node.group.id,
    data: dragData,
    disabled: isRoot,
  });
  const { ref: dropRef, isDropTarget } = useDroppable({
    id: node.group.id,
    data: dropData,
    // The droppable wraps the whole region (header + children); collisionPriority
    // = depth makes the innermost region under the pointer win.
    collisionPriority: depth,
  });

  const setRowRef = dragRef;

  useEffect(() => {
    if (!isOpen) return;
    requestJobsFor(node.group.id);
  }, [isOpen, node.group.id, requestJobsFor]);

  const pendingJobs = node.rolledUpStats.pendingJobs;
  const runningFrames = node.rolledUpStats.runningFrames;
  const deadFrames = node.rolledUpStats.deadFrames;
  // Defaults this group applies on reparent; shown as a tooltip and a drag badge.
  const defaultsSummary = formatGroupDefaults(node.group);
  const paddingLeft = `${BASE_PADDING_REM + depth * INDENT_PER_LEVEL_REM}rem`;
  const jobsEntry = jobsByGroup.get(node.group.id);
  const jobs = Array.isArray(jobsEntry) ? jobsEntry : null;
  const jobsLoading = jobsEntry === "loading";

  // Delay the loading row so fast fetches don't flash it on expand.
  const [showJobsLoader, setShowJobsLoader] = useState(false);
  useEffect(() => {
    if (!jobsLoading) {
      setShowJobsLoader(false);
      return;
    }
    const timer = setTimeout(() => setShowJobsLoader(true), 200);
    return () => clearTimeout(timer);
  }, [jobsLoading]);

  const isValidTarget = isDropTarget && isValidDropTarget(node.group.id);

  // A <span> (not <div>) so it stays valid phrasing content when rendered
  // inside the CollapsibleTrigger <button> below.
  const stats = (
    <span className="ml-auto flex items-center gap-3 text-xs text-muted-foreground shrink-0">
      {isValidTarget && defaultsSummary && (
        <span className="text-primary">applies {defaultsSummary}</span>
      )}
      {runningFrames > 0 && <span>{runningFrames} running</span>}
      {pendingJobs > 0 && <span>{pendingJobs} pending</span>}
      {deadFrames > 0 && (
        <span className="text-red-600 dark:text-red-400">{deadFrames} dead</span>
      )}
    </span>
  );

  const childRows = (
    <>
      {node.children.map(child => (
        <GroupNode key={child.group.id} node={child} depth={depth + 1} />
      ))}
      {showJobsLoader && (
        <p
          className="text-xs text-muted-foreground py-1"
          style={{ paddingLeft: `${BASE_PADDING_REM + (depth + 1) * INDENT_PER_LEVEL_REM + 3}rem` }}
        >
          Loading jobs…
        </p>
      )}
      {jobs?.map(job => (
        <JobLeaf
          key={job.id}
          job={job}
          depth={depth + 1}
          fromGroupId={node.group.id}
        />
      ))}
    </>
  );

  const rowStyle: React.CSSProperties = {
    paddingLeft,
    visibility: isDragSource ? "hidden" : undefined,
  };
  const dropHighlight = isValidTarget ? "bg-primary/10" : "";

  if (isRoot) {
    return (
      <div ref={dropRef} className={`transition-colors ${dropHighlight}`}>
        <div
          className="flex items-center w-full"
          style={rowStyle}
          title={defaultsSummary || undefined}
        >
          <span className="w-6 shrink-0" aria-hidden />
          <div className="flex-1 flex items-center py-1.5 pr-3">
            <span className="h-4 w-4 shrink-0" aria-hidden />
            <Folder className="h-4 w-4 shrink-0 ml-2 text-muted-foreground" />
            <span className="font-medium truncate ml-2">{node.group.name}</span>
            {stats}
          </div>
        </div>
        {childRows}
      </div>
    );
  }

  return (
    <div ref={dropRef} className={`transition-colors ${dropHighlight}`}>
      <Collapsible open={isOpen} onOpenChange={(next) => onToggle(node.group.id, next)}>
        {/* Grip (drag handle) and the toggle are siblings, not nested, so the
            toggle is a real focusable <button> — keyboard users can expand /
            collapse it, and there's no interactive-inside-interactive nesting. */}
        <div
          ref={setRowRef}
          className="flex items-center w-full hover:bg-muted/50 transition-colors"
          style={rowStyle}
          title={defaultsSummary || undefined}
          onMouseEnter={() => requestJobsFor(node.group.id)}
        >
          <button
            ref={handleRef}
            type="button"
            aria-label={`Drag group ${node.group.name}`}
            className="w-6 shrink-0 flex items-center justify-center py-1.5 cursor-grab text-muted-foreground hover:text-foreground"
          >
            <GripVertical className="h-4 w-4" />
          </button>
          <CollapsibleTrigger asChild>
            {/* `group` lives here (not the row) because Radix sets data-state on
                the trigger, and the chevron rotates via group-data-[state=open]. */}
            <button
              type="button"
              className="group flex-1 flex items-center py-1.5 pr-3 text-left"
              onFocus={() => requestJobsFor(node.group.id)}
            >
              <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-data-[state=open]:rotate-90" />
              <Folder className="h-4 w-4 shrink-0 ml-2 text-muted-foreground" />
              <span className="font-medium truncate ml-2">{node.group.name}</span>
              {stats}
            </button>
          </CollapsibleTrigger>
        </div>
        <CollapsibleContent>{childRows}</CollapsibleContent>
      </Collapsible>
    </div>
  );
}

// Memoized so only the node whose drop-target state changes re-renders mid-drag.
export const GroupNode = memo(GroupNodeBase);
