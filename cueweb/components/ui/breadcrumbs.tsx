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

import Link from "next/link";
import * as React from "react";
import { ChevronRight, Home } from "lucide-react";

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

export interface BreadcrumbItem {
  /** Visible label, e.g. "show-shot-user_jobName" or "Comments". */
  label: string;
  /**
   * Optional href. When omitted, the segment renders as plain text
   * (typical for the last segment / current page).
   */
  href?: string;
  /** Optional override for the tooltip / `title` value. Defaults to label. */
  title?: string;
}

export interface BreadcrumbsProps {
  items: BreadcrumbItem[];
  /** Whether to prepend a Home (/) icon segment. Defaults to true. */
  showHome?: boolean;
  className?: string;
}

/**
 * Detail-view breadcrumb. Renders separators between segments, links the
 * non-last items via `next/link`, marks the last segment with
 * `aria-current="page"`, and truncates any over-long segment to ~40
 * characters with a tooltip showing the full text on hover.
 */
export function Breadcrumbs({
  items,
  showHome = true,
  className,
}: BreadcrumbsProps) {
  const fullItems: Array<BreadcrumbItem & { _isHome?: boolean }> = showHome
    ? [{ label: "Home", href: "/", title: "Home", _isHome: true }, ...items]
    : items;

  return (
    <TooltipProvider delayDuration={200}>
      <nav
        aria-label="Breadcrumb"
        className={cn(
          "flex w-full items-center gap-1 text-sm text-muted-foreground",
          className,
        )}
      >
        <ol className="flex min-w-0 items-center gap-1">
          {fullItems.map((item, index) => {
            const isLast = index === fullItems.length - 1;
            const isHome = item._isHome === true;
            const title = item.title ?? item.label;

            // Label content: icon for home, otherwise truncated text wrapped
            // in a tooltip so the full label is recoverable on hover.
            const visible = isHome ? (
              <>
                <Home className="h-3.5 w-3.5" aria-hidden="true" />
                <span className="sr-only">{title}</span>
              </>
            ) : (
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="block max-w-[40ch] truncate align-middle">
                    {item.label}
                  </span>
                </TooltipTrigger>
                <TooltipContent>{title}</TooltipContent>
              </Tooltip>
            );

            // Last item: plain text, marked aria-current.
            const segment =
              isLast || !item.href ? (
                <span
                  aria-current={isLast ? "page" : undefined}
                  className={cn(
                    "inline-flex items-center gap-1 font-medium",
                    isLast && "text-foreground",
                  )}
                >
                  {visible}
                </span>
              ) : (
                <Link
                  href={item.href}
                  className="inline-flex items-center gap-1 rounded text-foreground/70 transition-colors hover:text-foreground hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {visible}
                </Link>
              );

            return (
              <li
                key={`${index}-${item.label}`}
                className="flex min-w-0 items-center gap-1"
              >
                {index > 0 && (
                  <ChevronRight
                    className="h-3.5 w-3.5 shrink-0 text-muted-foreground/60"
                    aria-hidden="true"
                  />
                )}
                {segment}
              </li>
            );
          })}
        </ol>
      </nav>
    </TooltipProvider>
  );
}
