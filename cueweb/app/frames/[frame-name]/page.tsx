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


import { getFrame, getJobsForRegex } from "@/app/utils/get_utils";
import type { Job } from "@/app/jobs/columns";
import { handleError, toastSuccess } from "@/app/utils/notify_utils";
import { Breadcrumbs } from "@/components/ui/breadcrumbs";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import Editor, { Monaco } from "@monaco-editor/react";
import { ChevronDown, FileX } from "lucide-react";
import FormControl from "@mui/material/FormControl";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import { editor } from "monaco-editor";
import { useParams, useSearchParams } from "next/navigation";
import * as path from "path";
import React, { useEffect, useMemo, useRef, useState } from "react";
import { SimpleDataTable } from "../../../components/ui/simple-data-table";
import { FrameExtraDialogs } from "../../../components/ui/frame-extra-dialogs";
import { FramePreviewPanel } from "../../../components/ui/frame-preview-panel";
import { FrameLogSearch } from "../../../components/ui/frame-log-search";
import { Frame, frameColumns } from "../frame-columns";
import { SelectChangeEvent } from "@mui/material/Select";

/**
 * Best-effort extraction of the job name from a frame's log file path.
 * RQD writes log files as `<jobName>.<frameName>.rqlog`, so the prefix
 * up to the first `.` is the job name. Returns an empty string when
 * the path doesn't follow that convention.
 */
function jobNameFromLogPath(logPath: string): string {
  if (!logPath) return "";
  const filename = path.basename(logPath);
  const firstDot = filename.indexOf(".");
  return firstDot > 0 ? filename.slice(0, firstDot) : "";
}

// number of log lines for paginated infinite logs
const LOG_CHUNK_SIZE = process.env.NEXT_PUBLIC_LOG_CHUNK_SIZE ? parseInt(process.env.NEXT_PUBLIC_LOG_CHUNK_SIZE) : 100;

