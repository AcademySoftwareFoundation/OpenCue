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
import { addHostComment, deleteHosts, deleteJobComment, renameHostTag, saveJobComment, setHostAllocation, takeHostOwnership } from "@/app/utils/action_utils";
import {
  CommentMacro,
  deleteCommentMacro,
  loadCommentMacros,
  upsertCommentMacro,
} from "@/app/utils/comment_macros";
import { UNKNOWN_USER } from "@/app/utils/constants";
import Markdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";

// Comment timestamps come from Cuebot as unix seconds.
function formatCommentTimestamp(unixSeconds: number): string {
  if (!unixSeconds) return "";
  return new Date(unixSeconds * 1000).toLocaleString();
}
import { handleError, toastSuccess, toastWarning } from "@/app/utils/notify_utils";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
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
  OPEN_HOST_TAKE_OWNERSHIP_EVENT,
  type OpenHostAllocationDetail,
  type OpenHostCommentsDetail,
  type OpenHostDeleteDetail,
  type OpenHostRenameTagDetail,
  type OpenHostTakeOwnershipDetail,
} from "@/components/ui/host-action-events";

function notifyChanged(hosts: Host[], patch: object) {
  window.dispatchEvent(
    new CustomEvent(HOSTS_CHANGED_EVENT, { detail: { hostIds: hosts.map((h) => h.id), patch } }),
  );
}

const SELECT_CLASS =
  "h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50";

// --- Comments -------------------------------------------------------------
// CueGUI's host "Comments..." opens a modal listing every comment with the
// subject/user/date, a read-only markdown preview, an edit area, and a
// predefined-comment ("macro") dropdown. This mirrors that window (and the
// Monitor Jobs comments dialog), reusing the shared comment-macro store.
const PREDEFINED_HEADER = "Use a predefined comment…";
const PREDEFINED_ADD = "> Add predefined comment";
const PREDEFINED_EDIT = "> Edit predefined comment";
const PREDEFINED_DELETE = "> Delete predefined comment";

type MacroDialogState = { mode: "closed" } | { mode: "add" } | { mode: "edit"; original: CommentMacro };

