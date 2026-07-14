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
import { HelpCircle } from "lucide-react";

import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@radix-ui/react-popover";

import { COMMAND_TOKENS } from "../lib/constants";

// The "?" badge cuesubmit shows next to Frame Spec / Command To Run.
// Same content (the dispatch-time token cheatsheet) for both because
// the tokens are valid in either field.
export function HelpPopover({ kind }: { kind: "frame-spec" | "command" }) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label="Field help"
          className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-input bg-background text-foreground/70 hover:text-foreground"
        >
          <HelpCircle className="h-4 w-4" />
        </button>
      </PopoverTrigger>
      <PopoverContent
        sideOffset={6}
        className="z-50 w-[min(28rem,calc(100vw-2rem))] rounded-md border bg-popover p-3 text-sm shadow-md text-popover-foreground"
      >
        {kind === "frame-spec" ? (
          <div className="space-y-1.5">
            <p className="font-medium">Frame Spec examples</p>
            <ul className="list-disc pl-5 text-xs text-foreground/80 space-y-0.5">
              <li><code>1-10</code> &mdash; frames 1 through 10</li>
              <li><code>1-100x2</code> &mdash; every other frame</li>
              <li><code>1-100y2</code> &mdash; every other frame dropped</li>
              <li><code>1-100:2</code> &mdash; interleaved</li>
              <li><code>1,3,5,7</code> &mdash; explicit list</li>
              <li><code>1-50,75-100</code> &mdash; comma-joined segments</li>
            </ul>
          </div>
        ) : (
          <div className="space-y-1.5">
            <p className="font-medium">Cuebot tokens (substituted per frame)</p>
            <ul className="text-xs text-foreground/80 space-y-0.5">
              {COMMAND_TOKENS.map((t) => (
                <li key={t.token} className="flex gap-2">
                  <code className="shrink-0 w-28">{t.token}</code>
                  <span>{t.description}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </PopoverContent>
    </Popover>
  );
}
