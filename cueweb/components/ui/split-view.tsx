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

import { ArrowRightLeft, ChevronDown, Columns, ExternalLink } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import * as React from "react";

import { useMediaQuery } from "@/app/utils/use_media_query";
import {
  buildSplitUrl,
  clampRatio,
  DEFAULT_LEFT,
  DEFAULT_RATIO,
  DEFAULT_RIGHT,
  MAX_RATIO,
  MIN_RATIO,
  PaneSide,
  readRatio,
  sanitizePanePath,
  writeRatio,
} from "@/app/utils/split_view_utils";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

/**
 * Multi-pane workspace - the web-native replacement for CueGUI's Window menu
 * "Add new window" entries (`cuegui/cuegui/MainWindow.py`). Renders two CueWeb
 * pages side-by-side, each in its own same-origin `<iframe>` so it keeps its
 * own URL, route params and reload behavior (rendering the page components
 * directly would force both panes to share one Next.js router context, which
 * breaks dynamic routes and searchParam-driven pages).
 *
 * The chrome (header / sidebar / status bar) is hidden inside the iframes by
 * `AppShell`'s embedded check, so each pane shows just its page content. The
 * full workspace is driven by the URL (`/split?left=...&right=...`) and the
 * divider ratio is persisted to localStorage, so reloading restores both panes
 * and the divider position.
 */

/** Top-level pages offered in the per-pane page picker. Limited to routes that
 *  actually exist so a pane can't be pointed at a 404; deep pages (a specific
 *  job / host / frame) are reached by navigating inside the pane, which syncs
 *  back into the URL. */
const SPLIT_TARGETS: { label: string; href: string }[] = [
  { label: "Monitor Jobs", href: "/" },
  // CueCommander pages, in sidebar order.
  { label: "Allocations", href: "/allocations" },
  { label: "Limits", href: "/limits" },
  { label: "Monitor Cue", href: "/monitor-cue" },
  { label: "Monitor Hosts", href: "/hosts" },
  { label: "Redirect", href: "/redirect" },
  { label: "Services", href: "/services" },
  { label: "Shows", href: "/shows" },
  { label: "Stuck Frame", href: "/stuck-frames" },
  { label: "Subscription Graphs", href: "/subscription-graphs" },
  { label: "Subscriptions", href: "/subscriptions" },
  { label: "CueSubmit", href: "/cuesubmit" },
  { label: "All plugins", href: "/plugins" },
  { label: "CueProgress bar plugin", href: "/plugins/cue-progress-bar" },
];

/** Best-effort friendly label for a pane URL (matches the longest known
 *  top-level route prefix); falls back to the raw path. */