export default function FramePage() {
  const searchParams = useSearchParams();
  const routeParams = useParams<{ "frame-name": string }>();
  const [frameObject, setFrame] = React.useState<Frame | null>(null);
  // Parent job, resolved from the log path's job-name prefix so the frame
  // preview panel and the job-scoped frame actions work on this page too.
  const [job, setJob] = React.useState<Job | null>(null);
  const [totalNumLogLines, setTotalNumLogLines] = useState(-1);
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const frameId = searchParams.get("frameId") || "";
  const logDirPath = searchParams.get("frameLogDir") || "";
  const username = searchParams.get("username") || "";
  // Live-tail mode (opened via the frame menu's "Tail Log"): load only the
  // most recent lines, follow by default, and poll faster.
  const tailMode = searchParams.get("mode") === "tail";
  const TAIL_INITIAL_LINES = 200;

  const [curLogVersion, setCurLogVersion] = useState(path.basename(logDirPath));
  const [curLogPath, setCurLogPath] = useState(logDirPath)
  const [logVersions, setLogVersions] = useState<string[]>([]);

  const [initialDataLoaded, setInitialDataLoaded] = useState(false);
  const [numberOfLinesLoaded, setNumberOfLinesLoaded] = useState(LOG_CHUNK_SIZE);
  const [fetchingLogs, setFetchingLogs] = useState(false);
  const [scrollTrigger, setScrollTrigger] = useState(false);
  const [editorMounted, setEditorMounted] = useState(false);
  // Bumped on every editor content change (initial fill, infinite-scroll
  // loads, version switch) so the log search can re-run as lines stream in.
  const [logContentVersion, setLogContentVersion] = useState(0);
  // "Follow" tail mode: auto-scroll to the bottom as new lines arrive. Pauses
  // when the user scrolls up; the Jump-to-bottom button re-enables it.
  const [followMode, setFollowMode] = useState(false);
  const [atBottom, setAtBottom] = useState(true);
  const followRef = useRef(false);
  // Timestamp of the last programmatic scroll / content replace, so the scroll
  // listener can tell a setValue-induced scroll reset from a real user scroll.
  const programmaticScrollRef = useRef(0);
  useEffect(() => { followRef.current = followMode; }, [followMode]);
  // Monaco namespace (for Range/MouseTargetType), the absolute line-number
  // offset, and the per-line copy-glyph decoration ids.
  const monacoRef = useRef<Monaco | null>(null);
  const logDisplayStartRef = useRef(1);
  const copyGlyphDecorationsRef = useRef<string[]>([]);

  // Copy a single log line to the clipboard with a confirmation toast.
  const copyLineText = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toastSuccess("Line copied");
    } catch (error) {
      handleError(error, "Could not copy line");
    }
  };
  // Status of the log file currently selected in the version dropdown.
  // `loading` (initial), `ready` (we have lines), `empty` (the log file
  // exists but is empty), or `missing` (the log file could not be found).
  const [logStatus, setLogStatus] = useState<
    "loading" | "ready" | "empty" | "missing"
  >("loading");
  // To track log line display
  const [logDisplayStart, setLogDisplayStart] = useState(-1);
  const [logDisplayEnd, setLogDisplayEnd] = useState(-1);
  // Keep the absolute line-number offset in a ref for Monaco's lineNumbers fn.
  useEffect(() => { logDisplayStartRef.current = logDisplayStart > 0 ? logDisplayStart : 1; }, [logDisplayStart]);
  const defaultMessage =
    "Please wait while the logs are loading. \
    Important: Loading files with more than 1 million lines may take additional time.";

  const fetchData = async () => {
    const frameBody = { id: frameId };
    const frame = await getFrame(JSON.stringify(frameBody));
    setFrame(frame);
  };

  useEffect(() => {
    fetchData();
  }, []);  

  useEffect(() => {
      fetchInitialLogs();
  }, [editorMounted, frameObject, curLogVersion]);
  

  const fetchInitialLogs = async () => {
    try {
      const totalLines = await getLogLineCount();
      if (totalLines == -1) {
        setLogStatus("missing");
        return;
      }
      if (totalLines === 0) {
        setLogStatus("empty");
        setNumberOfLinesLoaded(0);
        return;
      }

      setLogStatus("ready");
      setTotalNumLogLines(totalLines);
      // Tail mode loads the last ~200 lines; normal view loads one chunk.
      const initialLines = tailMode ? TAIL_INITIAL_LINES : LOG_CHUNK_SIZE;
      let startline = totalLines < initialLines ? 1 : totalLines - initialLines + 1;
      let endline = totalLines;
      let newLogs = await fetchPaginatedLogs(startline, endline);
      setNumberOfLinesLoaded(endline - startline + 1);
      setLogDisplayStart(startline);
      setLogDisplayEnd(endline);

      if (newLogs) {
        updateTextInEditor(newLogs);
        setInitialDataLoaded(true);
      }

      scrollToBottomOfIDE();
    } catch (error) {
      console.error("Error fetching initial logs:", error);
    }
  };

  // scrollTrigger listener
  useEffect(() => {
    async function loadMoreLogsIfNeededGuard() {
      if (fetchingLogs) return;
      setFetchingLogs(true);
      if (initialDataLoaded) await loadMoreLogsIfNeeded();
      setFetchingLogs(false);
    }
    loadMoreLogsIfNeededGuard();
  }, [scrollTrigger]);

  // mount code editor
  const handleEditorDidMount = (editor: editor.IStandaloneCodeEditor, monaco: Monaco) => {
    editor.updateOptions({
      theme: "vs-dark",
      // Absolute file line numbers: Monaco line N maps to file line
      // (logDisplayStart + N - 1) since only a window of the log is loaded.
      lineNumbers: (n: number) => String(logDisplayStartRef.current + n - 1),
      glyphMargin: true,
      readOnly: true,
    });
    monacoRef.current = monaco;

    // Right-click / keyboard "Copy Line" (copies the line under the cursor).
    editor.addAction({
      id: "cueweb-copy-frame-log-line",
      label: "Copy Line",
      contextMenuGroupId: "9_cutcopypaste",
      contextMenuOrder: 1.5,
      run: (ed) => {
        const pos = ed.getPosition();
        const model = ed.getModel();
        if (pos && model) copyLineText(model.getLineContent(pos.lineNumber));
      },
    });

    // Click the hover copy glyph (or a line number) to copy that line.
    editor.onMouseDown((e) => {
      const t = e.target;
      if (
        (t.type === monaco.editor.MouseTargetType.GUTTER_GLYPH_MARGIN ||
          t.type === monaco.editor.MouseTargetType.GUTTER_LINE_NUMBERS) &&
        t.position
      ) {
        const model = editor.getModel();
        if (model) copyLineText(model.getLineContent(t.position.lineNumber));
      }
    });

    editorRef.current = editor;
    editorRef.current.onDidScrollChange(() => {
      const ed = editorRef.current;
      if (ed) {
        // Distance (px) from the very bottom of the scrollable log.
        const dist = ed.getScrollHeight() - ed.getScrollTop() - ed.getLayoutInfo().height;
        const near = dist <= 50;
        setAtBottom(near);
        // Pause follow only on a genuine user scroll-up - not the scroll reset
        // setValue causes, nor our own auto-scroll-to-bottom.
        const programmatic = Date.now() - programmaticScrollRef.current < 300;
        if (!near && !programmatic && followRef.current) setFollowMode(false);
      }
      setScrollTrigger((prev) => !prev);
    });
    setEditorMounted(true);
  };

  const scrollToBottomOfIDE = () => {
    let lineCount = editorRef.current?.getModel()?.getLineCount();
    if (lineCount) {
      editorRef.current?.revealLinesInCenterIfOutsideViewport(lineCount - 20, lineCount);
    }
  };

  // Hard scroll to the very bottom (used by follow mode + Jump to bottom).
  const scrollToVeryBottom = () => {
    const ed = editorRef.current;
    if (!ed) return;
    programmaticScrollRef.current = Date.now();
    ed.setScrollTop(ed.getScrollHeight());
  };

  function updateTextInEditor(text: string) {
    if (editorRef.current !== null) {
      // setValue resets the scroll position; mark it programmatic so the
      // scroll listener doesn't mistake it for a user scroll-up.
      programmaticScrollRef.current = Date.now();
      editorRef.current?.setValue(text);
      setLogContentVersion((v) => v + 1);
    }
  }

  // show the first lines of the log file when scroll to top button is clicked
  const handleShowTopLines = async () => {
    // In the event log file didn't exist yet and could possibly still not exist
    if (totalNumLogLines == -1) {
      fetchInitialLogs();
      return;
    }

    // fetch the first lines
    let newLogs = await fetchPaginatedLogs(1, LOG_CHUNK_SIZE);

    // update editor with new logs
    if (newLogs) {
      updateTextInEditor(newLogs);
      //update log indexing state variables
      setLogDisplayStart(1);
      setLogDisplayEnd(LOG_CHUNK_SIZE);
      setNumberOfLinesLoaded(LOG_CHUNK_SIZE);
    }
    editorRef.current?.revealLine(0);
  };

  // handles the logic to load more logs when the user scrolls up or down
  const loadMoreLogsIfNeeded = async () => {
    if (!initialDataLoaded || !editorRef.current) return;

    // Was waiting for logfile to populate
    if (numberOfLinesLoaded == 0) {
      fetchInitialLogs();
      return;
    }

    let visibleEndOfLine = editorRef.current.getVisibleRanges()[0].endLineNumber;
    let visibleStartOfLine = editorRef.current.getVisibleRanges()[0].startLineNumber;

    // case for loading older log messages
    if (visibleStartOfLine == 1) loadOlderLogMessages();

    // case for loading newer log messages
    if (visibleStartOfLine == visibleEndOfLine) loadNewerLogMessages();
  };

  const loadOlderLogMessages = async () => {
    // set viewport back by a few lines, this is needed for smoother transition
    editorRef.current?.revealLinesInCenterIfOutsideViewport(5, 10);

    // calculate start and end line for chunk - this is the line number in the log file
    const startLine = Math.max(1, logDisplayStart - LOG_CHUNK_SIZE);
    const endLine = logDisplayStart - 1;

    // exit early if we are scrolling from top or we are already showing the whole log
    // or no logs were loaded yet
    if (logDisplayStart == 1 || totalNumLogLines == numberOfLinesLoaded || startLine > endLine) return;

    // fetch new logs
    let newLogLines = await fetchPaginatedLogs(startLine, endLine);
    // update text in editor
    let prevLogs = editorRef.current?.getValue();
    updateTextInEditor(newLogLines + prevLogs);
    editorRef.current?.revealLinesInCenterIfOutsideViewport(LOG_CHUNK_SIZE, LOG_CHUNK_SIZE + 50);
    // update the number of log lines loaded
    const increment = endLine - startLine + 1;
    setNumberOfLinesLoaded(numberOfLinesLoaded + increment);
    // update the new start line
    setLogDisplayStart(startLine);
  };

  const loadNewerLogMessages = async () => {
    // check if total number of lines has grown aka there are new logs
    const newLogLineCount = await getLogLineCount();
    // return early if the num of lines in logfile has not changed
    // and we are displaying the end of the log already
    if (newLogLineCount == totalNumLogLines && logDisplayEnd == totalNumLogLines) return;

    // calculate new end line
    // get the number of new lines that have been added to the log and
    // get whichever is smaller - the difference or LOG_CHUNK_SIZE
    const newLinesCount = Math.min(newLogLineCount - logDisplayEnd, LOG_CHUNK_SIZE);
    let endLine = logDisplayEnd + newLinesCount;
    // update text in editor
    let newLogLines = await fetchPaginatedLogs(logDisplayEnd + 1, endLine);
    let prevLogs = editorRef.current?.getValue();
    updateTextInEditor(prevLogs + newLogLines);

    // update the number of log lines loaded in window
    setNumberOfLinesLoaded(numberOfLinesLoaded + newLinesCount);
    // update the number of lines in log file
    setTotalNumLogLines(newLogLineCount);
    // update the new end line
    setLogDisplayEnd(endLine);
  };

  // helper function to access next js endpoint for retrieving log lines
  const fetchPaginatedLogs = async (start: number, end: number) => {
    let res = await fetch(
      `/api/getlines?path=${encodeURIComponent(curLogPath)}&start=${start}&end=${end}`,
    );
    let json = await res.json();
    if (json.error) {
      handleError(json.error, "Could not load frame log lines");
      return;
    }
    return json.lines;
  };

  // helper function to access next js endpoint for counting lines
  const getLogLineCount = async () => {
    const numLines = fetch(`/api/countlines?path=${encodeURIComponent(curLogPath)}`);
    const data = await (await numLines).json();
    const totLines = data.count;
    return totLines;
  };

  // Follow tail mode: while on, poll for newer lines, append them, and stick to
  // the bottom. Re-subscribes when the relevant log state changes so the
  // appended-from closure stays fresh.
  useEffect(() => {
    if (!followMode || logStatus !== "ready") return;
    let cancelled = false;
    // Serialize ticks: a slow fetch must not overlap with the next interval
    // and append the same chunk twice from stale logDisplayEnd state.
    let inFlight = false;
    const tick = async () => {
      if (cancelled || !editorRef.current || inFlight) return;
      inFlight = true;
      try {
        await loadNewerLogMessages();
        if (!cancelled) scrollToVeryBottom();
      } finally {
        inFlight = false;
      }
    };
    tick();
    // Tail mode polls every 1s; otherwise a gentler 1.5s.
    const id = setInterval(tick, tailMode ? 1000 : 1500);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [followMode, logStatus, logDisplayEnd, totalNumLogLines, numberOfLinesLoaded, curLogPath, tailMode]);

  // Start following automatically in tail mode or for a running frame
  // (still pausable by scrolling up).
  useEffect(() => {
    if (tailMode || frameObject?.state === "RUNNING") {
      setFollowMode(true);
      setAtBottom(true);
    }
  }, [tailMode, frameObject?.state]);

  // Maintain a hover copy-glyph on each line. Decorate only the visible lines
  // (re-applied on scroll) rather than every loaded line, so the cost is
  // bounded by the viewport instead of O(total loaded lines) on each content
  // update - important for large / live-tailing logs.
  useEffect(() => {
    const ed = editorRef.current;
    const monaco = monacoRef.current;
    if (!ed || !monaco) return;

    const applyVisibleGlyphs = () => {
      const model = ed.getModel();
      if (!model) return;
      const lineCount = model.getLineCount();
      const decos = [];
      for (const range of ed.getVisibleRanges()) {
        const start = Math.max(1, range.startLineNumber);
        const end = Math.min(lineCount, range.endLineNumber);
        for (let i = start; i <= end; i++) {
          decos.push({
            range: new monaco.Range(i, 1, i, 1),
            options: {
              glyphMarginClassName: "cueweb-copy-line-glyph",
              glyphMarginHoverMessage: { value: "Copy line" },
            },
          });
        }
      }
      copyGlyphDecorationsRef.current = ed.deltaDecorations(copyGlyphDecorationsRef.current, decos);
    };

    applyVisibleGlyphs();
    // Re-decorate as new lines scroll into view.
    const scrollDisposable = ed.onDidScrollChange(applyVisibleGlyphs);
    return () => scrollDisposable.dispose();
  }, [logContentVersion, editorMounted]);

  // Handles updates when a different log version is selected
  const handleVersionChange = (e: SelectChangeEvent<string>) => {
    setCurLogVersion(e.target.value);
    setCurLogPath(path.dirname(logDirPath) + "/" + e.target.value);
    setInitialDataLoaded(false); // Reset data for new log version
    setLogStatus("loading"); // Re-render the editor on the next fetch
  };
  // Retreives new log versions when the logDirPath changes
  useEffect(() => {
    async function fetchLogVersions() {
      const res = await fetch(`/api/getlogversions?filename=${logDirPath}`);
      const json = await res.json();
      if (res.ok && json.versions) {
        setLogVersions(json.versions);
      } else {
        setLogVersions([]);
      }
    }
    fetchLogVersions();
  }, [logDirPath]);

  // Resolve the parent job from the log path's job-name prefix so the frame
  // preview panel (and job-scoped frame actions) have job context here.
  useEffect(() => {
    const name = jobNameFromLogPath(logDirPath);
    if (!name) {
      setJob(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const escaped = name.replace(/[-/\\^$*+?.()|[\]{}]/g, "\\$&");
        const matches = await getJobsForRegex(`^${escaped}$`, true);
        if (!cancelled) setJob(matches.length ? matches[0] : null);
      } catch {
        if (!cancelled) setJob(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [logDirPath]);

  const frameNameFromRoute = decodeURIComponent(routeParams?.["frame-name"] ?? "");
  const derivedJobName = jobNameFromLogPath(logDirPath);
  const breadcrumbItems = useMemo(() => {
    const items = [{ label: "Jobs", href: "/" }];
    if (derivedJobName) {
      items.push({ label: derivedJobName, href: "" });
    }
    if (frameObject?.layerName) {
      items.push({ label: frameObject.layerName, href: "" });
    }
    items.push({
      label: frameObject?.name || frameNameFromRoute || "Frame",
      href: "",
    });
    // Drop the `href: ""` placeholders so non-clickable segments render
    // as plain text (only "Jobs" stays a link until the job/layer detail
    // pages are implemented).
    return items.map((it) => (it.href === "" ? { label: it.label } : it));
  }, [derivedJobName, frameObject?.layerName, frameObject?.name, frameNameFromRoute]);

  return (
    <div className="container mx-auto py-10 max-w-[90%]">
      <Breadcrumbs items={breadcrumbItems} className="mb-4" />

      {/* Table for frame */}
      {frameObject != null ? (
        <>
          <span>{frameObject.name}</span>
          <SimpleDataTable data={[frameObject]} columns={frameColumns} showPagination={false} isFramesLogTable={true} username={username}></SimpleDataTable>
          {/* Frame right-click dialogs + preview panel. The parent job is
              resolved from the log path's job-name prefix, so job-scoped
              actions and the frame preview work here too. */}
          <FrameExtraDialogs job={job ?? undefined} />
          <FramePreviewPanel job={job ?? undefined} />
        </>
      ) : (
        <div />
      )}

      {/* Some white space between table and logs div */}
      <div className="mb-12" />
      
      {/* Dropdown to select different log versions */}
      <div className="my-4">
        <h3>Log versions</h3>
        <FormControl 
          size="small"
          sx={{
            backgroundColor: theme => theme.palette.background.default,
            color: theme => theme.palette.text.primary
          }}
        >
          <Select
            id={"log-version-select"}
            value={curLogVersion}
            label="log version"
            onChange={handleVersionChange}
          >
            {logVersions.map((version) => (
              <MenuItem key={version} value={version}>
                {version}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </div>

      {/* Logs for Frame */}
      <div className="relative my-2 mt-1 pt-1 overflow-hidden w-full rounded-xl border border-gray-400 bg-black">
        <div className="flex items-center space-x-3">
          <Button
            size="xs"
            className="ml-4 text-xs font-medium text-white bg-blue-700 hover:bg-blue-800"
            onClick={handleShowTopLines}
          >
            Scroll from Top
          </Button>
          <Button
            size="xs"
            aria-pressed={followMode}
            title="Auto-scroll to the bottom as new lines arrive"
            className={`text-xs font-medium ${
              followMode
                ? "bg-green-700 text-white hover:bg-green-800"
                : "bg-gray-700 text-white hover:bg-gray-600"
            }`}
            onClick={() => {
              const next = !followMode;
              setFollowMode(next);
              if (next) {
                setAtBottom(true);
                scrollToVeryBottom();
              }
            }}
          >
            {followMode ? "Following" : "Follow"}
          </Button>
          <span className="text-white ml-4">
            {totalNumLogLines && totalNumLogLines != -1 ? totalNumLogLines.toLocaleString() + " lines of logs" : ""}
          </span>
        </div>
        {logStatus !== "missing" && logStatus !== "empty" ? (
          <FrameLogSearch editorRef={editorRef} contentVersion={logContentVersion} />
        ) : null}
        <div className="mt-1">
          {logStatus === "missing" || logStatus === "empty" ? (
            <div
              className="flex items-center justify-center bg-black text-white"
              style={{ height: "50vh" }}
            >
              <EmptyState
                icon={<FileX className="h-6 w-6" aria-hidden="true" />}
                title={
                  logStatus === "missing"
                    ? "Log file not found"
                    : "No log output yet"
                }
                description={
                  logStatus === "missing"
                    ? "Cuebot could not locate the log file for this frame. The frame may not have started yet, or the log has been moved or purged."
                    : "This frame has no log output yet. Once the frame starts producing lines they will appear here automatically."
                }
              />
            </div>
          ) : logStatus === "loading" && !initialDataLoaded ? (
            // Reserve the editor's 50vh footprint and show shimmer
            // skeleton bars so the panel does not shift when Monaco
            // mounts and the real log content streams in.
            <div
              className="flex flex-col gap-2 bg-black p-6"
              style={{ height: "50vh" }}
              aria-busy="true"
            >
              <Skeleton className="h-6 w-3/5" />
              <Skeleton className="h-4 w-2/5" />
              <div className="mt-3 space-y-2">
                {Array.from({ length: 12 }).map((_, i) => (
                  <Skeleton
                    key={`log-skeleton-${i}`}
                    className={`h-3 ${
                      i % 5 === 0
                        ? "w-3/4"
                        : i % 3 === 0
                          ? "w-1/2"
                          : "w-11/12"
                    }`}
                  />
                ))}
              </div>
            </div>
          ) : (
            <Editor
              theme="my-theme"
              height="50vh"
              defaultLanguage="plaintext"
              defaultValue={defaultMessage.replaceAll("  ", "")}
              onMount={handleEditorDidMount}
            />
          )}
        </div>

        {/* Floating jump-to-bottom: shown when scrolled up off the tail.
            Clicking it re-enables follow. */}
        {logStatus === "ready" && !atBottom ? (
          <button
            type="button"
            onClick={() => {
              scrollToVeryBottom();
              setAtBottom(true);
              setFollowMode(true);
            }}
            className="absolute bottom-4 right-6 z-10 inline-flex items-center gap-1 rounded-full border border-gray-500 bg-gray-800/90 px-3 py-1.5 text-xs font-medium text-white shadow-lg hover:bg-gray-700"
          >
            <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
            Jump to bottom
          </button>
        ) : null}
      </div>
    </div>
  );
}
