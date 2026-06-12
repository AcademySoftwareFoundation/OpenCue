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

import { showColumns } from "@/app/shows/show-columns";
import { Show, getActiveShows } from "@/app/utils/get_utils";
import { handleError } from "@/app/utils/notify_utils";
import { Button } from "@/components/ui/button";
import { CreateShowDialog } from "@/components/ui/create-show-dialog";
import { CreateSubscriptionDialog } from "@/components/ui/create-subscription-dialog";
import { SHOWS_CHANGED_EVENT } from "@/components/ui/show-action-events";
import { ShowPropertiesDialog } from "@/components/ui/show-properties-dialog";
import { SimpleDataTable } from "@/components/ui/simple-data-table";
import { Skeleton } from "@/components/ui/skeleton";
import * as React from "react";

const REFRESH_MS = 30000;

export default function ShowsClient() {
  const [shows, setShows] = React.useState<Show[] | null>(null);
  const [dialogOpen, setDialogOpen] = React.useState(false);

  const load = React.useCallback(async (isCancelled?: () => boolean) => {
    try {
      const data = await getActiveShows();
      if (isCancelled?.()) return;
      setShows(data);
    } catch (err) {
      if (isCancelled?.()) return;
      handleError(err, "Could not load shows");
      setShows((prev) => prev ?? []);
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

  // Re-fetch when a show changes (properties saved, subscription created, or a
  // new show with subscriptions is created).
  React.useEffect(() => {
    const handler = () => load();
    window.addEventListener(SHOWS_CHANGED_EVENT, handler);
    return () => window.removeEventListener(SHOWS_CHANGED_EVENT, handler);
  }, [load]);

  return (
    <>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Shows</h1>
        <Button onClick={() => setDialogOpen(true)}>Create Show</Button>
      </div>

      {shows === null ? (
        <div className="space-y-2">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
        </div>
      ) : (
        <SimpleDataTable
          columns={showColumns}
          data={shows}
          username=""
          isShowsTable
          columnVisibilityStorageKey="cueweb.shows.columnVisibility"
        />
      )}

      {/* Create Show (with optional per-allocation subscriptions). On success
          the table refreshes - matching CueGUI, which keeps the Shows window
          open and shows the new row. */}
      <CreateShowDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onSuccess={() => load()}
      />
      {/* Opened from the row context menu via CustomEvents. */}
      <ShowPropertiesDialog />
      <CreateSubscriptionDialog />
    </>
  );
}
