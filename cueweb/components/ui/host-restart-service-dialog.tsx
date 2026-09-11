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

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import type { Host } from "@/app/utils/get_utils";
import { restartHostsRqdNow } from "@/app/utils/action_utils";
import {
  HOSTS_CHANGED_EVENT,
  OPEN_HOST_RESTART_SERVICE_EVENT,
  type HostsChangedDetail,
  type OpenHostRestartServiceDetail,
} from "@/components/ui/host-action-events";

/**
 * Confirmation dialog for an immediate RQD service restart, opened in
 * response to a `cueweb:open-host-restart-service` CustomEvent from the
 * host row context menu (restartHostServiceGivenRow), mirroring the
 * reboot dialog's decoupling. CueGUI confirms the same action, and while
 * running frames are recovered by the restarted service, the host still
 * drops out of the booking pool for the restart window - worth an
 * "are you sure" on a misclick.
 *
 * On confirm it calls the batch-capable restartHostsRqdNow action, then
 * fires `cueweb:hosts-changed` with the optimistic REBOOTING state Cuebot
 * writes for the restart window, so the rows update immediately and
 * reconcile on the next fetch.
 */

export function HostRestartServiceDialog() {
  const [open, setOpen] = React.useState(false);
  const [hosts, setHosts] = React.useState<Host[]>([]);
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      const detail = (e as CustomEvent<OpenHostRestartServiceDetail>).detail;
      if (!detail?.hosts?.length) return;
      setHosts(detail.hosts);
      setOpen(true);
    }
    window.addEventListener(OPEN_HOST_RESTART_SERVICE_EVENT, handler);
    return () => window.removeEventListener(OPEN_HOST_RESTART_SERVICE_EVENT, handler);
  }, []);

  async function handleConfirm() {
    if (!hosts.length) return;
    setSubmitting(true);
    try {
      const ok = await restartHostsRqdNow(hosts);
      // Only fire the optimistic update when the restart request succeeded.
      if (ok) {
        window.dispatchEvent(
          new CustomEvent<HostsChangedDetail>(HOSTS_CHANGED_EVENT, {
            detail: {
              hostIds: hosts.map((h) => h.id),
              patch: { state: "REBOOTING" },
            },
          }),
        );
      }
      setOpen(false);
    } catch (error) {
      // restartHostsRqdNow routes failures through performAction (toast +
      // false), so this catch only guards against an unexpected throw.
      console.error("Failed to restart RQD service on host(s):", error);
    } finally {
      setSubmitting(false);
    }
  }

  const count = hosts.length;

  return (
    <Dialog open={open} onOpenChange={submitting ? () => {} : setOpen}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>
            Restart the RQD service on {count} host{count === 1 ? "" : "s"}?
          </DialogTitle>
          <DialogDescription>
            The machine{count === 1 ? " is" : "s are"} not rebooted and running
            frames are not killed - the restarted service recovers them. The
            host{count === 1 ? "" : "s"} will not book new frames during the
            short restart window.
          </DialogDescription>
        </DialogHeader>

        <div className="max-h-48 overflow-y-auto rounded-md border bg-muted/30 p-2">
          <ul className="space-y-0.5">
            {hosts.map((h) => (
              <li key={h.id || h.name} className="break-all font-mono text-xs">
                {h.name}
              </li>
            ))}
          </ul>
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={submitting}
          >
            Cancel
          </Button>
          <Button type="button" onClick={handleConfirm} disabled={submitting}>
            {submitting ? "Restarting…" : "Restart service"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
