"use client";

import { getFrame } from "@/app/utils/utils";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import Editor, { Monaco } from "@monaco-editor/react";
import { editor } from "monaco-editor";
import { useSearchParams } from "next/navigation";
import React, { useEffect, useRef, useState } from "react";
import CueWebIcon from "../../../components/ui/cuewebicon";
import { SimpleDataTable } from "../../../components/ui/simple-data-table";
import { Frame, frameColumns } from "../frame-columns";

// number of log lines for paginated infinite logs
const LOG_CHUNK_SIZE = process.env.NEXT_PUBLIC_LOG_CHUNK_SIZE ? parseInt(process.env.NEXT_PUBLIC_LOG_CHUNK_SIZE) : 100;

export default function FramePage() {
  const searchParams = useSearchParams();
  const [frameObject, setFrame] = React.useState<Frame | null>(null);
  const [totalNumLogLines, setTotalNumLogLines] = useState(-1);
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const frameId = searchParams.get("frameId");
  const logDirPath = searchParams.get("frameLogDir");

  const [initialDataLoaded, setInitialDataLoaded] = useState(false);
  const [numberOfLinesLoaded, setNumberOfLinesLoaded] = useState(LOG_CHUNK_SIZE);
  const [fetchingLogs, setFetchingLogs] = useState(false);
  const [scrollTrigger, setScrollTrigger] = useState(false);
  const [editorMounted, setEditorMounted] = useState(false);
  // To track log line display
  const [logDisplayStart, setLogDisplayStart] = useState(-1);
  const [logDisplayEnd, setLogDisplayEnd] = useState(-1);
  const defaultMessage =
    "Please wait while the logs are loading. \
    Important: Loading files with more than 1 million lines may take additional time.";

  const fetchData = async () => {
    const frameBody = { id: frameId };
    const frame = await getFrame(JSON.stringify(frameBody));
    setFrame(frame);
  };

  // on page load: get the frame object
  useEffect(() => {
    fetchData();
  }, []);

  // retrieve and display the logs once the editor has mounted or frame object has loaded
  useEffect(() => {
    fetchInitialLogs();
  }, [frameObject, editorMounted]);

  const fetchInitialLogs = async () => {
    const totalLines = await getLogLineCount();
    // exit early if log files are not generated -
    // either log file doesn't exist or no logs written out yet
    if (totalLines == -1) {
      updateTextInEditor("Could not find log file for the frame. \n___");
      return;
    }

    if (totalLines == 0) {
      updateTextInEditor("No log output to display yet. \n");
      setNumberOfLinesLoaded(0);
    }

    // set total number of lines currently in the logfile
    setTotalNumLogLines(totalLines);

    let startline = totalLines < LOG_CHUNK_SIZE ? 1 : totalLines - LOG_CHUNK_SIZE + 1;
    let endline = totalLines;
    let newLogs = await fetchPaginatedLogs(startline, endline);
    setNumberOfLinesLoaded(endline - startline + 1);
    setLogDisplayStart(startline);
    setLogDisplayEnd(endline);

    // update editor
    if (newLogs) {
      updateTextInEditor(newLogs);
      setInitialDataLoaded(true);
    }

    scrollToBottomOfIDE();
  };

  // the `loadMoreLogsIfNeeded` function listens to the `scrollTrigger` variable change to activate
  const scrollTriggerHandler = () => {
    setScrollTrigger((prev) => !prev);
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
      lineNumbers: "off",
      readOnly: true,
    });

    editorRef.current = editor;
    editorRef.current.onDidScrollChange(scrollTriggerHandler);
    setEditorMounted(true);
  };

  const scrollToBottomOfIDE = () => {
    let lineCount = editorRef.current?.getModel()?.getLineCount();
    if (lineCount) {
      editorRef.current?.revealLinesInCenterIfOutsideViewport(lineCount - 20, lineCount);
    }
  };

  function updateTextInEditor(text: string) {
    if (editorRef.current !== null) {
      editorRef.current?.setValue(text);
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
    let res = await fetch(`/api/getlines?path=${logDirPath}&start=${start}&end=${end}`);
    let json = await res.json();
    if (json.error) {
      alert("error");
      return;
    }
    return json.lines;
  };

  // helper function to access next js endpoint for counting lines
  const getLogLineCount = async () => {
    const numLines = fetch(`/api/countlines?path=${logDirPath}`);
    const data = await (await numLines).json();
    const totLines = data.count;
    return totLines;
  };

  return (
    <div className="container mx-auto py-10 max-w-[90%]">
      {/* Cueweb icon, Mode Toggle */}
      <div className="flex items-center justify-between px-1 py-4">
        <CueWebIcon />
        <ThemeToggle />
      </div>

      {/* Table for frame */}
      {frameObject != null ? (
        <>
          <span>{frameObject.name}</span>
          <SimpleDataTable data={[frameObject]} columns={frameColumns} showPagination={false}></SimpleDataTable>
        </>
      ) : (
        <div />
      )}

      {/* Some white space between table and logs div */}
      <div className="mb-6" />

      {/* Logs for Frame */}
      <div className="my-2 mt-1 pt-1 overflow-hidden w-full rounded-xl border border-gray-400 bg-black">
        <div className="space-x-3">
          <Button
            size="xs"
            className="ml-4 text-xs font-medium text-white bg-blue-700 hover:bg-blue-800"
            onClick={handleShowTopLines}
          >
            Scroll from Top
          </Button>
          <span className="text-white ml-4">
            {totalNumLogLines && totalNumLogLines != -1 ? totalNumLogLines.toLocaleString() + " lines of logs" : ""}
          </span>
        </div>
        <div className="mt-1">
          <Editor
            theme="my-theme"
            height="50vh"
            defaultLanguage="plaintext"
            defaultValue={defaultMessage.replaceAll("  ", "")}
            onMount={handleEditorDidMount}
          />
        </div>
      </div>
    </div>
  );
}
