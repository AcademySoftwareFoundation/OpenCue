"use client";

import { getJob, getJobComments, JobComment } from "@/app/utils/get_utils";
import {
  addJobComment,
  deleteJobComment,
  saveJobComment,
} from "@/app/utils/action_utils";
import {
  CommentMacro,
  deleteCommentMacro,
  loadCommentMacros,
  upsertCommentMacro,
} from "@/app/utils/comment_macros";
import { handleError } from "@/app/utils/notify_utils";
import { Job } from "@/app/jobs/columns";
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
import { ThemeToggle } from "@/components/ui/theme-toggle";
import CueWebIcon from "@/components/ui/cuewebicon";
import { UNKNOWN_USER } from "@/app/utils/constants";
import { useParams, useSearchParams } from "next/navigation";
import * as React from "react";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import Markdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";

const PREDEFINED_HEADER = "Use a predefined comment…";
const PREDEFINED_ADD = "> Add predefined comment";
const PREDEFINED_EDIT = "> Edit predefined comment";
const PREDEFINED_DELETE = "> Delete predefined comment";

// CueGUI timestamps are unix seconds — see comment.Comment in proto/src/comment.proto.
function formatTimestamp(unixSeconds: number): string {
  if (!unixSeconds) return "";
  return new Date(unixSeconds * 1000).toLocaleString();
}

type MacroDialogState =
  | { mode: "closed" }
  | { mode: "add" }
  | { mode: "edit"; original: CommentMacro };

