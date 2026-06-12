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
import type { Layer } from "@/app/layers/layer-columns";
import { editLayerProperties } from "@/app/utils/action_utils";
import { getJobForLayer, getLayersForJob } from "@/app/utils/get_utils";
import { formatKbToGbInput, parseMemoryToKb } from "@/app/utils/layers_frames_utils";
import {
  LAYERS_CHANGED_EVENT,
  OPEN_LAYER_PROPERTIES_EVENT,
  type LayersChangedDetail,
  type OpenLayerPropertiesDetail,
} from "@/components/ui/layer-action-events";

/**
 * Layer property editor dialog (#2291). Mirrors CueGUI's LayerDialog
 * (Resource Options + Tags), scoped to the three fields the issue calls for:
 * min memory, min cores and tags. Mounted once at the page level and opened
 * by a `cueweb:open-layer-properties` CustomEvent from the layer row context
 * menu (editLayerPropertiesGivenRow).
 *
 * Memory is entered with a unit suffix (a bare number is GB, matching
 * CueGUI's GB spinner) and validated via parseMemoryToKb. Tags render as
 * removable chips with a cmdk autocomplete seeded from the other layers in
 * the same job (the closest CueWeb analog to CueGUI's show-wide allowed
 * tags). On Save each field is diffed against the layer's current value and
 * only the changes are sent (SetMinMemory / SetMinCores / SetTags); a
 * `cueweb:layers-changed` event then patches the table optimistically.
 */

const uniqSorted = (xs: string[]): string[] => Array.from(new Set(xs)).sort();

