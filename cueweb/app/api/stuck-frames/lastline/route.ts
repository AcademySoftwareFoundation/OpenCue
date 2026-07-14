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
import { promises as fs } from "fs";
import path from "path";

const execFile = promisify(execFileCallback);

// Optional per-site allow-list (colon-separated absolute prefixes). When set,
// only .rqlog files under one of these roots are read; when unset, reads aren't
// restricted to a root (job log paths are site-specific).
function allowedLogRoots(): string[] {
  return (process.env.CUEWEB_LOG_ROOTS ?? "")
    .split(":")
    .map((r) => r.trim())
    .filter(Boolean);
}

// Returns the last non-empty line of a frame's .rqlog (the Stuck Frames
// "Last Line" column, mirroring CueGUI's getLastLine). Best-effort: if the log
// filesystem isn't mounted in this deployment, or the file is missing, it
// returns an empty line rather than erroring. execFile (no shell) + canonical
// path validation (realpath, .rqlog extension, optional root allow-list) keep
// the caller-supplied path from being abused.
export async function GET(request: NextRequest) {
  const rawPath = request.nextUrl.searchParams.get("path");
  if (!rawPath || !rawPath.endsWith(".rqlog")) {
    return NextResponse.json({ lastLine: "" }, { status: 200 });
  }

  // Canonicalize (follows symlinks) so the extension / root checks apply to the
  // real file rather than a lexical path. A missing/unreadable file resolves to
  // the best-effort empty response.
  let target: string;
  try {
    target = await fs.realpath(path.resolve(rawPath));
  } catch {
    return NextResponse.json({ lastLine: "" }, { status: 200 });
  }
  if (!target.endsWith(".rqlog")) {
    return NextResponse.json({ lastLine: "" }, { status: 200 });
  }

  const rawRoots = allowedLogRoots();
  if (rawRoots.length > 0) {
    const roots = (
      await Promise.all(
        rawRoots.map(async (r) => {
          try {
            return await fs.realpath(path.resolve(r));
          } catch {
            return null;
          }
        }),
      )
    ).filter((r): r is string => r !== null);
    const inAllowedRoot = roots.some((root) => {
      const rel = path.relative(root, target);
      return rel === "" || (!rel.startsWith("..") && !path.isAbsolute(rel));
    });
    if (!inAllowedRoot) {
      return NextResponse.json({ lastLine: "" }, { status: 200 });
    }
  }

  try {
    // tail the file, then keep the last non-blank line.
    const { stdout } = await execFile("tail", ["-n", "20", "--", target], {
      timeout: 5000,
      maxBuffer: 1024 * 1024,
    });
    const lines = stdout.split("\n").map((l) => l.trimEnd()).filter((l) => l.trim() !== "");
    return NextResponse.json({ lastLine: lines.length ? lines[lines.length - 1] : "" }, { status: 200 });
  } catch {
    return NextResponse.json({ lastLine: "" }, { status: 200 });
  }
}
