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

import * as React from "react";
import Link from "next/link";
import {
  Briefcase,
  Columns,
  Download,
  FileSpreadsheet,
  FileText,
  Filter,
  FilterX,
  Grid3X3,
  Keyboard,
  Layers as LayersIcon,
  List,
  ListChecks,
  MoreHorizontal,
  Pause,
  Play,
  RefreshCw,
  RotateCcw,
  Settings,
  Square,
  Timer,
} from "lucide-react";

import { Job } from "@/app/jobs/columns";
import { useMediaQuery } from "@/app/utils/use_media_query";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

/**
 * Shared toolbar for the Jobs / Frames / Layers monitor views.
 *
 * Layout: a horizontal `role="toolbar"` with named groups separated by
 * vertical dividers. Each group carries an `aria-label` so screen readers
 * announce "Monitor group, Refresh group, ..." rather than a flat row of
 * buttons.
 *
 * Groups (left to right):
 *   - View    - grid/list, density, column chooser
 *   - Monitor - quick navigation between Jobs / Layers / Frames views
 *   - Actions - pause / resume / kill / retry on the current selection
 *   - Filter  - quick filters + clear
 *   - Refresh - manual refresh + auto-refresh toggle
 *   - Export  - CSV / JSON / PDF
 *
 * Responsive behavior: below the `lg` breakpoint (1024px) the Filter and
 * Export groups collapse into a "More" overflow dropdown so the primary
 * Monitor / Action / Refresh affordances stay reachable on narrow screens.
 * The overflow is built on `dropdown-menu.tsx`, so keyboard navigation
 * (Arrow keys, Enter, Esc) comes for free.
 */
type ViewMode = "grid" | "list";
type Density = "compact" | "normal" | "comfortable";
type ExportFormat = "csv" | "json" | "pdf";
type JobAction = "pause" | "resume" | "kill" | "retry";

interface ToolbarProps {
  className?: string;
  onViewToggle?: (view: ViewMode) => void;
  onDensityChange?: (density: Density) => void;
  onColumnChooser?: () => void;
  onJobAction?: (action: JobAction) => void;
  onFilter?: (filter: string) => void;
  onClearFilters?: () => void;
  onExport?: (format: ExportFormat) => void;
  onRefresh?: () => void;
  /** Toggle for whether auto-refresh polling is active. */
  onAutoRefreshToggle?: (enabled: boolean) => void;
  selectedJobs?: Job[];
  currentView?: ViewMode;
  currentDensity?: Density;
  hasActiveFilters?: boolean;
  autoRefreshEnabled?: boolean;
  /** Surfaced in the Refresh tooltip; pass through whatever cadence the page polls. */
  refreshIntervalLabel?: string;
}

/**
 * Single icon button with a shortcut-aware tooltip. The shortcut string is
 * surfaced visually now; the keys themselves are wired up by A12 (keyboard
 * shortcuts overlay).
 */
interface ToolbarButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: "default" | "secondary" | "outline" | "ghost";
  size?: "default" | "sm" | "lg";
  tooltip: string;
  shortcut?: string;
  /** ARIA label - defaults to the tooltip text. */
  ariaLabel?: string;
  ariaPressed?: boolean;
}

const ToolbarButton = React.forwardRef<HTMLButtonElement, ToolbarButtonProps>(
  function ToolbarButton(
    {
      children,
      onClick,
      disabled,
      variant = "outline",
      size = "sm",
      tooltip,
      shortcut,
      ariaLabel,
      ariaPressed,
    },
    ref,
  ) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            ref={ref}
            variant={variant}
            size={size}
            onClick={onClick}
            disabled={disabled}
            aria-label={ariaLabel ?? tooltip}
            aria-pressed={ariaPressed}
            className="h-8 px-3"
          >
            {children}
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <div className="flex flex-col items-center">
            <span>{tooltip}</span>
            {shortcut && (
              <span className="mt-1 inline-flex items-center text-xs text-muted-foreground">
                <Keyboard className="mr-1 h-3 w-3" aria-hidden="true" />
                {shortcut}
              </span>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    );
  },
);

/**
 * Vertical hairline between groups. Uses `bg-border` so it picks up the
 * theme accent in light + dark modes.
 */
function ToolbarSeparator() {
  return (
    <div
      role="separator"
      aria-orientation="vertical"
      className="mx-2 h-6 w-px self-center bg-border"
    />
  );
}

function ToolbarGroup({
  title,
  children,
  className,
}: {
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      role="group"
      aria-label={title}
      className={cn("flex flex-col", className)}
    >
      <div className="mb-1 px-1 text-xs uppercase tracking-wide text-muted-foreground">
        {title}
      </div>
      <div className="flex items-center gap-1">{children}</div>
    </div>
  );
}

