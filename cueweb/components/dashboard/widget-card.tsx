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

import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { ArrowRight } from "lucide-react";
import Link from "next/link";
import * as React from "react";

/**
 * Shared shell for dashboard widget cards.
 *
 * Each card owns its own data fetch and loading state; this component is the
 * presentational shell so widgets stay consistent (title, headline number,
 * sub-label, footer click-through). The whole card is wrapped in a Link so
 * keyboard / screen-reader users get a single semantic target per widget.
 *
 * Cards on the dashboard load independently - if one widget's API call fails
 * the others still render, which is why the error string is rendered inside
 * the card (and not propagated upward).
 */
export interface WidgetCardProps {
  title: string;
  /** Lucide icon (or any React node) shown in the top-right corner. */
  icon?: React.ReactNode;
  /** Primary metric, e.g. "127" or "8 / 32". */
  value: React.ReactNode;
  /** Optional supplemental text under the value, e.g. "running now". */
  subLabel?: React.ReactNode;
  /** Footer slot, typically a short summary or list of recent items. */
  footer?: React.ReactNode;
  /** Click-through destination - the whole card is keyboard-focusable. */
  href: string;
  /** Anchor text rendered at the bottom of the card. */
  ctaLabel: string;
  className?: string;
}

export function WidgetCard({
  title,
  icon,
  value,
  subLabel,
  footer,
  href,
  ctaLabel,
  className,
}: WidgetCardProps) {
  return (
    <Link
      href={href}
      className={cn(
        "group flex h-full flex-col rounded-xl border border-border bg-card p-4 shadow-sm",
        "transition-colors hover:border-foreground/30 hover:bg-accent/40",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {title}
        </span>
        {icon ? (
          <span className="text-muted-foreground group-hover:text-foreground" aria-hidden="true">
            {icon}
          </span>
        ) : null}
      </div>

      <div className="mt-3 text-3xl font-semibold leading-tight tabular-nums">{value}</div>
      {subLabel ? <div className="mt-1 text-xs text-muted-foreground">{subLabel}</div> : null}

      {footer ? <div className="mt-3 text-xs text-muted-foreground">{footer}</div> : null}

      <div className="mt-auto inline-flex items-center gap-1 pt-4 text-xs font-medium text-foreground/80 group-hover:text-foreground">
        <span>{ctaLabel}</span>
        <ArrowRight
          className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5"
          aria-hidden="true"
        />
      </div>
    </Link>
  );
}

/**
 * Skeleton variant used while a widget's first fetch is in flight.
 * Matches the card layout above so there is no layout shift when content
 * arrives. Subsequent background refreshes do not show the skeleton.
 */
export function WidgetCardSkeleton({ title }: { title: string }) {
  return (
    <div
      className="flex h-full flex-col rounded-xl border border-border bg-card p-4 shadow-sm"
      aria-busy="true"
      aria-live="polite"
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {title}
        </span>
        <Skeleton className="h-4 w-4 rounded-sm" />
      </div>
      <Skeleton className="mt-3 h-9 w-24" />
      <Skeleton className="mt-2 h-3 w-32" />
      <Skeleton className="mt-3 h-3 w-full" />
      <Skeleton className="mt-1 h-3 w-3/4" />
      <div className="mt-auto pt-4">
        <Skeleton className="h-3 w-20" />
      </div>
    </div>
  );
}

/**
 * Error variant - keeps the click-through to the related page so users can
 * still investigate even when the dashboard's own fetch failed.
 */
export function WidgetCardError({
  title,
  href,
  message,
}: {
  title: string;
  href: string;
  message: string;
}) {
  return (
    <Link
      href={href}
      className="flex h-full flex-col rounded-xl border border-destructive/40 bg-destructive/5 p-4 shadow-sm"
    >
      <span className="text-xs font-semibold uppercase tracking-wide text-destructive">{title}</span>
      <p className="mt-3 text-sm text-destructive">{message}</p>
      <div className="mt-auto inline-flex items-center gap-1 pt-4 text-xs font-medium text-destructive">
        <span>Open page</span>
        <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
      </div>
    </Link>
  );
}
