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

import { NextRequest, NextResponse } from "next/server";
import { execFile as execFileCallback } from "child_process";
import { promisify } from "util";

const execFile = promisify(execFileCallback);

// Returns the last non-empty line of a frame's .rqlog (the Stuck Frames
// "Last Line" column, mirroring CueGUI's getLastLine). Best-effort: if the log
// filesystem isn't mounted in this deployment, or the file is missing, it
// returns an empty line rather than erroring. execFile (no shell) + an rqlog
// path allowlist keep the caller-supplied path from being abused.
export async function GET(request: NextRequest) {
  const path = request.nextUrl.searchParams.get("path");
  if (!path || !path.endsWith(".rqlog") || path.includes("..")) {
    return NextResponse.json({ lastLine: "" }, { status: 200 });
  }
  try {
    // tail the file, then keep the last non-blank line.
    const { stdout } = await execFile("tail", ["-n", "20", "--", path], {
      timeout: 5000,
      maxBuffer: 1024 * 1024,
    });
    const lines = stdout.split("\n").map((l) => l.trimEnd()).filter((l) => l.trim() !== "");
    return NextResponse.json({ lastLine: lines.length ? lines[lines.length - 1] : "" }, { status: 200 });
  } catch {
    return NextResponse.json({ lastLine: "" }, { status: 200 });
  }
}
