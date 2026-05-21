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


import { Frame } from "@/app/frames/frame-columns";
import { Layer } from "@/app/layers/layer-columns";
import { FRAME_STATE_FILTERS, filterFramesByStates, getFrameStateCounts } from "@/app/utils/frame_state_utils";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { EmptyState } from "@/components/ui/empty-state";
import { FrameContextMenu, LayerContextMenu } from "@/components/ui/context_menus/action-context-menu";
import { useContextMenu } from "@/components/ui/context_menus/useContextMenu";
import { Input } from "@/components/ui/input";
import { DataTablePagination } from "@/components/ui/pagination";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  ColumnDef,
  ColumnOrderState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  SortingState,
  useReactTable,
  VisibilityState,
} from "@tanstack/react-table";
import { ChevronDown, ChevronLeft, ChevronRight, Layers, Search, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import { Job } from "../../app/jobs/columns";
import {
  getItemFromLocalStorage,
  setItemInLocalStorage,
} from "../../app/utils/action_utils";
import { getFrameLogDir } from "../../app/utils/get_utils";
import { Status } from "./status";

const FRAME_STATE_QUERY_PARAM = "frameStates";

interface SimpleDataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  showPagination?: boolean;
  job?: Job;
  isFramesTable?: boolean;
  isFramesLogTable?: boolean;
  username: string;
  // When set, column visibility for this table persists to localStorage
  // under the given key. Use stable keys like "cueweb.layers.columnVisibility"
  // so the user's hide/show preferences survive reloads + job switches.
  // Omit to keep visibility ephemeral.
  columnVisibilityStorageKey?: string;
  // Initial visibility hide map applied before the user has changed
  // anything (e.g. {"maxRss": false}). Caller-provided defaults are
  // overridden by anything in localStorage.
  defaultColumnVisibility?: VisibilityState;
  // Optional click handler fired with the raw row payload. Used by
  // JobDetailsInline to select a layer (filter the frames panel + push
  // its attributes into the Attributes panel).
  onRowClick?: (row: TData) => void;
  // When provided, the row whose data.id matches gets data-state="selected"
  // styling so the user can see which row is currently driving the
  // downstream filter / attributes selection.
  selectedRowId?: string | null;
  // Optional left-side toolbar content rendered on the same row as the
  // Columns dropdown. Typically a section title with a row count, e.g.
  // <span>Layers [Total Count: 3]</span>.
  toolbarLeft?: React.ReactNode;
}

