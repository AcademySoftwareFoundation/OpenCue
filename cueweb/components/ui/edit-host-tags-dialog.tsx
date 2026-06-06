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
import { X } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Button } from "@/components/ui/button";
import type { Host } from "@/app/utils/get_utils";
import { getHosts } from "@/app/utils/get_utils";
import { addHostTags, removeHostTags } from "@/app/utils/action_utils";
import {
  HOSTS_CHANGED_EVENT,
  OPEN_HOST_TAGS_EVENT,
  type HostsChangedDetail,
  type OpenHostTagsDetail,
} from "@/components/ui/host-action-events";

/**
 * Host tag editor dialog. Mounted once at the page level and opened by a
 * `cueweb:open-host-tags` CustomEvent from the host row context menu
 * (editHostTagsGivenRow) or the host detail page's Tags tab.
 *
 * Mirrors CueGUI's TagsWidget: the host's current tags render as removable
 * chips, and a cmdk autocomplete suggests tags that already exist across
 * the host registry (loaded on open) plus a "create" option for new tags.
 * On Save the working set is diffed against the original tags and the
 * difference is applied via AddTags / RemoveTags, then a
 * `cueweb:hosts-changed` event fires so the table/detail page refresh.
 */

const uniqSorted = (xs: string[]): string[] => Array.from(new Set(xs)).sort();

export function EditHostTagsDialog() {
  const [open, setOpen] = React.useState(false);
  const [hosts, setHosts] = React.useState<Host[]>([]);
  const [originalTags, setOriginalTags] = React.useState<string[]>([]);
  const [tags, setTags] = React.useState<string[]>([]);
  const [allTags, setAllTags] = React.useState<string[]>([]);
  const [query, setQuery] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      const detail = (e as CustomEvent<OpenHostTagsDetail>).detail;
      if (!detail?.hosts?.length) return;
      const initial = uniqSorted(detail.hosts.flatMap((h) => h.tags ?? []));
      setHosts(detail.hosts);
      setOriginalTags(initial);
      setTags(initial);
      setQuery("");
      setAllTags(initial);
      setOpen(true);

      // Load the registry-wide tag set for autocomplete. Best-effort: if it
      // fails we still have this host's own tags as suggestions.
      getHosts()
        .then((all) => setAllTags(uniqSorted(all.flatMap((h) => h.tags ?? []))))
        .catch(() => {});
    }
    window.addEventListener(OPEN_HOST_TAGS_EVENT, handler);
    return () => window.removeEventListener(OPEN_HOST_TAGS_EVENT, handler);
  }, []);

  const addTag = React.useCallback(
    (raw: string) => {
      const v = raw.trim();
      setQuery("");
      if (!v) return;
      setTags((prev) => (prev.includes(v) ? prev : [...prev, v]));
    },
    [],
  );

  const removeTag = React.useCallback((t: string) => {
    setTags((prev) => prev.filter((x) => x !== t));
  }, []);

  // Suggestions: registry tags not already selected. The `cmdk` narrows these by
  // the typed query; the "create" item below covers brand-new tags.
  const suggestions = React.useMemo(
    () => allTags.filter((t) => !tags.includes(t)),
    [allTags, tags],
  );
  const trimmed = query.trim();
  const showCreate =
    trimmed.length > 0 && !tags.includes(trimmed) && !allTags.includes(trimmed);

  async function handleSave() {
    if (!hosts.length) return;
    setSubmitting(true);
    try {
      const current = new Set(tags);
      const original = new Set(originalTags);
      const added = tags.filter((t) => !original.has(t));
      const removed = originalTags.filter((t) => !current.has(t));

      await addHostTags(hosts, added);
      await removeHostTags(hosts, removed);

      window.dispatchEvent(
        new CustomEvent<HostsChangedDetail>(HOSTS_CHANGED_EVENT, {
          detail: { hostIds: hosts.map((h) => h.id), patch: { tags } },
        }),
      );
      setOpen(false);
    } finally {
      setSubmitting(false);
    }
  }

  const count = hosts.length;
  const dirty =
    tags.length !== originalTags.length ||
    tags.some((t) => !originalTags.includes(t));

  return (
    <Dialog open={open} onOpenChange={submitting ? () => {} : setOpen}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Edit tags</DialogTitle>
          <DialogDescription>
            {count === 1 ? (
              <span className="break-all font-mono">{hosts[0]?.name}</span>
            ) : (
              `${count} hosts`
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-1">
          {/* Current tags as removable chips. */}
          <div className="flex min-h-[2rem] flex-wrap gap-1.5 rounded-md border bg-muted/30 p-2">
            {tags.length === 0 ? (
              <span className="text-xs text-muted-foreground">No tags</span>
            ) : (
              tags.map((t) => (
                <span
                  key={t}
                  className="inline-flex items-center gap-1 rounded-full border border-border bg-background px-2 py-0.5 text-xs font-medium"
                >
                  {t}
                  <button
                    type="button"
                    aria-label={`Remove tag ${t}`}
                    title={`Remove ${t}`}
                    onClick={() => removeTag(t)}
                    disabled={submitting}
                    className="rounded-full p-0.5 text-muted-foreground hover:bg-foreground/10 hover:text-foreground"
                  >
                    <X className="h-3 w-3" aria-hidden="true" />
                  </button>
                </span>
              ))
            )}
          </div>

          {/* Autocomplete: existing tags + create-new. */}
          <Command className="rounded-md border">
            <CommandInput
              value={query}
              onValueChange={setQuery}
              onXClick={() => setQuery("")}
              placeholder="Add a tag..."
            />
            <CommandList className="max-h-40">
              {!showCreate && suggestions.length === 0 ? (
                <CommandEmpty>No tags to suggest</CommandEmpty>
              ) : null}
              <CommandGroup>
                {showCreate ? (
                  <CommandItem value={trimmed} onSelect={() => addTag(trimmed)}>
                    Create &quot;{trimmed}&quot;
                  </CommandItem>
                ) : null}
                {suggestions.map((t) => (
                  <CommandItem key={t} value={t} onSelect={() => addTag(t)}>
                    {t}
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
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
          <Button type="button" onClick={handleSave} disabled={submitting || !dirty}>
            {submitting ? "Saving…" : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
