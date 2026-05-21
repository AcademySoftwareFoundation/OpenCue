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

import Link from "next/link";
import { Briefcase } from "lucide-react";
import type { Job } from "@/app/jobs/columns";

const INDENT_PER_LEVEL_REM = 1.25;
const BASE_PADDING_REM = 0.5;
const ICON_GUTTER_REM = 1.5; // align with the chevron+folder gutter of group rows

export function JobLeaf({ job, depth }: { job: Job; depth: number }) {
  const paddingLeft = `${BASE_PADDING_REM + depth * INDENT_PER_LEVEL_REM + ICON_GUTTER_REM}rem`;

  return (
    <Link
      href={`/jobs/${encodeURIComponent(job.name)}`}
      className="flex items-center gap-2 py-1.5 pr-3 hover:bg-muted/50 transition-colors"
      style={{ paddingLeft }}
    >
      <Briefcase className="h-4 w-4 shrink-0 text-muted-foreground" />
      <span className="truncate">{job.name}</span>
      {job.state && (
        <span className="ml-auto text-xs text-muted-foreground shrink-0">{job.state}</span>
      )}
    </Link>
  );
}
