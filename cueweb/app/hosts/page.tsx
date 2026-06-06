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
import { Host, getHosts } from "@/app/utils/get_utils";
import { hostColumns } from "@/app/hosts/columns";
import { SimpleDataTable } from "@/components/ui/simple-data-table";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

const REFRESH_MS = 30000;

export default function HostsPage() {
  const [hosts, setHosts] = React.useState<Host[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  // isCancelled lets the polling effect drop a late response after unmount;
  // the Retry button omits it.
  const load = React.useCallback(async (isCancelled?: () => boolean) => {
    try {
      const data = await getHosts();
      if (isCancelled?.()) return;
      setHosts(data);
      setError(null);
    } catch (err) {
      if (isCancelled?.()) return;
      // Keep previously loaded rows on a failed poll; only blank to [] if we
      // never loaded anything. getHosts already toasts via handleError.
      setError(err instanceof Error ? err.message : String(err));
      setHosts((prev) => prev ?? []);
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
            isHostsTable
            columnVisibilityStorageKey="cueweb.hosts.columnVisibility"
          />
        </>
      )}
    </div>
  );
}
