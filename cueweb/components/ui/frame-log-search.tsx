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

import debounce from "lodash/debounce";
import type { editor } from "monaco-editor";
import { AlertTriangle, ChevronDown, ChevronUp, Search, X } from "lucide-react";

// Fixed pattern for the "Next error" jumper: a case-insensitive regex matching
// the common log failure markers.
const ERROR_PATTERN = "error|exception|traceback";

// Search box for the frame log viewer. The log lives in a Monaco editor,
// so this drives Monaco's findMatches + decorations rather than wrapping text
// in <mark>: matches are highlighted, the current match is emphasized and
// scrolled into view, Enter / Shift+Enter cycle, and an n/total counter shows.
// Case-insensitive by default with an optional regex toggle (JS-ish syntax).

interface FrameLogSearchProps {
  editorRef: React.MutableRefObject<editor.IStandaloneCodeEditor | null>;
  // Bumps whenever the editor mounts or its content changes, so we re-run the
  // search as more log lines stream in.
  contentVersion: unknown;
}

export function FrameLogSearch({ editorRef, contentVersion }: FrameLogSearchProps) {
  const [query, setQuery] = React.useState("");
  const [debouncedQuery, setDebouncedQuery] = React.useState("");
  const [caseSensitive, setCaseSensitive] = React.useState(false);
  const [useRegex, setUseRegex] = React.useState(false);
  const [index, setIndex] = React.useState(0);
  const [total, setTotal] = React.useState(0);
  const [error, setError] = React.useState<string | null>(null);

  const matchesRef = React.useRef<editor.FindMatch[]>([]);
  const decorationIdsRef = React.useRef<string[]>([]);

  // Debounce the typed query into the value that actually drives the search.
  const debounceQuery = React.useMemo(
    () => debounce((v: string) => setDebouncedQuery(v), 200),
    [],
  );
  React.useEffect(() => () => debounceQuery.cancel(), [debounceQuery]);

  const clearDecorations = React.useCallback(() => {
    const ed = editorRef.current;
    if (ed) decorationIdsRef.current = ed.deltaDecorations(decorationIdsRef.current, []);
  }, [editorRef]);

  const applyDecorations = React.useCallback(
    (matches: editor.FindMatch[], current: number) => {
      const ed = editorRef.current;
      if (!ed) return;
      const decos = matches.map((m, i) => ({
        range: m.range,
        options: {
          inlineClassName: i === current ? "cueweb-log-match-current" : "cueweb-log-match",
        },
      }));
      decorationIdsRef.current = ed.deltaDecorations(decorationIdsRef.current, decos);
      const match = matches[current];
      if (match) {
        ed.revealRangeInCenterIfOutsideViewport(match.range);
        ed.setSelection(match.range);
      }
    },
    [editorRef],
  );

  // Recompute matches whenever the query, toggles, or editor content change.
  React.useEffect(() => {
    const ed = editorRef.current;
    const model = ed?.getModel();
    if (!ed || !model || !debouncedQuery) {
      matchesRef.current = [];
      setTotal(0);
      setIndex(0);
      setError(null);
      clearDecorations();
      return;
    }
    try {
      // findMatches(searchString, searchScope, isRegex, matchCase,
      //             wordSeparators, captureMatches)
      const matches = model.findMatches(debouncedQuery, false, useRegex, caseSensitive, null, false);
      matchesRef.current = matches;
      setError(null);
      setTotal(matches.length);
      const next = matches.length === 0 ? 0 : Math.min(index, matches.length - 1);
      setIndex(next);
      applyDecorations(matches, next);
    } catch (e) {
      // Invalid regex - surface a hint and clear highlights.
      matchesRef.current = [];
      setTotal(0);
      setError(useRegex ? "Invalid regex" : "Search error");
      clearDecorations();
    }
    // index intentionally excluded: navigation calls applyDecorations directly.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedQuery, caseSensitive, useRegex, contentVersion, editorRef, applyDecorations, clearDecorations]);

  // Clear highlights when the component unmounts.
  React.useEffect(() => () => clearDecorations(), [clearDecorations]);

  const go = React.useCallback(
    (delta: number) => {
      const matches = matchesRef.current;
      if (matches.length === 0) return;
      const next = (index + delta + matches.length) % matches.length;
      setIndex(next);
      applyDecorations(matches, next);
    },
    [index, applyDecorations],
  );

  // "Next error" jumper. Reuses the same matches/decorations/counter pipeline as
  // the text search by driving a fixed case-insensitive error regex. The first
  // press activates it (and reveals the first match); subsequent presses cycle
  // through the matches via the same `go()` used by the next/prev buttons.
  const inErrorMode = query === ERROR_PATTERN && useRegex && !caseSensitive;
  const jumpToNextError = React.useCallback(() => {
    if (inErrorMode) {
      go(1);
      return;
    }
    setIndex(0);
    setCaseSensitive(false);
    setUseRegex(true);
    setQuery(ERROR_PATTERN);
    // Bypass the debounce for the fixed query so the jump is immediate.
    setDebouncedQuery(ERROR_PATTERN);
  }, [inErrorMode, go]);

  const onChange = (v: string) => {
    setQuery(v);
    debounceQuery(v);
  };

  const toggleBtn = "h-7 rounded px-2 text-xs font-medium border transition-colors";

  return (
    <div className="mx-4 my-1 flex flex-wrap items-center gap-2">
      <div className="relative">
        <Search className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" aria-hidden="true" />
        <input
          type="text"
          value={query}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              go(e.shiftKey ? -1 : 1);
            }
          }}
          placeholder="Search log..."
          aria-label="Search log"
          className="h-7 w-56 rounded border border-gray-500 bg-black pl-7 pr-7 text-xs text-white placeholder:text-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        {query ? (
          <button
            type="button"
            aria-label="Clear search"
            onClick={() => onChange("")}
            className="absolute right-1.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        ) : null}
      </div>

      <span className="min-w-[3.5rem] text-xs tabular-nums text-gray-300">
        {error ? <span className="text-red-400">{error}</span> : `${total === 0 ? 0 : index + 1}/${total}`}
      </span>

      <button
        type="button"
        aria-label="Previous match"
        title="Previous match (Shift+Enter)"
        onClick={() => go(-1)}
        disabled={total === 0}
        className={`${toggleBtn} border-gray-500 text-white hover:bg-gray-800 disabled:opacity-40`}
      >
        <ChevronUp className="h-4 w-4" aria-hidden="true" />
      </button>
      <button
        type="button"
        aria-label="Next match"
        title="Next match (Enter)"
        onClick={() => go(1)}
        disabled={total === 0}
        className={`${toggleBtn} border-gray-500 text-white hover:bg-gray-800 disabled:opacity-40`}
      >
        <ChevronDown className="h-4 w-4" aria-hidden="true" />
      </button>

      <button
        type="button"
        aria-pressed={caseSensitive}
        title="Match case"
        onClick={() => setCaseSensitive((v) => !v)}
        className={`${toggleBtn} ${caseSensitive ? "border-blue-500 bg-blue-700 text-white" : "border-gray-500 text-gray-300 hover:bg-gray-800"}`}
      >
        Aa
      </button>
      <button
        type="button"
        aria-pressed={useRegex}
        title="Use regular expression"
        onClick={() => setUseRegex((v) => !v)}
        className={`${toggleBtn} font-mono ${useRegex ? "border-blue-500 bg-blue-700 text-white" : "border-gray-500 text-gray-300 hover:bg-gray-800"}`}
      >
        .*
      </button>

      <button
        type="button"
        aria-pressed={inErrorMode}
        title="Jump to next error (error / exception / traceback)"
        aria-label="Jump to next error"
        onClick={jumpToNextError}
        className={`${toggleBtn} flex items-center gap-1 ${inErrorMode ? "border-amber-500 bg-amber-700 text-white" : "border-gray-500 text-gray-300 hover:bg-gray-800"}`}
      >
        <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />
        Next error
      </button>
    </div>
  );
}
