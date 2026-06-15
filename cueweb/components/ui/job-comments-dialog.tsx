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
import Markdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";

import type { Job } from "@/app/jobs/columns";
import { getJobComments, JobComment } from "@/app/utils/get_utils";
import { addJobComment, deleteJobComment, saveJobComment } from "@/app/utils/action_utils";
import {
  CommentMacro,
  deleteCommentMacro,
  loadCommentMacros,
  upsertCommentMacro,
} from "@/app/utils/comment_macros";
import { handleError, toastWarning } from "@/app/utils/notify_utils";
import { UNKNOWN_USER } from "@/app/utils/constants";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

// CueGUI's job "Comments..." opens a modal window; this mirrors it (instead of
// the previous new-tab page). Opened by a `cueweb:open-job-comments` event
// carrying the job. Mounted once on the Monitor Jobs page.
export const OPEN_JOB_COMMENTS_EVENT = "cueweb:open-job-comments";
export type OpenJobCommentsDetail = { job: Job };

const PREDEFINED_HEADER = "Use a predefined comment…";
const PREDEFINED_ADD = "> Add predefined comment";
const PREDEFINED_EDIT = "> Edit predefined comment";
const PREDEFINED_DELETE = "> Delete predefined comment";

function formatTimestamp(unixSeconds: number): string {
  if (!unixSeconds) return "";
  return new Date(unixSeconds * 1000).toLocaleString();
}

type MacroDialogState = { mode: "closed" } | { mode: "add" } | { mode: "edit"; original: CommentMacro };

export function JobCommentsDialog() {
  const { data: session } = useSession();
  const currentUser =
    session?.user?.email?.split("@")[0] ?? session?.user?.name ?? UNKNOWN_USER;

  const [open, setOpen] = React.useState(false);
  const [job, setJob] = React.useState<Job | null>(null);
  const [comments, setComments] = React.useState<JobComment[]>([]);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [subject, setSubject] = React.useState("");
  const [message, setMessage] = React.useState("");
  const [dirty, setDirty] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);
  const [macros, setMacros] = React.useState<CommentMacro[]>([]);
  const [macroDialog, setMacroDialog] = React.useState<MacroDialogState>({ mode: "closed" });
  // Themed "which predefined comment?" picker for Edit / Delete (replaces the
  // native window.prompt).
  const [macroPicker, setMacroPicker] = React.useState<null | "edit" | "delete">(null);

  const selected = React.useMemo(() => comments.find((c) => c.id === selectedId) ?? null, [comments, selectedId]);
  const isNew = selectedId === null;
  const isAuthor = selected ? selected.user === currentUser : true;

  const refresh = React.useCallback(async (j: Job) => {
    try {
      setComments(await getJobComments(j));
    } catch (error) {
      handleError(error, "Error fetching comments");
    }
  }, []);

  React.useEffect(() => {
    function handler(e: Event) {
      const j = (e as CustomEvent<OpenJobCommentsDetail>).detail?.job;
      if (!j) return;
      setJob(j);
      setSelectedId(null);
      setSubject("");
      setMessage("");
      setDirty(false);
      setComments([]);
      setMacros(loadCommentMacros());
      setOpen(true);
      refresh(j);
    }
    window.addEventListener(OPEN_JOB_COMMENTS_EVENT, handler);
    return () => window.removeEventListener(OPEN_JOB_COMMENTS_EVENT, handler);
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
    if (!job || !subject.trim()) return;
    setSubmitting(true);
    try {
      if (isNew) await addJobComment(job, currentUser, subject.trim(), message);
      else if (selected) await saveJobComment({ ...selected, subject: subject.trim(), message });
      await refresh(job);
      setDirty(false);
      if (isNew) startNew();
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!job || !selected) return;
    setSubmitting(true);
    try {
      await deleteJobComment(selected);
      await refresh(job);
      startNew();
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
            <DialogDescription className="break-all">{job?.name}</DialogDescription>
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
                    <div className="col-span-3 truncate text-muted-foreground">{formatTimestamp(c.timestamp)}</div>
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
              <label htmlFor="job-comment-subject" className="mb-1 block text-sm">Subject</label>
              <Input
                id="job-comment-subject"
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
              <label htmlFor="job-comment-message" className="mb-1 block text-sm">Message (markdown supported)</label>
              <textarea
                id="job-comment-message"
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
            <label htmlFor="macro-name" className="mb-1 block text-sm">Name</label>
            <Input id="macro-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Macro name" />
            {collides && <p className="mt-1 text-xs text-destructive">A predefined comment with that name already exists.</p>}
          </div>
          <div>
            <label htmlFor="macro-subject" className="mb-1 block text-sm">Subject</label>
            <Input id="macro-subject" value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Subject" />
          </div>
          <div>
            <label htmlFor="macro-message" className="mb-1 block text-sm">Message</label>
            <textarea
              id="macro-message"
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
