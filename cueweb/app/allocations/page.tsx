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
import { Allocation, getAllocations, getHosts } from "@/app/utils/get_utils";
import { allocationColumns } from "@/app/allocations/allocation-columns";
import {
  AllocationRow,
  buildAllocationRows,
  computeAllocationHostStats,
} from "@/app/allocations/allocation-utils";
import { SimpleDataTable } from "@/components/ui/simple-data-table";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

const REFRESH_MS = 30000;

export default function AllocationsPage() {
  const [rows, setRows] = React.useState<AllocationRow[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const load = React.useCallback(async (isCancelled?: () => boolean) => {
    try {
      // Allocations carry most columns in their stats. The Down/Repair host
      // columns are derived from the host list (one extra fetch, best-effort -
      // if it fails those columns just read 0 rather than failing the page).
      const allocations: Allocation[] = await getAllocations();
      let hosts = [] as Awaited<ReturnType<typeof getHosts>>;
      try {
        hosts = await getHosts();
      } catch {
        // Leave hosts empty; derived columns fall back to 0.
      }
      if (isCancelled?.()) return;
      setRows(buildAllocationRows(allocations, computeAllocationHostStats(hosts)));
      setError(null);
    } catch (err) {
      if (isCancelled?.()) return;
      // getAllocations already toasts via handleError; keep prior rows.
      setError(err instanceof Error ? err.message : String(err));
      setRows((prev) => prev ?? []);
    }
  }, []);

  React.useEffect(() => {
    let cancelled = false;
    const isCancelled = () => cancelled;
    load(isCancelled);
    const interval = setInterval(() => load(isCancelled), REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [load]);

  return (
    <div className="p-4">
      <h1 className="mb-4 text-lg font-semibold">Allocations</h1>

      {rows === null ? (
        <div className="space-y-2">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
        </div>
      ) : (
        <>
          {error && rows.length === 0 ? (
            <div className="mb-3 flex items-center gap-3 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm">
              <span>Could not load allocations from Cuebot.</span>
              <Button size="sm" variant="outline" onClick={() => load()}>
                Retry
              </Button>
            </div>
          ) : null}
          <SimpleDataTable
            columns={allocationColumns}
            data={rows}
            username=""
            isAllocationsTable
            columnVisibilityStorageKey="cueweb.allocations.columnVisibility"
          />
        </>
      )}
    </div>
  );
}
