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

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getFrameLogLines,
  getFrameLogVersions,
  LokiLogVersion,
} from "@/lib/loki";
import Editor, { Monaco } from "@monaco-editor/react";
import FormControl from "@mui/material/FormControl";
import MenuItem from "@mui/material/MenuItem";
import Select, { SelectChangeEvent } from "@mui/material/Select";
import { FileX } from "lucide-react";
import { editor } from "monaco-editor";
import React, { useEffect, useRef, useState } from "react";
import { handleError } from "@/app/utils/notify_utils";

interface LokiLogViewProps {
  frameId: string;
  // Frame start time in unix seconds; used to bound Loki queries. Optional
  // because the frame object loads asynchronously on the parent page.
  startTime?: number;
}

// Status of the log currently selected in the version dropdown, mirroring the
// file-based viewer: `loading` (initial), `ready` (we have lines), `empty`
// (the attempt exists but produced no lines), or `missing` (no log streams
// for this frame in Loki at all).
type LokiLogStatus = "loading" | "ready" | "empty" | "missing";

/**
 * Loki-backed frame log viewer. Rendered in place of the file-based viewer
 * when `NEXT_PUBLIC_LOKI_URL` is configured. The "log versions" dropdown lists
 * each frame attempt (Loki `session_start_time`), newest first, and selecting
 * one loads its lines into the same read-only Monaco editor the file viewer
 * uses so the two backends look and feel identical.
 */
