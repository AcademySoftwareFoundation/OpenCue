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
import { HostLockDialog } from "@/components/ui/host-lock-dialog";
import { HostRebootDialog } from "@/components/ui/host-reboot-dialog";
import { EditHostTagsDialog } from "@/components/ui/edit-host-tags-dialog";
import {
  HOSTS_CHANGED_EVENT,
  type HostsChangedDetail,
} from "@/components/ui/host-action-events";

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

  // After a lock/unlock/reboot the dialogs fire cueweb:hosts-changed.
  // Optimistically apply the patch (lockState and/or state) to the affected
  // rows so the table reflects the change immediately, then kick off a fetch
  // to reconcile with Cuebot (the gateway may take a beat to settle, and a
  // request it rejects will be corrected on the next poll).
  React.useEffect(() => {
    function handler(e: Event) {
      const detail = (e as CustomEvent<HostsChangedDetail>).detail;
      if (!detail?.hostIds?.length || !detail.patch) return;
      const ids = new Set(detail.hostIds);
      setHosts((prev) =>
        prev
          ? prev.map((h) => (ids.has(h.id) ? { ...h, ...detail.patch } : h))
          : prev,
      );
      load();
    }
    window.addEventListener(HOSTS_CHANGED_EVENT, handler);
    return () => window.removeEventListener(HOSTS_CHANGED_EVENT, handler);
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
            viewsPageKey="hosts"
          />
        </>
      )}

      {/* Dialogs opened by the host row context menu: Lock / Unlock
          (cueweb:open-host-lock), immediate Reboot (cueweb:open-host-reboot),
          and Edit Tags (cueweb:open-host-tags). */}
      <HostLockDialog />
      <HostRebootDialog />
      <EditHostTagsDialog />
    </div>
  );
}
