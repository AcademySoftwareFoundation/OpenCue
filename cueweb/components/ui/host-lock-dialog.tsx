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
import { lockHosts, unlockHosts } from "@/app/utils/action_utils";
import {
  HOSTS_CHANGED_EVENT,
  OPEN_HOST_LOCK_EVENT,
  type HostLockAction,
  type HostsChangedDetail,
  type OpenHostLockDetail,
} from "@/components/ui/host-action-events";

/**
 * Lock / Unlock confirmation dialog for the Monitor Hosts table. Mounted
 * once at the page level and opened in response to a
 * `cueweb:open-host-lock` CustomEvent dispatched from the host row context
 * menu (lockHostGivenRow / unlockHostGivenRow). Decoupled this way so the
 * menu's free-function handlers can stay free of component refs / table
 * state, mirroring the SetPriorityDialog pattern.
 *
 * On confirm it calls the batch-capable lockHosts/unlockHosts action and
 * then dispatches `cueweb:hosts-changed` with the affected ids and the new
 * lockState so the hosts page can update those rows immediately (optimistic)
 * and reconcile on its next fetch, instead of waiting for the 30s poll.
 */

export function HostLockDialog() {
  const [open, setOpen] = React.useState(false);
  const [hosts, setHosts] = React.useState<Host[]>([]);
  const [action, setAction] = React.useState<HostLockAction>("lock");
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      const detail = (e as CustomEvent<OpenHostLockDetail>).detail;
      if (!detail?.hosts?.length || !detail.action) return;
      setHosts(detail.hosts);
      setAction(detail.action);
      setOpen(true);
    }
    window.addEventListener(OPEN_HOST_LOCK_EVENT, handler);
    return () => window.removeEventListener(OPEN_HOST_LOCK_EVENT, handler);
  }, []);

  async function handleConfirm() {
    if (!hosts.length) return;
    setSubmitting(true);
    try {
      if (action === "lock") {
        await lockHosts(hosts);
      } else {
        await unlockHosts(hosts);
      }
      window.dispatchEvent(
        new CustomEvent<HostsChangedDetail>(HOSTS_CHANGED_EVENT, {
          detail: {
            hostIds: hosts.map((h) => h.id),
            patch: { lockState: action === "lock" ? "LOCKED" : "OPEN" },
          },
        }),
      );
      setOpen(false);
    } finally {
      setSubmitting(false);
    }
  }

  const verb = action === "lock" ? "Lock" : "Unlock";
  const count = hosts.length;

  return (
    <Dialog open={open} onOpenChange={submitting ? () => {} : setOpen}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>
            {verb} {count} host{count === 1 ? "" : "s"}?
          </DialogTitle>
          <DialogDescription>
            {action === "lock"
              ? "Locked hosts stop booking new frames. Frames already running keep going."
              : "Unlocked hosts return to the booking pool and can pick up new frames."}
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
            {submitting ? `${verb}ing…` : verb}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