export const Toolbar: React.FC<ToolbarProps> = ({
  className,
  onViewToggle,
  onDensityChange,
  onColumnChooser,
  onJobAction,
  onFilter,
  onClearFilters,
  onExport,
  onRefresh,
  onAutoRefreshToggle,
  selectedJobs = [],
  currentView = "list",
  currentDensity = "normal",
  hasActiveFilters = false,
  autoRefreshEnabled = false,
  refreshIntervalLabel,
}) => {
  // The "narrow" cutoff matches Tailwind's `lg` breakpoint - below 1024px the
  // Filter + Export groups collapse into an overflow menu.
  const isNarrow = useMediaQuery("(max-width: 1023px)");

  const hasSelectedJobs = selectedJobs.length > 0;
  const allJobsFinished =
    selectedJobs.length > 0 &&
    selectedJobs.every((job) => job.state === "FINISHED");

  const cycleDensity = () => {
    const densities: Density[] = ["compact", "normal", "comfortable"];
    const currentIndex = densities.indexOf(currentDensity);
    const next = densities[(currentIndex + 1) % densities.length];
    onDensityChange?.(next);
  };

  return (
    <TooltipProvider delayDuration={200}>
      <div
        role="toolbar"
        aria-label="Monitor toolbar"
        className={cn(
          "sticky top-0 z-10 flex items-end gap-2 overflow-x-auto border-b border-border bg-background p-4 shadow-sm",
          className,
        )}
      >
        {/* View Controls */}
        <ToolbarGroup title="View">
          <ToolbarButton
            tooltip="Grid view"
            shortcut="Ctrl+G"
            onClick={() => onViewToggle?.("grid")}
            variant={currentView === "grid" ? "default" : "outline"}
            ariaPressed={currentView === "grid"}
          >
            <Grid3X3 className="h-4 w-4" />
          </ToolbarButton>

          <ToolbarButton
            tooltip="List view"
            shortcut="Ctrl+L"
            onClick={() => onViewToggle?.("list")}
            variant={currentView === "list" ? "default" : "outline"}
            ariaPressed={currentView === "list"}
          >
            <List className="h-4 w-4" />
          </ToolbarButton>

          <ToolbarButton
            tooltip={`Density: ${currentDensity}`}
            shortcut="Ctrl+D"
            onClick={cycleDensity}
          >
            <Settings className="h-4 w-4" />
          </ToolbarButton>

          <ToolbarButton
            tooltip="Choose columns"
            shortcut="Ctrl+K"
            onClick={onColumnChooser}
          >
            <Columns className="h-4 w-4" />
          </ToolbarButton>
        </ToolbarGroup>

        <ToolbarSeparator />

        {/* Monitor - quick switch between top-level monitor views. */}
        <ToolbarGroup title="Monitor">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="outline" size="sm" asChild className="h-8 px-3">
                <Link href="/" aria-label="Monitor Jobs">
                  <ListChecks className="h-4 w-4" />
                  <span className="ml-1 text-xs">Jobs</span>
                </Link>
              </Button>
            </TooltipTrigger>
            <TooltipContent>Monitor Jobs</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="outline" size="sm" asChild className="h-8 px-3">
                <Link href="/layers" aria-label="Monitor Layers">
                  <LayersIcon className="h-4 w-4" />
                  <span className="ml-1 text-xs">Layers</span>
                </Link>
              </Button>
            </TooltipTrigger>
            <TooltipContent>Monitor Layers</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="outline" size="sm" asChild className="h-8 px-3">
                <Link href="/frames" aria-label="Monitor Frames">
                  <Briefcase className="h-4 w-4" />
                  <span className="ml-1 text-xs">Frames</span>
                </Link>
              </Button>
            </TooltipTrigger>
            <TooltipContent>Monitor Frames</TooltipContent>
          </Tooltip>
        </ToolbarGroup>

        <ToolbarSeparator />

        {/* Job Actions */}
        <ToolbarGroup title="Actions">
          <ToolbarButton
            tooltip="Resume selected jobs"
            shortcut="Ctrl+R"
            onClick={() => onJobAction?.("resume")}
            disabled={!hasSelectedJobs || allJobsFinished}
          >
            <Play className="h-4 w-4" />
          </ToolbarButton>

          <ToolbarButton
            tooltip="Pause selected jobs"
            shortcut="Ctrl+P"
            onClick={() => onJobAction?.("pause")}
            disabled={!hasSelectedJobs || allJobsFinished}
          >
            <Pause className="h-4 w-4" />
          </ToolbarButton>

          <ToolbarButton
            tooltip="Kill selected jobs"
            shortcut="Ctrl+X"
            onClick={() => onJobAction?.("kill")}
            disabled={!hasSelectedJobs || allJobsFinished}
          >
            <Square className="h-4 w-4" />
          </ToolbarButton>

          <ToolbarButton
            tooltip="Retry selected jobs"
            shortcut="Ctrl+T"
            onClick={() => onJobAction?.("retry")}
            disabled={!hasSelectedJobs}
          >
            <RotateCcw className="h-4 w-4" />
          </ToolbarButton>
        </ToolbarGroup>

        <ToolbarSeparator />

        {/* Filter - hidden on narrow screens (surfaced via "More" instead). */}
        {!isNarrow && (
          <>
            <ToolbarGroup title="Filter">
              <ToolbarButton
                tooltip="Quick filter: Active jobs"
                shortcut="Ctrl+1"
                onClick={() => onFilter?.("active")}
              >
                <Filter className="h-4 w-4" />
                <span className="ml-1 text-xs">Active</span>
              </ToolbarButton>

              <ToolbarButton
                tooltip="Quick filter: Paused jobs"
                shortcut="Ctrl+2"
                onClick={() => onFilter?.("paused")}
              >
                <Filter className="h-4 w-4" />
                <span className="ml-1 text-xs">Paused</span>
              </ToolbarButton>

              <ToolbarButton
                tooltip="Clear all filters"
                shortcut="Ctrl+0"
                onClick={onClearFilters}
                disabled={!hasActiveFilters}
              >
                <FilterX className="h-4 w-4" />
              </ToolbarButton>
            </ToolbarGroup>

            <ToolbarSeparator />
          </>
        )}

        {/* Refresh - manual refresh + auto-refresh toggle. */}
        <ToolbarGroup title="Refresh">
          <ToolbarButton
            tooltip={
              refreshIntervalLabel
                ? `Refresh now (auto every ${refreshIntervalLabel})`
                : "Refresh now"
            }
            shortcut="F5"
            onClick={onRefresh}
          >
            <RefreshCw className="h-4 w-4" />
          </ToolbarButton>

          <ToolbarButton
            tooltip={
              autoRefreshEnabled
                ? "Auto-refresh: on"
                : "Auto-refresh: off"
            }
            shortcut="Ctrl+Shift+R"
            variant={autoRefreshEnabled ? "default" : "outline"}
            ariaPressed={autoRefreshEnabled}
            onClick={() => onAutoRefreshToggle?.(!autoRefreshEnabled)}
          >
            <Timer className="h-4 w-4" />
          </ToolbarButton>
        </ToolbarGroup>

        {/* Export - hidden on narrow screens (surfaced via "More" instead). */}
        {!isNarrow && (
          <>
            <ToolbarSeparator />

            <ToolbarGroup title="Export">
              <ToolbarButton
                tooltip="Export as CSV"
                shortcut="Ctrl+E, C"
                onClick={() => onExport?.("csv")}
              >
                <FileSpreadsheet className="h-4 w-4" />
                <span className="ml-1 text-xs">CSV</span>
              </ToolbarButton>

              <ToolbarButton
                tooltip="Export as JSON"
                shortcut="Ctrl+E, J"
                onClick={() => onExport?.("json")}
              >
                <FileText className="h-4 w-4" />
                <span className="ml-1 text-xs">JSON</span>
              </ToolbarButton>

              <ToolbarButton
                tooltip="Export as PDF"
                shortcut="Ctrl+E, P"
                onClick={() => onExport?.("pdf")}
              >
                <Download className="h-4 w-4" />
                <span className="ml-1 text-xs">PDF</span>
              </ToolbarButton>
            </ToolbarGroup>
          </>
        )}

        {/* Overflow menu for narrow viewports. */}
        {isNarrow && (
          <>
            <ToolbarSeparator />
            <div className="flex flex-col">
              <div className="mb-1 px-1 text-xs uppercase tracking-wide text-muted-foreground">
                More
              </div>
              <DropdownMenu>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-8 px-3"
                        aria-label="More toolbar actions"
                      >
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                  </TooltipTrigger>
                  <TooltipContent>More actions</TooltipContent>
                </Tooltip>
                <DropdownMenuContent align="end" className="min-w-[14rem]">
                  <DropdownMenuLabel>Filter</DropdownMenuLabel>
                  <DropdownMenuItem onSelect={() => onFilter?.("active")}>
                    <Filter className="mr-2 h-4 w-4" aria-hidden="true" />
                    Active jobs
                  </DropdownMenuItem>
                  <DropdownMenuItem onSelect={() => onFilter?.("paused")}>
                    <Filter className="mr-2 h-4 w-4" aria-hidden="true" />
                    Paused jobs
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onSelect={() => onClearFilters?.()}
                    disabled={!hasActiveFilters}
                  >
                    <FilterX className="mr-2 h-4 w-4" aria-hidden="true" />
                    Clear filters
                  </DropdownMenuItem>

                  <DropdownMenuSeparator />

                  <DropdownMenuLabel>Export</DropdownMenuLabel>
                  <DropdownMenuItem onSelect={() => onExport?.("csv")}>
                    <FileSpreadsheet className="mr-2 h-4 w-4" aria-hidden="true" />
                    Export CSV
                  </DropdownMenuItem>
                  <DropdownMenuItem onSelect={() => onExport?.("json")}>
                    <FileText className="mr-2 h-4 w-4" aria-hidden="true" />
                    Export JSON
                  </DropdownMenuItem>
                  <DropdownMenuItem onSelect={() => onExport?.("pdf")}>
                    <Download className="mr-2 h-4 w-4" aria-hidden="true" />
                    Export PDF
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </>
        )}
      </div>
    </TooltipProvider>
  );
};

export default Toolbar;
