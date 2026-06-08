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

import { cn } from "@/lib/utils";

/**
 * Minimal shadcn-style skeleton primitive. Renders a pulsing block sized
 * by the caller via className (height, width, rounded). Use to reserve
 * space for content while it loads - matching the final layout prevents
 * cumulative layout shift when real content arrives.
 *
 * Example:
 *   <Skeleton className="h-6 w-3/5" />
 */
export function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      aria-hidden="true"
      className={cn("animate-pulse rounded-md bg-muted/60", className)}
      {...props}
    />
  );
}
