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
import { useSession } from "next-auth/react";

import type { Allocation, Host, JobComment } from "@/app/utils/get_utils";
import { getAllocations, getHostComments } from "@/app/utils/get_utils";
import { addHostComment, deleteHosts, renameHostTag, setHostAllocation } from "@/app/utils/action_utils";
import { handleError, toastSuccess, toastWarning } from "@/app/utils/notify_utils";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  HOSTS_CHANGED_EVENT,
  OPEN_HOST_ALLOCATION_EVENT,
  OPEN_HOST_COMMENTS_EVENT,
  OPEN_HOST_DELETE_EVENT,
  OPEN_HOST_RENAME_TAG_EVENT,
  type OpenHostAllocationDetail,
  type OpenHostCommentsDetail,
  type OpenHostDeleteDetail,
  type OpenHostRenameTagDetail,
} from "@/components/ui/host-action-events";

function notifyChanged(hosts: Host[], patch: object) {
  window.dispatchEvent(
    new CustomEvent(HOSTS_CHANGED_EVENT, { detail: { hostIds: hosts.map((h) => h.id), patch } }),
  );
}

const SELECT_CLASS =
  "h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50";

// --- Comments -------------------------------------------------------------
function HostCommentsDialog() {
  const { data: session } = useSession();
  const username = session?.user?.name ?? session?.user?.email ?? "cueweb";
  const [open, setOpen] = React.useState(false);
  const [host, setHost] = React.useState<Host | null>(null);
  const [comments, setComments] = React.useState<JobComment[]>([]);
  const [subject, setSubject] = React.useState("");
  const [message, setMessage] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  const reload = React.useCallback(async (h: Host) => {
    try {
      setComments(await getHostComments(h));
    } catch (err) {
      handleError(err, "Could not load host comments");
    }
  }, []);

  React.useEffect(() => {
    function handler(e: Event) {
      const h = (e as CustomEvent<OpenHostCommentsDetail>).detail.hosts[0];
      setHost(h);
      setSubject("");
      setMessage("");
      setComments([]);
      setOpen(true);
      if (h) reload(h);
    }
    window.addEventListener(OPEN_HOST_COMMENTS_EVENT, handler);
    return () => window.removeEventListener(OPEN_HOST_COMMENTS_EVENT, handler);
  }, [reload]);

  async function save() {
    if (!host) return;
    if (!subject.trim()) {
      toastWarning("A subject is required.");
      return;
    }
    setBusy(true);
    try {
      const ok = await addHostComment(host, username, subject.trim(), message);
      if (ok) {
        toastSuccess("Added comment");
        setSubject("");
        setMessage("");
        await reload(host);
        notifyChanged([host], { hasComment: true });
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Comments — {host?.name}</DialogTitle>
        </DialogHeader>
        <div className="max-h-60 overflow-y-auto rounded-md border">
          {comments.length === 0 ? (
            <p className="p-3 text-sm text-muted-foreground">No comments.</p>
          ) : (
            <ul className="divide-y">
              {comments.map((c) => (
                <li key={c.id} className="p-2 text-sm">
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span className="font-medium text-foreground">{c.subject}</span>
                    <span>{c.user}</span>
                  </div>
                  <p className="whitespace-pre-wrap">{c.message}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="space-y-2 py-2">
          <Input value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Subject" aria-label="Subject" />
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Comment"
            aria-label="Comment"
            className="min-h-24 w-full rounded-md border border-input bg-background p-2 text-sm"
          />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)} disabled={busy}>Close</Button>
          <Button onClick={save} disabled={busy}>{busy ? "Saving…" : "Save New Comment"}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// --- Rename Tag -----------------------------------------------------------
function HostRenameTagDialog() {
  const [open, setOpen] = React.useState(false);
  const [hosts, setHosts] = React.useState<Host[]>([]);
  const [oldTag, setOldTag] = React.useState("");
  const [newTag, setNewTag] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      const hs = (e as CustomEvent<OpenHostRenameTagDetail>).detail.hosts;
      setHosts(hs);
      const tags = hs[0]?.tags ?? [];
      setOldTag(tags[0] ?? "");
      setNewTag(tags[0] ?? "");
      setOpen(true);
    }
    window.addEventListener(OPEN_HOST_RENAME_TAG_EVENT, handler);
    return () => window.removeEventListener(OPEN_HOST_RENAME_TAG_EVENT, handler);
  }, []);

  const tags = hosts[0]?.tags ?? [];

  async function save() {
    if (!oldTag || !newTag.trim()) {
      toastWarning("Pick a tag and enter a new name.");
      return;
    }
    setBusy(true);
    try {
      const ok = await renameHostTag(hosts, oldTag, newTag.trim());
      if (ok) {
        toastSuccess("Renamed tag");
        notifyChanged(hosts, {});
        setOpen(false);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Rename Tag</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 py-2">
          <label className="block text-sm">
            <span className="text-muted-foreground">Tag to rename</span>
            <select value={oldTag} onChange={(e) => setOldTag(e.target.value)} className={SELECT_CLASS} aria-label="Tag to rename">
              {tags.length === 0 ? <option value="">(no tags)</option> : null}
              {tags.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            <span className="text-muted-foreground">New name</span>
            <Input value={newTag} onChange={(e) => setNewTag(e.target.value)} aria-label="New tag name" />
          </label>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)} disabled={busy}>Cancel</Button>
          <Button onClick={save} disabled={busy || !oldTag}>OK</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// --- Change Allocation ----------------------------------------------------
function HostChangeAllocationDialog() {
  const [open, setOpen] = React.useState(false);
  const [hosts, setHosts] = React.useState<Host[]>([]);
  const [allocs, setAllocs] = React.useState<Allocation[]>([]);
  const [allocId, setAllocId] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      setHosts((e as CustomEvent<OpenHostAllocationDetail>).detail.hosts);
      setOpen(true);
      getAllocations()
        .then((a) => {
          setAllocs(a);
          setAllocId(a[0]?.id ?? "");
        })
        .catch((err) => handleError(err, "Could not load allocations"));
    }
    window.addEventListener(OPEN_HOST_ALLOCATION_EVENT, handler);
    return () => window.removeEventListener(OPEN_HOST_ALLOCATION_EVENT, handler);
  }, []);

  async function save() {
    if (!allocId) return;
    setBusy(true);
    try {
      const ok = await setHostAllocation(hosts, allocId);
      if (ok) {
        const allocName = allocs.find((a) => a.id === allocId)?.name ?? "";
        toastSuccess("Moved host(s) to allocation");
        notifyChanged(hosts, { allocName });
        setOpen(false);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Move host to allocation</DialogTitle>
        </DialogHeader>
        <div className="space-y-2 py-2 text-sm">
          <p className="text-muted-foreground">What allocation should the host(s) be moved to?</p>
          <select value={allocId} onChange={(e) => setAllocId(e.target.value)} className={SELECT_CLASS} aria-label="Allocation">
            {allocs.map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)} disabled={busy}>Cancel</Button>
          <Button onClick={save} disabled={busy || !allocId}>OK</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// --- Delete ---------------------------------------------------------------
function HostDeleteDialog() {
  const [open, setOpen] = React.useState(false);
  const [hosts, setHosts] = React.useState<Host[]>([]);
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      setHosts((e as CustomEvent<OpenHostDeleteDetail>).detail.hosts);
      setOpen(true);
    }
    window.addEventListener(OPEN_HOST_DELETE_EVENT, handler);
    return () => window.removeEventListener(OPEN_HOST_DELETE_EVENT, handler);
  }, []);

  async function confirm() {
    setBusy(true);
    try {
      const ok = await deleteHosts(hosts);
      if (ok) {
        toastSuccess(`Deleted ${hosts.length} host(s)`);
        notifyChanged(hosts, {});
        setOpen(false);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Delete selected hosts?</DialogTitle>
        </DialogHeader>
        <div className="space-y-2 py-2 text-sm">
          <p className="text-muted-foreground">This should only be done by OpenCue administrators.</p>
          <ul className="max-h-40 overflow-y-auto rounded-md border bg-muted/40 p-2 font-mono text-xs">
            {hosts.map((h) => (
              <li key={h.id}>{h.name}</li>
            ))}
          </ul>
        </div>
        <DialogFooter>
          <Button onClick={confirm} disabled={busy}>{busy ? "Deleting…" : "Ok"}</Button>
          <Button variant="outline" onClick={() => setOpen(false)} disabled={busy}>Cancel</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Mounts every host context-menu dialog. Place once on the Monitor Hosts page.
export function HostMonitorDialogs() {
  return (
    <>
      <HostCommentsDialog />
      <HostRenameTagDialog />
      <HostChangeAllocationDialog />
      <HostDeleteDialog />
    </>
  );
}