function labelForUrl(url: string): string {
  const pathOnly = url.split(/[?#]/)[0] || "/";
  // Exact match first, then deepest prefix match (so /hosts/x -> "Monitor Hosts").
  const exact = SPLIT_TARGETS.find((t) => t.href === pathOnly);
  if (exact) return exact.label;
  const prefix = SPLIT_TARGETS.filter(
    (t) => t.href !== "/" && pathOnly.startsWith(`${t.href}/`),
  ).sort((a, b) => b.href.length - a.href.length)[0];
  if (prefix) return prefix.label;
  if (pathOnly === "/" || pathOnly.startsWith("/jobs")) return "Monitor Jobs";
  return pathOnly;
}

interface PaneProps {
  side: PaneSide;
  url: string;
  dragging: boolean;
  onPick: (side: PaneSide, href: string) => void;
  onNavigate: (side: PaneSide, path: string) => void;
}

/**
 * A single workspace pane: a slim header (page picker + current path + open in
 * new tab) over an iframe. The iframe `src` is managed imperatively so that
 * navigation *inside* the iframe is reported back up (onNavigate) without the
 * parent immediately clobbering it on the next render.
 */
function Pane({ side, url, dragging, onPick, onNavigate }: PaneProps) {
  const iframeRef = React.useRef<HTMLIFrameElement>(null);

  // Read the iframe's current location (same-origin; guarded for the initial
  // about:blank state and any transient cross-origin redirect).
  const currentLocation = React.useCallback((): string | null => {
    const win = iframeRef.current?.contentWindow;
    if (!win) return null;
    try {
      return `${win.location.pathname}${win.location.search}`;
    } catch {
      return null;
    }
  }, []);

  // Drive the iframe only when the desired `url` differs from what it's already
  // showing - i.e. the change came from outside (picker / swap / reload), not
  // from the user navigating within the pane.
  React.useEffect(() => {
    const frame = iframeRef.current;
    if (!frame) return;
    if (currentLocation() !== url) {
      frame.src = url;
    }
  }, [url, currentLocation]);

  const handleLoad = React.useCallback(() => {
    const path = currentLocation();
    if (path) onNavigate(side, path);
  }, [currentLocation, onNavigate, side]);

  return (
    <div className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden rounded-md border border-border bg-background">
      <div className="flex h-9 shrink-0 items-center gap-2 border-b border-border bg-muted/40 px-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 max-w-[60%] px-2"
              aria-label={`Choose ${side} pane page`}
            >
              <Columns className="mr-1 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              <span className="truncate">{labelForUrl(url)}</span>
              <ChevronDown className="ml-1 h-3.5 w-3.5 shrink-0 opacity-70" aria-hidden="true" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="min-w-[12rem]">
            <DropdownMenuLabel>Open in {side} pane</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {SPLIT_TARGETS.map((t) => (
              <DropdownMenuItem key={t.href} onSelect={() => onPick(side, t.href)}>
                {t.label}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        <span
          className="min-w-0 flex-1 truncate text-xs text-muted-foreground"
          title={url}
        >
          {url}
        </span>

        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          title="Open this pane in a new tab"
          aria-label="Open this pane in a new tab"
          className="rounded p-1 text-muted-foreground hover:bg-foreground/10 hover:text-foreground"
        >
          <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
        </a>
      </div>

      <div className="relative min-h-0 flex-1">
        <iframe
          ref={iframeRef}
          onLoad={handleLoad}
          title={`${side} pane`}
          className="absolute inset-0 h-full w-full border-0"
          // While dragging the divider, mouse moves over an iframe would be
          // swallowed by its document and never reach the parent's pointer
          // handlers - disable hit-testing for the duration of the drag.
          style={{ pointerEvents: dragging ? "none" : "auto" }}
        />
      </div>
    </div>
  );
}

export function SplitView() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const isNarrow = useMediaQuery("(max-width: 767px)");

  const left = sanitizePanePath(searchParams.get("left"), DEFAULT_LEFT);
  const right = sanitizePanePath(searchParams.get("right"), DEFAULT_RIGHT);

  // Divider position (percent for the left pane). Hydrated from localStorage
  // after mount so SSR and the first client render agree.
  const [ratio, setRatio] = React.useState<number>(DEFAULT_RATIO);
  const ratioRef = React.useRef(ratio);
  ratioRef.current = ratio;
  React.useEffect(() => {
    setRatio(readRatio());
  }, []);

  const setPane = React.useCallback(
    (side: PaneSide, path: string) => {
      const sanitized = sanitizePanePath(
        path,
        side === "left" ? DEFAULT_LEFT : DEFAULT_RIGHT,
      );
      const next = new URLSearchParams(searchParams.toString());
      if (next.get(side) === sanitized) return; // no-op: avoids redundant replaces
      next.set(side, sanitized);
      router.replace(`${pathname}?${next.toString()}`, { scroll: false });
    },
    [router, pathname, searchParams],
  );

  const handleNavigate = React.useCallback(
    (side: PaneSide, path: string) => setPane(side, path),
    [setPane],
  );

  const handlePick = React.useCallback(
    (side: PaneSide, href: string) => setPane(side, href),
    [setPane],
  );

  const handleSwap = React.useCallback(() => {
    router.replace(buildSplitUrl(right, left), { scroll: false });
  }, [router, left, right]);

  const resetRatio = React.useCallback(() => {
    setRatio(DEFAULT_RATIO);
    writeRatio(DEFAULT_RATIO);
  }, []);

  // Divider drag (pointer events cover mouse + touch + pen). The actual ratio
  // math lives here; the iframes get pointer-events:none while `dragging` so
  // the move events keep reaching the window.
  const containerRef = React.useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = React.useState(false);

  React.useEffect(() => {
    if (!dragging) return;
    const onMove = (e: PointerEvent) => {
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect || rect.width === 0) return;
      const pct = ((e.clientX - rect.left) / rect.width) * 100;
      setRatio(clampRatio(pct));
    };
    const onUp = () => {
      setDragging(false);
      writeRatio(ratioRef.current);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointercancel", onUp);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onUp);
    };
  }, [dragging]);

  const onDividerKeyDown = (e: React.KeyboardEvent) => {
    let delta = 0;
    if (e.key === "ArrowLeft") delta = -2;
    else if (e.key === "ArrowRight") delta = 2;
    else if (e.key === "Home") {
      e.preventDefault();
      setRatio(MIN_RATIO);
      writeRatio(MIN_RATIO);
      return;
    } else if (e.key === "End") {
      e.preventDefault();
      setRatio(MAX_RATIO);
      writeRatio(MAX_RATIO);
      return;
    }
    if (delta !== 0) {
      e.preventDefault();
      const next = clampRatio(ratioRef.current + delta);
      setRatio(next);
      writeRatio(next);
    }
  };

  const leftPane = (
    <Pane
      side="left"
      url={left}
      dragging={dragging}
      onPick={handlePick}
      onNavigate={handleNavigate}
    />
  );
  const rightPane = (
    <Pane
      side="right"
      url={right}
      dragging={dragging}
      onPick={handlePick}
      onNavigate={handleNavigate}
    />
  );

  return (
    <div className="flex h-[calc(100vh-5rem)] min-h-[420px] w-full flex-col px-4">
      {/* Workspace toolbar */}
      <div className="flex items-center justify-between gap-2 py-2">
        <div className="text-xs font-medium text-muted-foreground">
          Split view
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="h-8"
            onClick={handleSwap}
          >
            <ArrowRightLeft className="mr-1 h-4 w-4" aria-hidden="true" />
            Swap
          </Button>
          {!isNarrow ? (
            <Button
              variant="outline"
              size="sm"
              className="h-8"
              onClick={resetRatio}
            >
              Reset 50 / 50
            </Button>
          ) : null}
        </div>
      </div>

      {isNarrow ? (
        // On phones, stack the panes vertically (no draggable divider - there
        // isn't room to resize comfortably). Each pane gets half the height.
        <div className="flex min-h-0 flex-1 flex-col gap-2 pb-2">
          <div className="min-h-0 flex-1">{leftPane}</div>
          <div className="min-h-0 flex-1">{rightPane}</div>
        </div>
      ) : (
        <div ref={containerRef} className="flex min-h-0 flex-1 pb-2">
          <div style={{ flexBasis: `${ratio}%` }} className="min-w-0">
            {leftPane}
          </div>

          <div
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize panes"
            aria-valuenow={Math.round(ratio)}
            aria-valuemin={MIN_RATIO}
            aria-valuemax={MAX_RATIO}
            tabIndex={0}
            onPointerDown={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onKeyDown={onDividerKeyDown}
            className={cn(
              "group relative mx-1 w-2 shrink-0 cursor-col-resize touch-none select-none",
              "focus:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            )}
          >
            <div
              className={cn(
                "absolute inset-y-0 left-1/2 w-0.5 -translate-x-1/2 bg-border transition-colors",
                "group-hover:bg-foreground/40",
                dragging && "bg-primary",
              )}
              aria-hidden="true"
            />
          </div>

          <div className="min-w-0 flex-1">{rightPane}</div>
        </div>
      )}
    </div>
  );
}

export default SplitView;
