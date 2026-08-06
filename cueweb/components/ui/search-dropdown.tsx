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

import { Job } from "@/app/jobs/columns";
import { cn } from "@/lib/utils";
import React, { CSSProperties, useEffect } from "react";
import { FixedSizeList } from "react-window";

type SearchDropdownProps = {
  jobs: Job[];
  hidden: boolean;
  maxListWidth: number;
  tableData: Job[];
  setMaxListWidth(width: number): void;
  handleJobSearchSelect(job: Job): void;
};

// SearchDropdown component to display a list of jobs in a virtualized dropdown.
// Uses Tailwind semantic tokens (bg-popover / text-popover-foreground /
// border-border) so the dropdown follows the active light or dark theme
// without needing to plug into MUI's theming.
export default function SearchDropdown({
  jobs,
  hidden,
  tableData,
  maxListWidth,
  setMaxListWidth,
  handleJobSearchSelect,
}: SearchDropdownProps) {
  const itemHeight = 40;
  const maxListHeight = 400;
  const listHeight = Math.min(itemHeight * jobs.length + 5, maxListHeight);
  const listRef = React.useRef<FixedSizeList | null>(null);

  // The outer container only needs positioning + z-index here; colors,
  // border, and shadow are handled by the className on the FixedSizeList
  // wrapper element below.
  const listStyle: CSSProperties = {
    position: "absolute",
    top: "100%",
    left: 0,
    right: 0,
    zIndex: 1000,
  };

  // Calculates the max width for a job and sets the list's width to that size.
  useEffect(() => {
    if (jobs.length > 0) {
      const tempDiv = document.createElement("div");
      tempDiv.style.position = "absolute";
      tempDiv.style.visibility = "hidden";
      tempDiv.style.whiteSpace = "nowrap";
      document.body.appendChild(tempDiv);

      let maxWidth = 0;
      jobs.forEach((job) => {
        tempDiv.innerText = job.name;
        maxWidth = Math.max(maxWidth, tempDiv.clientWidth);
      });
      document.body.removeChild(tempDiv);

      setMaxListWidth(maxWidth + 100);
    }
  }, [jobs]);

  // Auto-scroll to the top when jobs change (when filtering).
  useEffect(() => {
    if (listRef && listRef.current) {
      listRef.current.scrollTo(0);
    }
  }, [jobs]);

  if (hidden) return null;

  return (
    <div className="relative w-auto">
      <FixedSizeList
        height={listHeight}
        itemCount={jobs.length}
        itemSize={itemHeight}
        width={maxListWidth}
        ref={listRef}
        style={listStyle}
        // The wrapper div react-window renders gets these classes — they
        // give the dropdown its themed background/border/shadow and make
        // the scrollbar sit inside a rounded card.
        className="overflow-auto rounded-md border border-border bg-popover text-popover-foreground shadow-lg"
      >
        {({ index, style }: { index: number; style: React.CSSProperties }) => {
          const job = jobs[index];
          const isJobAdded = tableData.some(
            (existingJob: Job) => existingJob.name === job.name,
          );

          return (
            <div
              key={index}
              role="button"
              tabIndex={0}
              style={style}
              onClick={() => handleJobSearchSelect(job)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  handleJobSearchSelect(job);
                }
              }}
              className={cn(
                "flex cursor-pointer items-center border-b border-border px-3 text-sm transition-colors last:border-b-0",
                isJobAdded
                  ? // Already-monitored jobs: subtle green tint that reads on
                    // both themes.
                    "bg-green-500/20 hover:bg-green-500/40 dark:bg-green-500/15 dark:hover:bg-green-500/30"
                  : "hover:bg-accent hover:text-accent-foreground",
              )}
            >
              <span className="truncate">{job.name}</span>
            </div>
          );
        }}
      </FixedSizeList>
    </div>
  );
}