function HostCommentsDialog() {
  const { data: session } = useSession();
  const currentUser =
    session?.user?.email?.split("@")[0] ?? session?.user?.name ?? UNKNOWN_USER;

  const [open, setOpen] = React.useState(false);
  const [host, setHost] = React.useState<Host | null>(null);
  const [comments, setComments] = React.useState<JobComment[]>([]);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [subject, setSubject] = React.useState("");
  const [message, setMessage] = React.useState("");
  const [dirty, setDirty] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);
  const [macros, setMacros] = React.useState<CommentMacro[]>([]);
  const [macroDialog, setMacroDialog] = React.useState<MacroDialogState>({ mode: "closed" });
  // Themed "which predefined comment?" picker for Edit / Delete.
  const [macroPicker, setMacroPicker] = React.useState<null | "edit" | "delete">(null);

  const selected = React.useMemo(() => comments.find((c) => c.id === selectedId) ?? null, [comments, selectedId]);
  const isNew = selectedId === null;
  const isAuthor = selected ? selected.user === currentUser : true;

  const refresh = React.useCallback(async (h: Host) => {
    try {
      setComments(await getHostComments(h));
    } catch (error) {
      handleError(error, "Could not load host comments");
    }
  }, []);

  React.useEffect(() => {
    function handler(e: Event) {
      const h = (e as CustomEvent<OpenHostCommentsDetail>).detail.hosts[0];
      setHost(h);
      setSelectedId(null);
      setSubject("");
      setMessage("");
      setDirty(false);
      setComments([]);
      setMacros(loadCommentMacros());
      setOpen(true);
      if (h) refresh(h);
    }
    window.addEventListener(OPEN_HOST_COMMENTS_EVENT, handler);
    return () => window.removeEventListener(OPEN_HOST_COMMENTS_EVENT, handler);
  }, [refresh]);

  function startNew() {
    setSelectedId(null);
    setSubject("");
    setMessage("");
    setDirty(false);
  }
  function handleSelect(c: JobComment) {
    setSelectedId(c.id);
    setSubject(c.subject);
    setMessage(c.message ?? "");
    setDirty(false);
  }

  async function handleSave() {
    if (!host || !subject.trim()) return;
    setSubmitting(true);
    try {
      if (isNew) await addHostComment(host, currentUser, subject.trim(), message);
      else if (selected) await saveJobComment({ ...selected, subject: subject.trim(), message });
      await refresh(host);
      notifyChanged([host], { hasComment: true });
      setDirty(false);
      if (isNew) startNew();
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!host || !selected) return;
    setSubmitting(true);
    try {
      const ok = await deleteJobComment(selected);
      if (ok) {
        const next = comments.filter((c) => c.id !== selected.id);
        await refresh(host);
        startNew();
        // Clear the row's comment indicator once the last comment is gone.
        notifyChanged([host], { hasComment: next.length > 0 });
      }
    } finally {
      setSubmitting(false);
    }
  }

  function handlePredefinedChange(value: string) {
    if (value === PREDEFINED_HEADER) return;
    if (value === PREDEFINED_ADD) {
      setMacroDialog({ mode: "add" });
      return;
    }
    if (value === PREDEFINED_EDIT) {
      if (macros.length === 0) {
        toastWarning("No predefined comments to edit.");
        return;
      }
      setMacroPicker("edit");
      return;
    }
    if (value === PREDEFINED_DELETE) {
      if (macros.length === 0) {
        toastWarning("No predefined comments to delete.");
        return;
      }
      setMacroPicker("delete");
      return;
    }
    const macro = macros.find((m) => m.name === value);
    if (macro) {
      setSelectedId(null);
      setSubject(macro.subject);
      setMessage(macro.message);
      setDirty(true);
    }
  }

  return (
    <>
      <Dialog open={open} onOpenChange={submitting ? () => {} : setOpen}>
        <DialogContent className="max-h-[88vh] overflow-y-auto sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle>Comments</DialogTitle>
            <DialogDescription className="break-all">{host?.name}</DialogDescription>
          </DialogHeader>

          {/* Comment list */}
          <section className="overflow-hidden rounded-lg border border-border">
            <div className="grid grid-cols-12 gap-2 bg-muted/50 px-3 py-2 text-xs font-semibold uppercase tracking-wide">
              <div className="col-span-6">Subject</div>
              <div className="col-span-3">User</div>
              <div className="col-span-3">Date</div>
            </div>
            {comments.length === 0 ? (
              <div className="px-3 py-4 text-sm text-muted-foreground">No comments yet.</div>
            ) : (
              <ul className="max-h-48 overflow-y-auto">
                {comments.map((c) => (
                  <li
                    key={c.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => handleSelect(c)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        handleSelect(c);
                      }
                    }}
                    className={
                      "grid cursor-pointer grid-cols-12 gap-2 border-t border-border px-3 py-2 text-sm " +
                      (c.id === selectedId ? "bg-accent" : "hover:bg-accent/50")
                    }
                  >
                    <div className="col-span-6 truncate font-medium">{c.subject}</div>
                    <div className="col-span-3 truncate text-muted-foreground">{c.user || "unknown"}</div>
                    <div className="col-span-3 truncate text-muted-foreground">{formatCommentTimestamp(c.timestamp)}</div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {selected && message ? (
            <section className="rounded-lg border border-border p-3">
              <div className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">Preview</div>
              <div className="prose prose-sm dark:prose-invert max-w-none break-words">
                <Markdown rehypePlugins={[rehypeSanitize]}>{message}</Markdown>
              </div>
            </section>
          ) : null}

          {/* Edit area */}
          <section className="space-y-3">
            <h2 className="text-sm font-semibold">
              {isNew ? "New comment" : isAuthor ? "Edit comment" : "View comment (read-only)"}
            </h2>
            <div>
              <label htmlFor="host-comment-subject" className="mb-1 block text-sm">Subject</label>
              <Input
                id="host-comment-subject"
                value={subject}
                onChange={(e) => {
                  setSubject(e.target.value);
                  setDirty(true);
                }}
                placeholder="Subject"
                disabled={submitting || (!isNew && !isAuthor)}
              />
            </div>
            <div>
              <label htmlFor="host-comment-message" className="mb-1 block text-sm">Message (markdown supported)</label>
              <textarea
                id="host-comment-message"
                value={message}
                onChange={(e) => {
                  setMessage(e.target.value);
                  setDirty(true);
                }}
                placeholder="Write your comment…"
                rows={5}
                disabled={submitting || (!isNew && !isAuthor)}
                className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
              />
            </div>
          </section>

          <DialogFooter className="flex-wrap sm:justify-between">
            <select
              value={PREDEFINED_HEADER}
              onChange={(e) => handlePredefinedChange(e.target.value)}
              className="h-9 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label="Predefined comments"
            >
              <option value={PREDEFINED_HEADER}>{PREDEFINED_HEADER}</option>
              {macros.map((m) => (
                <option key={m.name} value={m.name}>{m.name}</option>
              ))}
              <option value={PREDEFINED_ADD}>{PREDEFINED_ADD}</option>
              <option value={PREDEFINED_EDIT}>{PREDEFINED_EDIT}</option>
              <option value={PREDEFINED_DELETE}>{PREDEFINED_DELETE}</option>
            </select>
            <div className="flex flex-wrap items-center gap-2">
              <Button variant="outline" onClick={startNew} disabled={submitting}>New</Button>
              <Button
                onClick={handleSave}
                disabled={submitting || !subject.trim() || (!isNew && !isAuthor) || (!isNew && !dirty)}
              >
                {submitting ? "Saving…" : isNew ? "Save New Comment" : "Save changes"}
              </Button>
              <Button variant="destructive" onClick={handleDelete} disabled={submitting || !selected || !isAuthor}>
                Delete
              </Button>
              <Button variant="ghost" onClick={() => setOpen(false)} disabled={submitting}>Close</Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <MacroDialog
        state={macroDialog}
        onClose={() => setMacroDialog({ mode: "closed" })}
        onSave={(macro, replaceName) => {
          setMacros(upsertCommentMacro(macro, replaceName));
          setMacroDialog({ mode: "closed" });
        }}
        existingNames={macros.map((m) => m.name)}
      />

      <MacroPickerDialog
        mode={macroPicker}
        macros={macros}
        onClose={() => setMacroPicker(null)}
        onPick={(name) => {
          if (macroPicker === "edit") {
            const found = macros.find((m) => m.name === name);
            if (found) setMacroDialog({ mode: "edit", original: found });
          } else if (macroPicker === "delete") {
            setMacros(deleteCommentMacro(name));
          }
          setMacroPicker(null);
        }}
      />
    </>
  );
}

// Themed replacement for the native "which predefined comment?" prompt: a
// select of saved macro names with Cancel / OK.
function MacroPickerDialog({
  mode,
  macros,
  onClose,
  onPick,
}: {
  mode: null | "edit" | "delete";
  macros: CommentMacro[];
  onClose: () => void;
  onPick: (name: string) => void;
}) {
  const [name, setName] = React.useState("");
  React.useEffect(() => {
    if (mode) setName(macros[0]?.name ?? "");
  }, [mode, macros]);

  return (
    <Dialog open={mode !== null} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>{mode === "delete" ? "Delete predefined comment" : "Edit predefined comment"}</DialogTitle>
          <DialogDescription>Which predefined comment?</DialogDescription>
        </DialogHeader>
        <div className="py-2">
          <select
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            aria-label="Predefined comment"
          >
            {macros.map((m) => (
              <option key={m.name} value={m.name}>{m.name}</option>
            ))}
          </select>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button
            variant={mode === "delete" ? "destructive" : "default"}
            disabled={!name}
            onClick={() => name && onPick(name)}
          >
            {mode === "delete" ? "Delete" : "Edit"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface MacroDialogProps {
  state: MacroDialogState;
  onClose: () => void;
  onSave: (macro: CommentMacro, replaceName?: string) => void;
  existingNames: string[];
}

function MacroDialog({ state, onClose, onSave, existingNames }: MacroDialogProps) {
  const open = state.mode !== "closed";
  const editing = state.mode === "edit" ? state.original : null;
  const [name, setName] = React.useState("");
  const [subject, setSubject] = React.useState("");
  const [message, setMessage] = React.useState("");

  React.useEffect(() => {
    if (state.mode === "edit") {
      setName(state.original.name);
      setSubject(state.original.subject);
      setMessage(state.original.message);
    } else if (state.mode === "add") {
      setName("");
      setSubject("");
      setMessage("");
    }
  }, [state]);

  const trimmedName = name.trim();
  const trimmedSubject = subject.trim();
  const collides = trimmedName.length > 0 && trimmedName !== editing?.name && existingNames.includes(trimmedName);
  const canSave = trimmedName.length > 0 && trimmedSubject.length > 0 && !collides;

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{editing ? "Edit predefined comment" : "Add predefined comment"}</DialogTitle>
          <DialogDescription>Predefined comments are saved in this browser only.</DialogDescription>
        </DialogHeader>
        <div className="space-y-3 py-2">
          <div>
            <label htmlFor="host-macro-name" className="mb-1 block text-sm">Name</label>
            <Input id="host-macro-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Macro name" />
            {collides && <p className="mt-1 text-xs text-destructive">A predefined comment with that name already exists.</p>}
          </div>
          <div>
            <label htmlFor="host-macro-subject" className="mb-1 block text-sm">Subject</label>
            <Input id="host-macro-subject" value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Subject" />
          </div>
          <div>
            <label htmlFor="host-macro-message" className="mb-1 block text-sm">Message</label>
            <textarea
              id="host-macro-message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={5}
              className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button disabled={!canSave} onClick={() => onSave({ name: trimmedName, subject: trimmedSubject, message }, editing?.name)}>
            Apply
          </Button>
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
      // Offer the union of tags across all selected hosts, not just the first.
      const union = Array.from(new Set(hs.flatMap((h) => h.tags ?? []))).sort();
      setOldTag(union[0] ?? "");
      setNewTag(union[0] ?? "");
      setOpen(true);
    }
    window.addEventListener(OPEN_HOST_RENAME_TAG_EVENT, handler);
    return () => window.removeEventListener(OPEN_HOST_RENAME_TAG_EVENT, handler);
  }, []);

  const tags = React.useMemo(
    () => Array.from(new Set(hosts.flatMap((h) => h.tags ?? []))).sort(),
    [hosts],
  );

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
      // Clear the prior open's selection so a fast OK before getAllocations()
      // resolves can't move the new hosts to the previous allocation. With
      // allocId empty the OK button stays disabled until fresh data loads.
      setAllocs([]);
      setAllocId("");
      setBusy(false);
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

// --- Take Ownership -------------------------------------------------------
function HostTakeOwnershipDialog() {
  const { data: session } = useSession();
  const username = session?.user?.name ?? session?.user?.email ?? "cueweb";
  const [open, setOpen] = React.useState(false);
  const [hosts, setHosts] = React.useState<Host[]>([]);
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      setHosts((e as CustomEvent<OpenHostTakeOwnershipDetail>).detail.hosts);
      setOpen(true);
    }
    window.addEventListener(OPEN_HOST_TAKE_OWNERSHIP_EVENT, handler);
    return () => window.removeEventListener(OPEN_HOST_TAKE_OWNERSHIP_EVENT, handler);
  }, []);

  async function confirm() {
    setBusy(true);
    try {
      const results = await Promise.all(hosts.map((h) => takeHostOwnership(h, username)));
      if (results.every(Boolean)) {
        toastSuccess(`Took ownership of ${hosts.length} host(s)`);
        notifyChanged(hosts, {}); // owner isn't a table column; just re-fetch.
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
          <DialogTitle>Take ownership of {hosts.length === 1 ? "this host" : "these hosts"}?</DialogTitle>
        </DialogHeader>
        <div className="space-y-2 py-2 text-sm">
          <p className="text-muted-foreground">
            The host(s) will be owned by <span className="font-mono">{username}</span>.
          </p>
          <ul className="max-h-40 overflow-y-auto rounded-md border bg-muted/40 p-2 font-mono text-xs">
            {hosts.map((h) => (
              <li key={h.id}>{h.name}</li>
            ))}
          </ul>
        </div>
        <DialogFooter>
          <Button onClick={confirm} disabled={busy}>{busy ? "Taking…" : "Ok"}</Button>
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
      <HostTakeOwnershipDialog />
    </>
  );
}
