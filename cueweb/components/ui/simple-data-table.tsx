"use client";

import { Frame } from "@/app/frames/frame-columns";
import { Layer } from "@/app/layers/layer-columns";
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
import * as React from "react";
import { Job } from "../../app/jobs/columns";
import { getFrameLogDir } from "../../app/utils/get_utils";
import { Status } from "./status";

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
  
  // Ref for the table container, required for the context menu
  const tableRef = React.useRef<HTMLDivElement>(null);
  
  const {
    contextMenuState,
    contextMenuHandleOpen,
    contextMenuHandleClose,
    contextMenuRef,
    contextMenuTargetAreaRef,
  } = useContextMenu(tableRef);

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    onSortingChange: setSorting,
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    state: { sorting },
    autoResetPageIndex: false,
  });

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