export function EditLayerPropertiesDialog() {
  const [open, setOpen] = React.useState(false);
  const [layer, setLayer] = React.useState<Layer | null>(null);

  // Original values, captured on open so we can diff on Save.
  const [originalMemoryKb, setOriginalMemoryKb] = React.useState(0);
  const [originalCores, setOriginalCores] = React.useState(0);
  const [originalTags, setOriginalTags] = React.useState<string[]>([]);

  // Working state.
  const [memoryInput, setMemoryInput] = React.useState("");
  const [cores, setCores] = React.useState(0);
  const [tags, setTags] = React.useState<string[]>([]);
  const [allTags, setAllTags] = React.useState<string[]>([]);
  const [query, setQuery] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      const detail = (e as CustomEvent<OpenLayerPropertiesDetail>).detail;
      if (!detail?.layer) return;
      const l = detail.layer;
      const memKb = Number.parseInt(l.minMemory);
      const startMemKb = Number.isFinite(memKb) ? memKb : 0;
      const startCores = Number.isFinite(Number(l.minCores)) ? Number(l.minCores) : 0;
      const startTags = uniqSorted(l.tags ?? []);

      setLayer(l);
      setOriginalMemoryKb(startMemKb);
      setOriginalCores(startCores);
      setOriginalTags(startTags);
      setMemoryInput(formatKbToGbInput(startMemKb));
      setCores(startCores);
      setTags(startTags);
      setAllTags(startTags);
      setQuery("");
      setSubmitting(false);
      setOpen(true);

      // Seed tag autocomplete from the other layers in this job. Best-effort:
      // if the lookup fails we still have this layer's own tags as
      // suggestions (CueGUI offers a show-wide ALLOWED_TAGS list; CueWeb has
      // no equivalent registry endpoint, so sibling layers are the closest
      // source of "tags from the existing show").
      getJobForLayer(l)
        .then((job) => (job ? getLayersForJob(job) : []))
        .then((layers) => setAllTags(uniqSorted(layers.flatMap((x) => x.tags ?? []))))
        .catch(() => {});
    }
    window.addEventListener(OPEN_LAYER_PROPERTIES_EVENT, handler);
    return () => window.removeEventListener(OPEN_LAYER_PROPERTIES_EVENT, handler);
  }, []);

  const addTag = React.useCallback((raw: string) => {
    const v = raw.trim();
    setQuery("");
    if (!v) return;
    setTags((prev) => (prev.includes(v) ? prev : [...prev, v]));
  }, []);

  const removeTag = React.useCallback((t: string) => {
    setTags((prev) => prev.filter((x) => x !== t));
  }, []);

  const suggestions = React.useMemo(
    () => allTags.filter((t) => !tags.includes(t)),
    [allTags, tags],
  );
  const trimmedQuery = query.trim();
  const showCreate =
    trimmedQuery.length > 0 && !tags.includes(trimmedQuery) && !allTags.includes(trimmedQuery);

  // Validation. Memory must parse to a valid KB amount; cores must be a
  // finite, non-negative number; at least one tag is required (CueGUI's
  // LayerTagsWidget.verify enforces the same).
  const memoryKb = parseMemoryToKb(memoryInput);
  const memoryValid = memoryKb !== null;
  const coresValid = Number.isFinite(cores) && cores >= 0;
  const tagsValid = tags.length > 0;

  // Per-field dirty flags so Save only POSTs what changed.
  const memoryDirty = memoryValid && memoryKb !== originalMemoryKb;
  const coresDirty = coresValid && cores !== originalCores;
  const tagsDirty =
    tags.length !== originalTags.length || tags.some((t) => !originalTags.includes(t));

  const dirty = memoryDirty || coresDirty || tagsDirty;
  const valid = memoryValid && coresValid && tagsValid;

  async function handleSave() {
    if (!layer || !valid || !dirty) return;
    setSubmitting(true);
    try {
      const changes: { minMemory?: number; minCores?: number; tags?: string[] } = {};
      if (memoryDirty && memoryKb !== null) changes.minMemory = memoryKb;
      if (coresDirty) changes.minCores = cores;
      if (tagsDirty) changes.tags = tags;

      const ok = await editLayerProperties(layer, changes);
      // Only patch the row optimistically when the action actually
      // succeeded; editLayerProperties surfaces failures via a toast and
      // returns false, so a rejected change leaves the table at its true
      // value instead of flickering.
      if (ok) {
        const patch: LayersChangedDetail["patch"] = {};
        if (changes.minMemory !== undefined) patch.minMemory = String(changes.minMemory);
        if (changes.minCores !== undefined) patch.minCores = changes.minCores;
        if (changes.tags !== undefined) patch.tags = changes.tags;
        window.dispatchEvent(
          new CustomEvent<LayersChangedDetail>(LAYERS_CHANGED_EVENT, {
            detail: { layerIds: [layer.id], patch },
          }),
        );
        setOpen(false);
      }
    } catch (error) {
      console.error("Failed to update layer properties:", error);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={submitting ? () => {} : setOpen}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Layer Properties</DialogTitle>
          <DialogDescription>
            {layer ? (
              <span className="font-mono break-all">{layer.name}</span>
            ) : (
              "Edit the layer's resource requirements."
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Min memory + min cores. */}
          <div className="flex items-start gap-4">
            <label className="flex flex-1 flex-col gap-1 text-sm">
              <span className="text-foreground/70">Min Memory</span>
              <input
                type="text"
                inputMode="decimal"
                value={memoryInput}
                onChange={(e) => setMemoryInput(e.target.value)}
                disabled={submitting}
                aria-label="Minimum memory"
                placeholder="e.g. 4GB"
                className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm font-mono"
              />
              <span className="text-xs text-muted-foreground">
                Units: K/M/G/T (a plain number is GB).
              </span>
              {!memoryValid && memoryInput.trim() !== "" && (
                <span className="text-xs text-destructive">
                  Enter a positive amount with an optional K/M/G/T unit.
                </span>
              )}
            </label>
            <label className="flex flex-1 flex-col gap-1 text-sm">
              <span className="text-foreground/70">Min Cores</span>
              <input
                type="number"
                min={0}
                max={50000}
                step={0.1}
                value={cores}
                onChange={(e) => setCores(Number(e.target.value))}
                disabled={submitting}
                aria-label="Minimum cores"
                className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm font-mono"
              />
              <span className="text-xs text-muted-foreground">Whole cores (1 = one core).</span>
              {!coresValid && (
                <span className="text-xs text-destructive">Cores must be 0 or greater.</span>
              )}
            </label>
          </div>

          {/* Tags: removable chips + autocomplete. */}
          <div className="space-y-2">
            <span className="text-sm text-foreground/70">Tags</span>
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
                    <CommandItem value={trimmedQuery} onSelect={() => addTag(trimmedQuery)}>
                      Create &quot;{trimmedQuery}&quot;
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
            {!tagsValid && (
              <span className="text-xs text-destructive">
                A layer must have at least one tag. Changing tags may stop the layer from running.
              </span>
            )}
          </div>
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
            onClick={handleSave}
            disabled={submitting || !valid || !dirty}
          >
            {submitting ? "Saving…" : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
