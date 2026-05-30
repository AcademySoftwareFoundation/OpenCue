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

"use client";

import * as React from "react";
import { ArrowDown, ArrowUp, Minus, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import type { LayerInput } from "../lib/schemas";

// Mirrors the "Submission Details" table at the bottom of the
// cuesubmit window: one row per layer with Layer Name, Job Type,
// Frames, Depend Type, plus the four control buttons (+, -, down, up).
// Click a row to load it into the Layer Info editor.

export function LayersTable({
  layers,
  selectedIndex,
  onSelect,
  onAdd,
  onRemove,
  onMoveUp,
  onMoveDown,
  disabled,
}: {
  layers: ReadonlyArray<LayerInput>;
  selectedIndex: number;
  onSelect: (i: number) => void;
  onAdd: () => void;
  onRemove: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  disabled?: boolean;
}) {
  const canMoveUp = selectedIndex > 0;
  const canMoveDown = selectedIndex >= 0 && selectedIndex < layers.length - 1;
  const canRemove = layers.length > 1 && selectedIndex >= 0;

  return (
    <div className="space-y-2">
      <div className="overflow-x-auto rounded-md border">
        <table className="w-full text-sm">
          <thead className="bg-foreground/5">
            <tr>
              <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide">
                Layer Name
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide">
                Job Type
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide">
                Frames
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide">
                Depend Type
              </th>
            </tr>
          </thead>
          <tbody>
            {layers.map((layer, i) => (
              <tr
                key={i}
                className={cn(
                  "border-t cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  i === selectedIndex
                    ? "bg-blue-500/15 text-foreground"
                    : "hover:bg-foreground/5",
                )}
                role="button"
                tabIndex={0}
                aria-pressed={i === selectedIndex}
                onClick={() => onSelect(i)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelect(i);
                  }
                }}
              >
                <td className="px-3 py-2 align-top font-medium">
                  {layer.name || <span className="text-foreground/40">(unnamed)</span>}
                </td>
                <td className="px-3 py-2 align-top">{layer.jobType}</td>
                <td className="px-3 py-2 align-top">{layer.frameSpec || ""}</td>
                <td className="px-3 py-2 align-top">{layer.dependencyType || ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onAdd}
          disabled={disabled}
          title="Add a new layer"
          aria-label="Add a new layer"
        >
          <Plus className="h-4 w-4" />
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onRemove}
          disabled={disabled || !canRemove}
          title="Remove the selected layer"
          aria-label="Remove the selected layer"
        >
          <Minus className="h-4 w-4" />
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onMoveDown}
          disabled={disabled || !canMoveDown}
          title="Move selected layer down"
          aria-label="Move selected layer down"
        >
          <ArrowDown className="h-4 w-4" />
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onMoveUp}
          disabled={disabled || !canMoveUp}
          title="Move selected layer up"
          aria-label="Move selected layer up"
        >
          <ArrowUp className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
