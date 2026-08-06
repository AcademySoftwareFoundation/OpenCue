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
import { Limit, getLimits } from "@/app/utils/get_utils";
import { limitColumns } from "@/app/limits/limit-columns";
import { handleError } from "@/app/utils/notify_utils";
import { SimpleDataTable } from "@/components/ui/simple-data-table";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { LimitAddDialog } from "@/components/ui/limit-add-dialog";
import { LimitEditMaxValueDialog } from "@/components/ui/limit-edit-max-value-dialog";
import { LimitRenameDialog } from "@/components/ui/limit-rename-dialog";
import { LimitDeleteDialog } from "@/components/ui/limit-delete-dialog";
import { LIMITS_CHANGED_EVENT } from "@/components/ui/limit-action-events";

const REFRESH_MS = 30000;

export default function LimitsPage() {
  const [limits, setLimits] = React.useState<Limit[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [addOpen, setAddOpen] = React.useState(false);

  const load = React.useCallback(async (isCancelled?: () => boolean) => {
    try {
      const data = await getLimits();
      if (isCancelled?.()) return;
      setLimits(data);
      setError(null);
    } catch (err) {
      if (isCancelled?.()) return;
      handleError(err, "Could not load limits");
      setError(err instanceof Error ? err.message : String(err));
      setLimits((prev) => prev ?? []);
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

  // Re-fetch after a limit is created / renamed / deleted / max value set.
  React.useEffect(() => {
    const handler = () => load();
    window.addEventListener(LIMITS_CHANGED_EVENT, handler);
    return () => window.removeEventListener(LIMITS_CHANGED_EVENT, handler);
  }, [load]);

  return (
    <div className="p-4">
      <div className="mb-4 flex items-center justify-between gap-2">
        <h1 className="text-lg font-semibold">Limits</h1>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={() => load()}>
            Refresh
          </Button>
          <Button size="sm" onClick={() => setAddOpen(true)}>
            Add Limit
          </Button>
        </div>
      </div>

      {limits === null ? (
        <div className="space-y-2">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
        </div>
      ) : (
        <>
          {error && limits.length === 0 ? (
            <div className="mb-3 flex items-center gap-3 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm">
              <span>Could not load limits from Cuebot.</span>
              <Button size="sm" variant="outline" onClick={() => load()}>
                Retry
              </Button>
            </div>
          ) : null}
          <SimpleDataTable
            columns={limitColumns}
            data={limits}
            username=""
            isLimitsTable
            columnVisibilityStorageKey="cueweb.limits.columnVisibility"
          />
        </>
      )}

      {/* Add Limit (header button) + the row context-menu dialogs (Edit Max
          Value / Rename / Delete), opened via CustomEvents. */}
      <LimitAddDialog open={addOpen} onOpenChange={setAddOpen} />
      <LimitEditMaxValueDialog />
      <LimitRenameDialog />
      <LimitDeleteDialog />
    </div>
  );
}