export function SimpleDataTable<TData, TValue>({
  columns,
  data,
  showPagination = true,
  job,
  isFramesTable = false,
  isFramesLogTable = false,
  username,
  columnVisibilityStorageKey,
  defaultColumnVisibility,
  onRowClick,
  selectedRowId,
  toolbarLeft,
}: SimpleDataTableProps<TData, TValue>) {
  const [sorting, setSorting] = React.useState<SortingState>([]);

  // Column visibility. Hydration model:
  //   - On first render, use the caller's defaultColumnVisibility (so SSR
  //     and the first client render match - no hydration mismatch).
  //   - On mount, if a storage key was provided, read the persisted map
  //     and merge it over the defaults.
  //   - Any user change writes back to the same key.
  const [columnVisibility, setColumnVisibility] = React.useState<VisibilityState>(
    () => defaultColumnVisibility ?? {},
  );
  React.useEffect(() => {
    if (!columnVisibilityStorageKey) return;
    try {
      const stored = getItemFromLocalStorage(
        columnVisibilityStorageKey,
        JSON.stringify(defaultColumnVisibility ?? {}),
      );
      if (stored && typeof stored === "object" && !Array.isArray(stored)) {
        setColumnVisibility(stored as VisibilityState);
      }
    } catch {
      // Bad value in storage; keep the defaults.
    }
    // We intentionally only hydrate once per mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const handleColumnVisibilityChange = React.useCallback(
    (updater: React.SetStateAction<VisibilityState>) => {
      setColumnVisibility((prev) => {
        const next =
          typeof updater === "function"
            ? (updater as (p: VisibilityState) => VisibilityState)(prev)
            : updater;
        if (columnVisibilityStorageKey) {
          try {
            setItemInLocalStorage(columnVisibilityStorageKey, JSON.stringify(next));
          } catch {
            // Storage full / private mode; ignore.
          }
        }
        return next;
      });
    },
    [columnVisibilityStorageKey],
  );

  // Column order. Persisted alongside visibility under a parallel key. For
  // the conventional keys (`...columnVisibility` -> `...columnOrder`) we
  // swap the suffix so existing localStorage entries documented in
  // cueweb/README.md and docs/reference/cueweb.md stay valid. For any
  // other key shape we append `.columnOrder` so visibility and order can
  // never collide on the same storage slot. When the stored value is
  // missing or empty, TanStack falls back to the natural order defined
  // by the column defs.
  const columnOrderStorageKey = !columnVisibilityStorageKey
    ? undefined
    : columnVisibilityStorageKey.endsWith("columnVisibility")
      ? columnVisibilityStorageKey.replace(/columnVisibility$/, "columnOrder")
      : `${columnVisibilityStorageKey}.columnOrder`;
  const [columnOrder, setColumnOrder] = React.useState<ColumnOrderState>([]);
  React.useEffect(() => {
    if (!columnOrderStorageKey) return;
    try {
      const raw = window.localStorage.getItem(columnOrderStorageKey);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) setColumnOrder(parsed as string[]);
      }
    } catch {
      // Bad value in storage; keep the empty (natural order) fallback.
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const handleColumnOrderChange = React.useCallback(
    (updater: React.SetStateAction<ColumnOrderState>) => {
      setColumnOrder((prev) => {
        const next =
          typeof updater === "function"
            ? (updater as (p: ColumnOrderState) => ColumnOrderState)(prev)
            : updater;
        if (columnOrderStorageKey) {
          try {
            window.localStorage.setItem(columnOrderStorageKey, JSON.stringify(next));
          } catch {
            // Quota / private mode; ignore.
          }
        }
        return next;
      });
    },
    [columnOrderStorageKey],
  );
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [selectedFrameStates, setSelectedFrameStates] = React.useState<string[]>([]);
  
  // Ref for the table container, required for the context menu
  const tableRef = React.useRef<HTMLDivElement>(null);
  
  const {
    contextMenuState,
    contextMenuHandleOpen,
    contextMenuHandleClose,
    contextMenuRef,
    contextMenuTargetAreaRef,
  } = useContextMenu(tableRef);

  React.useEffect(() => {
    if (!isFramesTable) {
      return;
    }

    const selectedStates = Array.from(
      new Set(
        (searchParams.get(FRAME_STATE_QUERY_PARAM) || "")
          .split(",")
          .map((state) => state.trim().toUpperCase())
          .filter((state) => FRAME_STATE_FILTERS.includes(state)),
      ),
    );
    setSelectedFrameStates(selectedStates);
  }, [isFramesTable, searchParams]);

  const frameStateCounts = React.useMemo(() => {
    return isFramesTable ? getFrameStateCounts(data as Frame[]) : {};
  }, [data, isFramesTable]);

  const tableData = React.useMemo(() => {
    return isFramesTable ? (filterFramesByStates(data as Frame[], selectedFrameStates) as TData[]) : data;
  }, [data, isFramesTable, selectedFrameStates]);

  const updateFrameStateFilters = (state: string) => {
    const nextSelectedStates = selectedFrameStates.includes(state)
      ? selectedFrameStates.filter((selectedState) => selectedState !== state)
      : [...selectedFrameStates, state];

    setSelectedFrameStates(nextSelectedStates);

    const nextParams = new URLSearchParams(searchParams.toString());
    if (nextSelectedStates.length > 0) {
      nextParams.set(FRAME_STATE_QUERY_PARAM, nextSelectedStates.join(","));
    } else {
      nextParams.delete(FRAME_STATE_QUERY_PARAM);
    }

    const query = nextParams.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  };

  // Client-side substring filter applied across every visible column. Lets
  // the user narrow the already-loaded rows without re-fetching from Cuebot.
  const [globalFilter, setGlobalFilter] = React.useState<string>("");

  const table = useReactTable({
    data: tableData,
    columns,
    getCoreRowModel: getCoreRowModel(),
    onSortingChange: setSorting,
    onColumnVisibilityChange: handleColumnVisibilityChange,
    onColumnOrderChange: handleColumnOrderChange,
    onGlobalFilterChange: setGlobalFilter,
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    state: { sorting, columnVisibility, columnOrder, globalFilter },
    autoResetPageIndex: false,
    // Column resizing: drag the right edge of any header to resize.
    enableColumnResizing: true,
    columnResizeMode: "onChange",
    // Default 10 rows for the inline Layers and Frames panels - matches
    // the CueGUI Monitor Job Details default and keeps the inline panel
    // compact when a job has lots of layers/frames.
    initialState: { pagination: { pageSize: 10 } },
  });

  // Move a hideable column one slot left (-1) or right (+1) in the table.
  // Non-hideable columns (e.g. row-select) stay anchored in their original
  // positions; we only shuffle hideable IDs among themselves.
  const moveColumn = React.useCallback((columnId: string, direction: -1 | 1) => {
    const allColumns = table.getAllColumns();
    const currentOrder = table.getState().columnOrder.length
      ? [...table.getState().columnOrder]
      : allColumns.map((c) => c.id);
    const hideableIds = new Set(
      allColumns.filter((c) => c.getCanHide()).map((c) => c.id),
    );
    const hideable = currentOrder.filter((id) => hideableIds.has(id));
    const idx = hideable.indexOf(columnId);
    if (idx < 0) return;
    const targetIdx = idx + direction;
    if (targetIdx < 0 || targetIdx >= hideable.length) return;
    [hideable[idx], hideable[targetIdx]] = [hideable[targetIdx], hideable[idx]];
    let cursor = 0;
    const next = currentOrder.map((id) => (hideableIds.has(id) ? hideable[cursor++] : id));
    handleColumnOrderChange(next);
  }, [table, handleColumnOrderChange]);

  // Reset both visibility AND order to the caller-provided defaults.
  const resetColumnsToDefault = React.useCallback(() => {
    handleColumnVisibilityChange(defaultColumnVisibility ?? {});
    handleColumnOrderChange([]);
  }, [defaultColumnVisibility, handleColumnVisibilityChange, handleColumnOrderChange]);

  React.useEffect(() => {
    if (!isFramesTable) {
      return;
    }
    table.setPageIndex(0);
  }, [isFramesTable, selectedFrameStates, table]);

  // Snap back to page 1 whenever the substring filter changes so the user
  // never lands on an empty page after narrowing the result set.
  React.useEffect(() => {
    table.setPageIndex(0);
  }, [globalFilter, table]);

  // Builds the frame-log URL the existing layer-name <Link> uses. Hoisted
  // so the row-level double-click handler can navigate to the same target
  // without duplicating the URL shape.
  const buildFrameLogUrl = React.useCallback(
    (frame: Frame): string => {
      const params = new URLSearchParams({
        frameId: frame.id,
        frameLogDir: getFrameLogDir(job as Job, frame),
        username,
      });
      return `/frames/${encodeURIComponent(frame.name)}?${params.toString()}`;
    },
    [job, username],
  );

  // Double-click anywhere on a frame row opens the log viewer (CueGUI
  // parity). Only wired when this is a frames table AND we know the
  // parent job (required to compute the log directory). The Layer-name
  // <Link> cell continues to work on a single click for keyboard / a11y
  // users; this just adds a faster path for mouse users on any column.
  const handleFrameRowDoubleClick = React.useCallback(
    (frame: Frame) => {
      if (!job) return;
      router.push(buildFrameLogUrl(frame));
    },
    [buildFrameLogUrl, job, router],
  );

  // Every column is centered now (jobs / layers / frames share the same
  // visual rhythm). The TableCell wrapper sets text-center; individual
  // cell renderers below add nothing extra so the alignment is consistent
  // regardless of column id.
  const renderTableCellContent = (cell: any, row: any) => {
    if (cell.column.id === "state") {
      return <Status status={(row.original as Frame).state} />;
    } else if (isFramesTable && cell.column.id === "layerName") {
      return (
        <Link
          href={{
            pathname: `frames/${(row.original as Frame).name}`,
            query: {
              frameId: (row.original as Frame).id,
              frameLogDir: getFrameLogDir(job as Job, row.original as Frame),
              username,
            },
          }}
        >
          <div className="text-blue-600 dark:text-blue-400 dark:font-bold">
            {flexRender(cell.column.columnDef.cell, cell.getContext())}
          </div>
        </Link>
      );
    }
    return flexRender(cell.column.columnDef.cell, cell.getContext());
  };

  // Shared Columns dropdown rendered right above the table on the right.
  // Listing only columns that opt-in via columnDef.enableHiding !== false
  // (the TanStack default), so action / progress / sticky columns don't
  // appear in the toggle list.
  const columnsDropdown = (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" className="h-8">
          Columns
          <ChevronDown className="ml-1 h-4 w-4" aria-hidden="true" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="max-h-[60vh] w-64 overflow-y-auto">
        {/* Pin the Reset button at the visual top of the menu and give it a
            clear bottom border + secondary background so it doesn't blend
            in with the rows below. Reset clears BOTH visibility AND order
            so the table returns fully to the column-def defaults. */}
        <div className="sticky top-0 z-10 mb-1 border-b border-border bg-popover pb-1">
          <Button
            className="w-full justify-start px-2 py-1.5"
            variant="secondary"
            size="sm"
            onClick={resetColumnsToDefault}
          >
            Reset to Default
          </Button>
        </div>
        {(() => {
          const hideable = table.getAllColumns().filter((c) => c.getCanHide());
          return hideable.map((column, idx) => (
            <DropdownMenuItem
              key={column.id}
              // Keep the menu open after every interaction so the user can
              // toggle visibility and bump the column around without having
              // to reopen the dropdown each time.
              onSelect={(e) => e.preventDefault()}
              className="flex cursor-default items-center justify-between gap-2 px-2 py-1 capitalize focus:bg-accent/40"
            >
              <label className="flex min-w-0 flex-1 cursor-pointer items-center gap-2">
                <Checkbox
                  checked={column.getIsVisible()}
                  onCheckedChange={(value) => column.toggleVisibility(!!value)}
                  aria-label={`Toggle ${column.id}`}
                />
                <span className="truncate">{column.id}</span>
              </label>
              <span className="inline-flex shrink-0 items-center gap-0.5">
                <button
                  type="button"
                  aria-label={`Move ${column.id} left`}
                  title="Move left"
                  disabled={idx === 0}
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    moveColumn(column.id, -1);
                  }}
                  className="rounded p-0.5 text-foreground/70 hover:bg-foreground/10 hover:text-foreground disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:bg-transparent"
                >
                  <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
                <button
                  type="button"
                  aria-label={`Move ${column.id} right`}
                  title="Move right"
                  disabled={idx === hideable.length - 1}
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    moveColumn(column.id, 1);
                  }}
                  className="rounded p-0.5 text-foreground/70 hover:bg-foreground/10 hover:text-foreground disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:bg-transparent"
                >
                  <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              </span>
            </DropdownMenuItem>
          ));
        })()}
      </DropdownMenuContent>
    </DropdownMenu>
  );

  return (
    <>
      {/* Toolbar row above the table: optional caller-supplied title
          on the far left, frame-state filters next to it (when this is
          a frames table), Columns dropdown on the right. The row is
          always rendered so the Columns dropdown has a stable location
          across all SimpleDataTable callsites. */}
      <div className="mb-2 flex flex-wrap items-center gap-2">
        {toolbarLeft ? <div>{toolbarLeft}</div> : null}
        {isFramesTable
          ? FRAME_STATE_FILTERS.map((state) => {
              const isSelected = selectedFrameStates.includes(state);
              return (
                <Button
                  key={state}
                  size="xs"
                  variant={isSelected ? "default" : "outline"}
                  onClick={() => updateFrameStateFilters(state)}
                >
                  {state} ({frameStateCounts[state] || 0})
                </Button>
              );
            })
          : null}
        <div className="ml-auto flex items-center gap-2">
          {/* Client-side substring filter across every visible column. Tied
              to TanStack's globalFilter state, so sorting / pagination /
              column visibility keep working over the filtered subset. */}
          <div className="relative">
            <Search
              className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <Input
              type="search"
              value={globalFilter}
              onChange={(e) => setGlobalFilter(e.target.value)}
              placeholder={isFramesTable ? "Filter frames..." : "Filter layers..."}
              aria-label={isFramesTable ? "Filter frames" : "Filter layers"}
              className="h-8 w-44 pl-7 pr-7 text-xs"
            />
            {globalFilter ? (
              <button
                type="button"
                aria-label="Clear filter"
                title="Clear filter"
                onClick={() => setGlobalFilter("")}
                className="absolute right-1 top-1/2 -translate-y-1/2 rounded p-0.5 text-muted-foreground hover:bg-foreground/10 hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            ) : null}
          </div>
          {columnsDropdown}
        </div>
      </div>
      <div className="rounded-md border" ref={tableRef}>
        <Table className="border">
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead
                    key={header.id}
                    className="group relative px-0"
                    style={{ width: header.getSize() }}
                  >
                    {header.isPlaceholder ? null : (
                      <div className="flex items-center justify-center">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                      </div>
                    )}
                    {header.column.getCanResize() && (
                      <div
                        onMouseDown={header.getResizeHandler()}
                        onTouchStart={header.getResizeHandler()}
                        onClick={(e) => e.stopPropagation()}
                        data-state={header.column.getIsResizing() ? "resizing" : undefined}
                        className="absolute right-0 top-0 z-10 h-full w-1.5 cursor-col-resize touch-none select-none bg-border opacity-0 transition-opacity hover:bg-foreground/40 group-hover:opacity-60 data-[state=resizing]:bg-primary data-[state=resizing]:opacity-100"
                        aria-hidden="true"
                      />
                    )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.length ? (
              table.getRowModel().rows.map((row) => {
                const rowData = row.original as { id?: string };
                const isSelectedById =
                  !!selectedRowId && rowData?.id === selectedRowId;
                const isFrameRowWithJob = isFramesTable && !!job;
                return (
                  <TableRow
                    key={row.id}
                    title={
                      isFrameRowWithJob ? "Double-click to open the log viewer" : undefined
                    }
                    data-state={
                      isSelectedById || row.getIsSelected() ? "selected" : undefined
                    }
                    onContextMenu={(e) => contextMenuHandleOpen(e, row)}
                    onClick={
                      onRowClick
                        ? () => onRowClick(row.original as TData)
                        : undefined
                    }
                    onDoubleClick={
                      isFrameRowWithJob
                        ? () => handleFrameRowDoubleClick(row.original as Frame)
                        : undefined
                    }
                    className={
                      onRowClick || isFrameRowWithJob ? "cursor-pointer" : undefined
                    }
                  >
                    {row.getVisibleCells().map((cell) => (
                      <TableCell
                        key={cell.id}
                        className="p-2"
                        style={{ width: cell.column.getSize() }}
                      >
                        {/* Wrap every cell's content in a centered flex
                            container so links, badges and plain text
                            sit in the middle of the cell horizontally
                            regardless of their own display type. */}
                        <div className="flex items-center justify-center">
                          {renderTableCellContent(cell, row)}
                        </div>
                      </TableCell>
                    ))}
                  </TableRow>
                );
              })
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-32 p-0">
                  <EmptyState
                    icon={<Layers className="h-6 w-6" aria-hidden="true" />}
                    title={
                      isFramesTable
                        ? "Layer has no frames"
                        : isFramesLogTable
                          ? "Frame not found"
                          : "Job has no layers"
                    }
                    description={
                      isFramesTable
                        ? "No frames matched the current filter. Clear the frame-state chips above to see every frame."
                        : isFramesLogTable
                          ? "The frame referenced by this URL is no longer available in Cuebot."
                          : "This job does not contain any layers yet."
                    }
                  />
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {showPagination && (
        <div className="space-x-2 py-4">
          <DataTablePagination
            table={table}
            pageSizes={[5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 100, 150, 200, 250, 300]}
          />
        </div>
      )}

      {/* Context menus for frames and layers */}
      {(isFramesTable || isFramesLogTable) ? (
        <FrameContextMenu
          username={username}
          contextMenuState={contextMenuState}
          contextMenuHandleClose={contextMenuHandleClose}
          contextMenuRef={contextMenuRef}
          contextMenuTargetAreaRef={contextMenuTargetAreaRef}
        />
      ) : (
        <LayerContextMenu
          username={username}
          contextMenuState={contextMenuState}
          contextMenuHandleClose={contextMenuHandleClose}
          contextMenuRef={contextMenuRef}
          contextMenuTargetAreaRef={contextMenuTargetAreaRef}
        />
      )}
    </>
  );
}
