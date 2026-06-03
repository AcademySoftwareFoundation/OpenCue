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
import { Server } from "lucide-react";
import { Host, getHosts } from "@/app/utils/get_utils";
import { hostColumns } from "@/app/hosts/columns";
import { SimpleDataTable } from "@/components/ui/simple-data-table";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";

const REFRESH_MS = 30000;

export default function HostsPage() {
  const [hosts, setHosts] = React.useState<Host[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const load = React.useCallback(async () => {
    try {
      const data = await getHosts();
      setHosts(data);
      setError(null);
    } catch (err) {
      // getHosts already toasts via handleError; keep any previously loaded
      // rows on a failed poll and surface an inline message only when we have
      // nothing to show.
      setError(err instanceof Error ? err.message : String(err));
      setHosts((prev) => prev ?? []);
    }
  }, []);

  React.useEffect(() => {
    load();
    const interval = setInterval(load, REFRESH_MS);
    return () => clearInterval(interval);
  }, [load]);

  return (
    <div className="p-4">
      <h1 className="mb-4 text-lg font-semibold">Monitor Hosts</h1>

      {hosts === null ? (
        <div className="space-y-2">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
        </div>
      ) : (
        <>
          {error && hosts.length === 0 ? (
            <div className="mb-3 flex items-center gap-3 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm">
              <span>Could not load hosts from Cuebot.</span>
              <Button size="sm" variant="outline" onClick={() => load()}>
                Retry
              </Button>
            </div>
          ) : null}
          <SimpleDataTable
            columns={hostColumns}
            data={hosts}
            username=""
            disableContextMenu
            filterPlaceholder="Filter hosts..."
            emptyState={
              <EmptyState
                icon={<Server className="h-6 w-6" aria-hidden="true" />}
                title="No hosts registered"
                description="No hosts have reported to Cuebot yet."
              />
            }
            columnVisibilityStorageKey="cueweb.hosts.columnVisibility"
          />
        </>
      )}
    </div>
  );
}
