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
import { rebootHosts } from "@/app/utils/action_utils";
import {
  HOSTS_CHANGED_EVENT,
  OPEN_HOST_REBOOT_EVENT,
  type HostsChangedDetail,
  type OpenHostRebootDetail,
} from "@/components/ui/host-action-events";

/**
 * Immediate-reboot confirmation dialog for the Monitor Hosts table.
 * Mounted once at the page level and opened in response to a
 * `cueweb:open-host-reboot` CustomEvent dispatched from the host row
 * context menu (rebootHostGivenRow). Decoupled the same way as the lock
 * dialog so the menu's free-function handlers stay free of component refs.
 *
 * An immediate reboot KILLS frames running on the host, so this is the
 * destructive variant that requires the extra "are you sure" step
 * (reboot-when-idle is non-destructive and fires without a dialog).
 *
 * On confirm it calls the batch-capable rebootHosts action, then fires
 * `cueweb:hosts-changed` with the optimistic REBOOTING state so the hosts
 * page updates the affected rows immediately and reconciles on its next
 * fetch.
 */

export function HostRebootDialog() {
  const [open, setOpen] = React.useState(false);
  const [hosts, setHosts] = React.useState<Host[]>([]);
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      const detail = (e as CustomEvent<OpenHostRebootDetail>).detail;
      if (!detail?.hosts?.length) return;
      setHosts(detail.hosts);
      setOpen(true);
    }
    window.addEventListener(OPEN_HOST_REBOOT_EVENT, handler);
    return () => window.removeEventListener(OPEN_HOST_REBOOT_EVENT, handler);
  }, []);

  async function handleConfirm() {
    if (!hosts.length) return;
    setSubmitting(true);
    try {
      const ok = await rebootHosts(hosts);
      // Only fire the optimistic update when the reboot request succeeded.
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
      // rebootHosts routes failures through performAction (toast + false), so
      // this catch only guards against an unexpected throw. Dialog stays open.
      console.error("Failed to reboot host(s):", error);
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
            Reboot {count} host{count === 1 ? "" : "s"}?
          </DialogTitle>
          <DialogDescription>
            Frames running on {count === 1 ? "this host" : "these hosts"} will be
            killed. To reboot without killing frames, use “Reboot When Idle”
            instead.
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
          <Button
            type="button"
            variant="destructive"
            onClick={handleConfirm}
            disabled={submitting}
          >
            {submitting ? "Rebooting…" : "Reboot"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
