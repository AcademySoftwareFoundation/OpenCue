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

import { useEffect, useState } from "react";
import { ChevronRight, Folder } from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Job } from "@/app/jobs/columns";
import { getGroupJobs } from "@/app/utils/get_utils";
import type { TreeNode } from "./build-tree";
import { JobLeaf } from "./job-leaf";

const INDENT_PER_LEVEL_REM = 1.25;
const BASE_PADDING_REM = 0.5;

type Props = {
  node: TreeNode;
  depth: number;
  expanded: Set<string>;
  onToggle: (groupId: string, open: boolean) => void;
};

export function GroupNode({ node, depth, expanded, onToggle }: Props) {
  const isRoot = depth === 0;
  const isOpen = isRoot || expanded.has(node.group.id);

  const [jobs, setJobs] = useState<Job[] | null>(null);
  const [jobsLoading, setJobsLoading] = useState(false);

  useEffect(() => {
    if (!isOpen || jobs !== null) return;
    let cancelled = false;
    setJobsLoading(true);
    getGroupJobs(node.group.id)
      .then(result => { if (!cancelled) setJobs(result); })
      .finally(() => { if (!cancelled) setJobsLoading(false); });
    return () => { cancelled = true; };
  }, [isOpen, jobs, node.group.id]);

  const pendingJobs = node.group.groupStats?.pendingJobs ?? 0;
  const runningFrames = node.group.groupStats?.runningFrames ?? 0;
  const paddingLeft = `${BASE_PADDING_REM + depth * INDENT_PER_LEVEL_REM}rem`;

  const stats = (
    <div className="ml-auto flex items-center gap-3 text-xs text-muted-foreground shrink-0">
      {runningFrames > 0 && <span>{runningFrames} running</span>}
      {pendingJobs > 0 && <span>{pendingJobs} pending</span>}
    </div>
  );

  const childRows = (
    <>
      {node.children.map(child => (
        <GroupNode
          key={child.group.id}
          node={child}
          depth={depth + 1}
          expanded={expanded}
          onToggle={onToggle}
        />
      ))}
      {jobsLoading && (
        <p
          className="text-xs text-muted-foreground py-1"
          style={{ paddingLeft: `${BASE_PADDING_REM + (depth + 1) * INDENT_PER_LEVEL_REM}rem` }}
        >
          Loading jobs…
        </p>
      )}
      {jobs?.map(job => (
        <JobLeaf key={job.id} job={job} depth={depth + 1} />
      ))}
    </>
  );

  if (isRoot) {
    // Root group is always open; render as a non-interactive header to avoid a
    // dead chevron that toggles nothing.
    return (
      <>
        <div
          className="flex items-center gap-2 w-full py-1.5 pr-3"
          style={{ paddingLeft }}
        >
          <span className="h-4 w-4 shrink-0" aria-hidden />
          <Folder className="h-4 w-4 shrink-0 text-muted-foreground" />
          <span className="font-medium truncate">{node.group.name}</span>
          {stats}
        </div>
        {childRows}
      </>
    );
  }

  return (
    <Collapsible
      open={isOpen}
      onOpenChange={(next) => onToggle(node.group.id, next)}
    >
      <CollapsibleTrigger
        className="group flex items-center gap-2 w-full py-1.5 pr-3 text-left hover:bg-muted/50 transition-colors"
        style={{ paddingLeft }}
      >
        <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-data-[state=open]:rotate-90" />
        <Folder className="h-4 w-4 shrink-0 text-muted-foreground" />
        <span className="font-medium truncate">{node.group.name}</span>
        {stats}
      </CollapsibleTrigger>
      <CollapsibleContent>
        {childRows}
      </CollapsibleContent>
    </Collapsible>
  );
}