export default function JobCommentsPage() {
  const params = useParams<{ "job-name": string }>();
  const searchParams = useSearchParams();
  const jobId = searchParams.get("jobId") ?? "";
  const username = searchParams.get("username") ?? UNKNOWN_USER;

  const [job, setJob] = React.useState<Job | null>(null);
  const [comments, setComments] = React.useState<JobComment[]>([]);
  const [loading, setLoading] = React.useState(true);

  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [subject, setSubject] = React.useState("");
  const [message, setMessage] = React.useState("");
  const [dirty, setDirty] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);

  const [macros, setMacros] = React.useState<CommentMacro[]>([]);
  const [macroDialog, setMacroDialog] = React.useState<MacroDialogState>({ mode: "closed" });

  const selected = React.useMemo(
    () => comments.find((c) => c.id === selectedId) ?? null,
    [comments, selectedId]
  );
  const isAuthor = selected ? selected.user === username : true;
  const isNew = selectedId === null;

  const fetchAll = React.useCallback(async () => {
    if (!jobId) {
      setLoading(false);
      return;
    }
    try {
      const fetchedJob = await getJob(jobId);
      setJob(fetchedJob);
      if (fetchedJob) {
        const fetchedComments = await getJobComments(fetchedJob);
        setComments(fetchedComments);
      }
    } catch (error) {
      handleError(error, "Error fetching comments");
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  React.useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  React.useEffect(() => {
    setMacros(loadCommentMacros());
  }, []);

  const refreshComments = React.useCallback(async () => {
    if (!job) return;
    try {
      const fetched = await getJobComments(job);
      setComments(fetched);
    } catch (error) {
      handleError(error, "Error refreshing comments");
    }
  }, [job]);

  const startNew = React.useCallback(() => {
    setSelectedId(null);
    setSubject("");
    setMessage("");
    setDirty(false);
  }, []);

  const handleSelect = (comment: JobComment) => {
    setSelectedId(comment.id);
    setSubject(comment.subject);
    setMessage(comment.message ?? "");
    setDirty(false);
  };

  const handleSave = async () => {
    if (!job || !subject.trim()) return;
    setSubmitting(true);
    try {
      if (isNew) {
        await addJobComment(job, username, subject.trim(), message);
      } else if (selected) {
        await saveJobComment({
          ...selected,
          subject: subject.trim(),
          message,
        });
      }
      await refreshComments();
      setDirty(false);
      if (isNew) startNew();
    } catch (error) {
      handleError(error, "Error saving comment");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!selected) return;
    if (!window.confirm("Delete the selected comment?")) return;
    setSubmitting(true);
    try {
      await deleteJobComment(selected);
      await refreshComments();
      startNew();
    } catch (error) {
      handleError(error, "Error deleting comment");
    } finally {
      setSubmitting(false);
    }
  };

  const applyMacro = (macro: CommentMacro) => {
    setSelectedId(null);
    setSubject(macro.subject);
    setMessage(macro.message);
    setDirty(true);
  };

  const handlePredefinedChange = (value: string) => {
    if (value === PREDEFINED_HEADER) return;
    if (value === PREDEFINED_ADD) {
      setMacroDialog({ mode: "add" });
      return;
    }
    if (value === PREDEFINED_EDIT) {
      const name = window.prompt("Edit which predefined comment? (enter name)");
      if (!name) return;
      const found = macros.find((m) => m.name === name);
      if (!found) {
        window.alert(`No predefined comment named "${name}"`);
        return;
      }
      setMacroDialog({ mode: "edit", original: found });
      return;
    }
    if (value === PREDEFINED_DELETE) {
      const name = window.prompt("Delete which predefined comment? (enter name)");
      if (!name) return;
      if (!macros.some((m) => m.name === name)) {
        window.alert(`No predefined comment named "${name}"`);
        return;
      }
      if (window.confirm(`Delete predefined comment "${name}"?`)) {
        setMacros(deleteCommentMacro(name));
      }
      return;
    }
    const macro = macros.find((m) => m.name === value);
    if (macro) applyMacro(macro);
  };

  const jobName = job?.name ?? decodeURIComponent(params?.["job-name"] ?? "");

  return (
    <div className="container mx-auto py-6 max-w-6xl">
      <ToastContainer />
      <div className="flex items-center justify-between px-1 py-2">
        <CueWebIcon height={40} />
        <ThemeToggle />
      </div>

      <h1 className="text-2xl font-semibold mb-1">Comments</h1>
      <p className="text-sm text-muted-foreground mb-4 break-all">{jobName}</p>

      {loading ? (
        <div className="text-sm text-muted-foreground">Loading…</div>
      ) : !job ? (
        <div className="text-sm text-destructive">
          Job not found. Make sure `jobId` is supplied in the URL.
        </div>
      ) : (
        <>
          {/* Comment list */}
          <section className="rounded-lg border border-border overflow-hidden mb-4">
            <div className="grid grid-cols-12 gap-2 px-3 py-2 text-xs font-semibold uppercase tracking-wide bg-muted/50">
              <div className="col-span-6">Subject</div>
              <div className="col-span-3">User</div>
              <div className="col-span-3">Date</div>
            </div>
            {comments.length === 0 ? (
              <div className="px-3 py-4 text-sm text-muted-foreground">No comments yet.</div>
            ) : (
              <ul>
                {comments.map((c) => {
                  const isSelected = c.id === selectedId;
                  return (
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
                        "grid grid-cols-12 gap-2 px-3 py-2 text-sm cursor-pointer border-t border-border " +
                        (isSelected ? "bg-accent" : "hover:bg-accent/50")
                      }
                    >
                      <div className="col-span-6 truncate font-medium">{c.subject}</div>
                      <div className="col-span-3 truncate text-muted-foreground">
                        {c.user || "unknown"}
                      </div>
                      <div className="col-span-3 truncate text-muted-foreground">
                        {formatTimestamp(c.timestamp)}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          {/* Preview (rendered markdown for selected comment) */}
          {selected && (
            <section className="mb-4 rounded-lg border border-border p-4">
              <div className="text-xs uppercase tracking-wide text-muted-foreground mb-2">
                Preview
              </div>
              <div className="prose prose-sm dark:prose-invert max-w-none break-words">
                <Markdown rehypePlugins={[rehypeSanitize]}>{message || ""}</Markdown>
              </div>
            </section>
          )}

          {/* Edit area */}
          <section className="rounded-lg border border-border p-4 mb-4">
            <h2 className="text-base font-semibold mb-3">
              {isNew ? "New comment" : isAuthor ? "Edit comment" : "View comment (read-only)"}
            </h2>
            <div className="space-y-3">
              <div>
                <label htmlFor="comment-subject" className="block text-sm mb-1">
                  Subject
                </label>
                <Input
                  id="comment-subject"
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
                <label htmlFor="comment-message" className="block text-sm mb-1">
                  Message (markdown supported)
                </label>
                <textarea
                  id="comment-message"
                  value={message}
                  onChange={(e) => {
                    setMessage(e.target.value);
                    setDirty(true);
                  }}
                  placeholder="Write your comment…"
                  rows={6}
                  disabled={submitting || (!isNew && !isAuthor)}
                  className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm \
                    ring-offset-background placeholder:text-muted-foreground \
                    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring \
                    focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                />
              </div>
            </div>
          </section>

          {/* Action bar — mirrors CueGUI Comments dialog buttons */}
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={PREDEFINED_HEADER}
              onChange={(e) => handlePredefinedChange(e.target.value)}
              className="h-10 rounded-md border border-input bg-background px-3 text-sm \
                ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label="Predefined comments"
            >
              <option value={PREDEFINED_HEADER}>{PREDEFINED_HEADER}</option>
              {macros.map((m) => (
                <option key={m.name} value={m.name}>
                  {m.name}
                </option>
              ))}
              <option value={PREDEFINED_ADD}>{PREDEFINED_ADD}</option>
              <option value={PREDEFINED_EDIT}>{PREDEFINED_EDIT}</option>
              <option value={PREDEFINED_DELETE}>{PREDEFINED_DELETE}</option>
            </select>

            <div className="ml-auto flex flex-wrap items-center gap-2">
              <Button
                variant="outline"
                onClick={startNew}
                disabled={submitting}
              >
                New
              </Button>
              <Button
                onClick={handleSave}
                disabled={
                  submitting ||
                  !subject.trim() ||
                  (!isNew && !isAuthor) ||
                  (!isNew && !dirty)
                }
              >
                {submitting
                  ? "Saving…"
                  : isNew
                  ? "Save new comment"
                  : "Save changes"}
              </Button>
              <Button
                variant="destructive"
                onClick={handleDelete}
                disabled={submitting || !selected || !isAuthor}
              >
                Delete
              </Button>
            </div>
          </div>
        </>
      )}

      <MacroDialog
        state={macroDialog}
        onClose={() => setMacroDialog({ mode: "closed" })}
        onSave={(macro, replaceName) => {
          setMacros(upsertCommentMacro(macro, replaceName));
          setMacroDialog({ mode: "closed" });
        }}
        existingNames={macros.map((m) => m.name)}
      />
    </div>
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
  const collidesWithExisting =
    trimmedName.length > 0 &&
    trimmedName !== editing?.name &&
    existingNames.includes(trimmedName);
  const canSave = trimmedName.length > 0 && trimmedSubject.length > 0 && !collidesWithExisting;

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {editing ? "Edit predefined comment" : "Add predefined comment"}
          </DialogTitle>
          <DialogDescription>
            Predefined comments are saved in this browser only.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-2">
          <div>
            <label htmlFor="macro-name" className="block text-sm mb-1">
              Name
            </label>
            <Input
              id="macro-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Macro name"
            />
            {collidesWithExisting && (
              <p className="text-xs text-destructive mt-1">
                A predefined comment with that name already exists.
              </p>
            )}
          </div>
          <div>
            <label htmlFor="macro-subject" className="block text-sm mb-1">
              Subject
            </label>
            <Input
              id="macro-subject"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Subject"
            />
          </div>
          <div>
            <label htmlFor="macro-message" className="block text-sm mb-1">
              Message
            </label>
            <textarea
              id="macro-message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={5}
              className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm \
                ring-offset-background placeholder:text-muted-foreground \
                focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring \
                focus-visible:ring-offset-2"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            disabled={!canSave}
            onClick={() =>
              onSave(
                { name: trimmedName, subject: trimmedSubject, message },
                editing?.name
              )
            }
          >
            Apply
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