export default function LokiLogView({ frameId, startTime }: LokiLogViewProps) {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const [editorMounted, setEditorMounted] = useState(false);
  const [versions, setVersions] = useState<LokiLogVersion[]>([]);
  const [curSession, setCurSession] = useState("");
  const [logStatus, setLogStatus] = useState<LokiLogStatus>("loading");
  const [lineCount, setLineCount] = useState(0);
  // Bumped by the Refresh button to force the line-fetch effect to re-run for
  // the currently selected session.
  const [refreshKey, setRefreshKey] = useState(0);

  const defaultMessage = "Please wait while the logs are loading from Loki.";

  // Fetch the list of attempts (log versions) for this frame and default to
  // the most recent one. Independent of the editor so it can resolve the
  // missing/ready state before Monaco mounts (the editor only renders once we
  // know there is something to show).
  useEffect(() => {
    let cancelled = false;
    async function fetchVersions() {
      try {
        const found = await getFrameLogVersions(frameId, startTime);
        if (cancelled) return;
        setVersions(found);
        if (found.length === 0) {
          setLogStatus("missing");
          setCurSession("");
        } else {
          // Newest attempt is first (getFrameLogVersions sorts desc). Flip to
          // `ready` so the editor mounts; the line-fetch effect then loads it.
          setCurSession(found[0].sessionStartTime);
          setLogStatus("ready");
        }
      } catch (error) {
        if (cancelled) return;
        handleError(`${error}`, "Could not load frame logs from Loki");
        setLogStatus("missing");
      }
    }
    if (frameId) fetchVersions();
    return () => {
      cancelled = true;
    };
  }, [frameId, startTime]);

  // Load the selected attempt's lines once both the editor is mounted and a
  // session is chosen. We deliberately do NOT flip back to `loading` here: the
  // editor must stay mounted (it only renders while status is `ready`), so the
  // previous content simply stays put until the new lines arrive.
  useEffect(() => {
    let cancelled = false;
    async function fetchLines() {
      if (!curSession || !editorMounted) return;
      try {
        const text = await getFrameLogLines(frameId, curSession, startTime);
        if (cancelled) return;
        if (!text) {
          setLineCount(0);
          setLogStatus("empty");
          editorRef.current?.setValue("");
          return;
        }
        editorRef.current?.setValue(text);
        setLineCount(text.split("\n").length);
        setLogStatus("ready");
        scrollToBottom();
      } catch (error) {
        if (cancelled) return;
        handleError(`${error}`, "Could not load frame logs from Loki");
      }
    }
    fetchLines();
    return () => {
      cancelled = true;
    };
  }, [curSession, editorMounted, frameId, startTime, refreshKey]);

  const handleEditorDidMount = (
    ed: editor.IStandaloneCodeEditor,
    _monaco: Monaco,
  ) => {
    ed.updateOptions({ theme: "vs-dark", lineNumbers: "off", readOnly: true });
    editorRef.current = ed;
    setEditorMounted(true);
  };

  const scrollToBottom = () => {
    const count = editorRef.current?.getModel()?.getLineCount();
    if (count) {
      editorRef.current?.revealLinesInCenterIfOutsideViewport(count - 20, count);
    }
  };

  const handleVersionChange = (e: SelectChangeEvent<string>) => {
    setCurSession(e.target.value);
  };

  const handleRefresh = () => {
    // Re-run the line-fetch effect for the current session.
    setRefreshKey((k) => k + 1);
  };

  // The editor mounts as soon as there is at least one log version to show and
  // stays mounted across loading/empty states. Loading skeleton and empty/
  // missing notices render as an overlay on top of it (rather than swapping it
  // out) so the editor ref is never invalidated mid-fetch.
  const showEditor = curSession !== "" || logStatus === "ready";
  const overlay =
    logStatus === "missing" || logStatus === "empty" ? (
      <EmptyState
        icon={<FileX className="h-6 w-6" aria-hidden="true" />}
        title={logStatus === "missing" ? "No logs in Loki" : "No log output yet"}
        description={
          logStatus === "missing"
            ? "Loki has no log streams for this frame. The frame may not have started yet, or its logs were not shipped to Loki."
            : "This frame attempt has no log output yet. Refresh once the frame starts producing lines."
        }
      />
    ) : logStatus === "loading" ? (
      <div className="flex flex-col gap-2 w-full p-6" aria-busy="true">
        <Skeleton className="h-6 w-3/5" />
        <Skeleton className="h-4 w-2/5" />
        <div className="mt-3 space-y-2">
          {Array.from({ length: 12 }).map((_, i) => (
            <Skeleton
              key={`loki-log-skeleton-${i}`}
              className={`h-3 ${
                i % 5 === 0 ? "w-3/4" : i % 3 === 0 ? "w-1/2" : "w-11/12"
              }`}
            />
          ))}
        </div>
      </div>
    ) : null;

  return (
    <>
      {/* Dropdown to select different log versions (frame attempts). */}
      <div className="my-4">
        <h3>Log versions</h3>
        <FormControl
          size="small"
          sx={{
            backgroundColor: (theme) => theme.palette.background.default,
            color: (theme) => theme.palette.text.primary,
          }}
        >
          <Select
            id="loki-log-version-select"
            value={curSession}
            label="log version"
            onChange={handleVersionChange}
            displayEmpty
          >
            {versions.length === 0 ? (
              <MenuItem value="" disabled>
                No log versions
              </MenuItem>
            ) : (
              versions.map((v) => (
                <MenuItem key={v.sessionStartTime} value={v.sessionStartTime}>
                  {v.label}
                </MenuItem>
              ))
            )}
          </Select>
        </FormControl>
      </div>

      {/* Logs for Frame (Loki). */}
      <div className="my-2 mt-1 pt-1 overflow-hidden w-full rounded-xl border border-gray-400 bg-black">
        <div className="space-x-3">
          <Button
            size="xs"
            className="ml-4 text-xs font-medium text-white bg-blue-700 hover:bg-blue-800"
            onClick={handleRefresh}
          >
            Refresh
          </Button>
          <span className="text-white ml-4">
            {logStatus === "ready" && lineCount > 0
              ? `${lineCount.toLocaleString()} lines of logs (Loki)`
              : ""}
          </span>
        </div>
        <div className="mt-1 relative" style={{ height: "50vh" }}>
          {showEditor && (
            <Editor
              theme="my-theme"
              height="50vh"
              defaultLanguage="plaintext"
              defaultValue={defaultMessage}
              onMount={handleEditorDidMount}
            />
          )}
          {overlay && (
            <div className="absolute inset-0 flex items-center justify-center bg-black text-white">
              {overlay}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
