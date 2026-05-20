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
import { FrameContextMenu, LayerContextMenu } from "@/components/ui/context_menus/action-context-menu";
import { useContextMenu } from "@/components/ui/context_menus/useContextMenu";
import { DataTablePagination } from "@/components/ui/pagination";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  SortingState,
  useReactTable
} from "@tanstack/react-table";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import { Job } from "../../app/jobs/columns";
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
}

export function SimpleDataTable<TData, TValue>({
  columns,
  data,
  showPagination = true,
  job,
  isFramesTable = false,
  isFramesLogTable = false,
  username,
}: SimpleDataTableProps<TData, TValue>) {
  const [sorting, setSorting] = React.useState<SortingState>([]);
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

  const table = useReactTable({
    data: tableData,
    columns,
    getCoreRowModel: getCoreRowModel(),
    onSortingChange: setSorting,
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    state: { sorting },
    autoResetPageIndex: false,
  });

  React.useEffect(() => {
    if (!isFramesTable) {
      return;
    }
    table.setPageIndex(0);
  }, [isFramesTable, selectedFrameStates, table]);

  const leftAlignedColumns = React.useMemo(() => ["dispatchOrder", "name", "services", "lastResource"], []);

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
    } else {
      return leftAlignedColumns.includes(cell.column.id) ? (
        flexRender(cell.column.columnDef.cell, cell.getContext())
      ) : (
        <div className="text-center">{flexRender(cell.column.columnDef.cell, cell.getContext())}</div>
      );
    }
  };

  return (
    <>
      {isFramesTable && (
        <div className="mb-3 flex flex-wrap gap-2">
          {FRAME_STATE_FILTERS.map((state) => {
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
          })}
        </div>
      )}
      <div className="rounded-md border" ref={tableRef}>
        <Table className="border">
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id} className="px-0">
                    {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() ? "selected" : undefined}
                  onContextMenu={(e) => contextMenuHandleOpen(e, row)}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id} className="p-2">
                      {renderTableCellContent(cell, row)}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center">
                  No results.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {showPagination && (
        <div className="space-x-2 py-4">
          <DataTablePagination table={table} pageSizes={[10, 20, 30, 40, 50]} />
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
