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

import { promises as fs } from "fs";
import path from "path";
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

export async function GET(request: NextRequest) {
  // Respect auth: require a session when authentication is configured.
  if ((process.env.NEXT_PUBLIC_AUTH_PROVIDER ?? "").trim().length > 0) {
    const session = await getServerSession(authOptions).catch(() => null);
    if (!session?.user) {
      return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
    }
  }

  const filePath = request.nextUrl.searchParams.get("path");
  if (!filePath) {
    return NextResponse.json({ error: "Query parameter 'path' is required" }, { status: 400 });
  }

  try {
    const stat = await fs.stat(filePath);
    if (!stat.isFile()) {
      return NextResponse.json({ error: "Not a file" }, { status: 400 });
    }
    // Read with fs (no shell) so the path can't be used for command injection.
    const data = await fs.readFile(filePath);
    return new NextResponse(data, {
      status: 200,
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Content-Disposition": `attachment; filename="${downloadName(filePath)}"`,
        "Content-Length": String(stat.size),
        "Cache-Control": "no-store",
      },
    });
  } catch (error) {
    return NextResponse.json({ error: "Log file not found" }, { status: 404 });
  }
}
