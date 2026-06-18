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

import { createReadStream, promises as fs } from "fs";
import path from "path";
import { Readable } from "stream";
import { getServerSession } from "next-auth";
import { NextRequest, NextResponse } from "next/server";

import { authOptions } from "@/lib/auth";

/**
 * Download the raw frame log as a plain-text attachment. Backs the "Download"
 * button on the frame log viewer; `path` is the currently-selected log version
 * (the same path the viewer streams via /api/getlines).
 *
 * Auth: when an authentication provider is configured
 * (`NEXT_PUBLIC_AUTH_PROVIDER`), a signed-in session is required; the sandbox
 * (no provider) stays open, matching the rest of CueWeb.
 */

// Download filename: the log basename with the `.rqlog` suffix swapped for
// `.log`, sanitized so it is safe to embed in the Content-Disposition header
// (the value is derived server-side, never taken from the client).
function downloadName(filePath: string): string {
  const base = path.basename(filePath);
  const stem = base.endsWith(".rqlog") ? base.slice(0, -".rqlog".length) : base;
  const safe = stem.replace(/[^A-Za-z0-9._-]/g, "_");
  return `${safe || "log"}.log`;
}

// Optional per-site allow-list (colon-separated absolute prefixes), shared with
// the Stuck Frames "Last Line" route. When set, only files under one of these
// roots are served; when unset, reads aren't restricted to a root (job log
// paths are site-specific).
function allowedLogRoots(): string[] {
  return (process.env.CUEWEB_LOG_ROOTS ?? "")
    .split(":")
    .map((r) => r.trim())
    .filter(Boolean);
}

export async function GET(request: NextRequest) {
  // Respect auth: require a session when authentication is configured.
  if ((process.env.NEXT_PUBLIC_AUTH_PROVIDER ?? "").trim().length > 0) {
    const session = await getServerSession(authOptions).catch(() => null);
    if (!session?.user) {
      return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
    }
  }

  const filePath = request.nextUrl.searchParams.get("path") ?? "";
  if (!filePath || filePath.includes("\0") || !path.isAbsolute(filePath)) {
    return NextResponse.json({ error: "Query parameter 'path' is required" }, { status: 400 });
  }

  try {
    // Canonicalize via realpath before any read: path.resolve is purely lexical,
    // but fs follows symlinks, so a `..` or symlinked path could otherwise escape
    // the allow-list. realpath also requires the file to exist (surfaced as 404).
    const realPath = await fs.realpath(path.resolve(filePath));

    // When log roots are configured, the canonical target must sit inside one of
    // them (also canonicalized). Without this a crafted path could read any file
    // the server process can access.
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
        const rel = path.relative(root, realPath);
        return rel === "" || (!rel.startsWith("..") && !path.isAbsolute(rel));
      });
      if (!inAllowedRoot) {
        return NextResponse.json({ error: "Path is outside the allowed log roots" }, { status: 403 });
      }
    }

    const stat = await fs.stat(realPath);
    if (!stat.isFile()) {
      return NextResponse.json({ error: "Not a file" }, { status: 400 });
    }
    // Stream the file (no shell, so the path can't be used for command
    // injection) instead of buffering it into memory: render logs can be very
    // large, and fs.readFile would hold the whole file per concurrent download.
    const stream = Readable.toWeb(createReadStream(realPath)) as ReadableStream<Uint8Array>;
    return new NextResponse(stream, {
      status: 200,
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Content-Disposition": `attachment; filename="${downloadName(realPath)}"`,
        "Content-Length": String(stat.size),
        "Cache-Control": "no-store",
      },
    });
  } catch (error) {
    return NextResponse.json({ error: "Log file not found" }, { status: 404 });
  }
}
