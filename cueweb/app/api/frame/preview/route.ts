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
import { NextRequest, NextResponse } from "next/server";
import path from "path";
import { fileExtension, isWebRenderableImage } from "@/app/utils/preview_utils";

// Serves a rendered frame image from the server filesystem for the frame
// preview side panel. GET /api/frame/preview?path=<absolute file path>.
//
// A browser can't read filesystem paths, so this route streams the bytes (the
// CueWeb container must have the render output mounted/readable). EXR-like
// formats return 415 so the panel shows its "not supported in browser"
// fallback. Path traversal is blocked and, when CUEWEB_PREVIEW_ROOTS is set
// (colon-separated absolute prefixes), reads are restricted to those roots.

const MIME: Record<string, string> = {
  png: "image/png",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  gif: "image/gif",
  webp: "image/webp",
  bmp: "image/bmp",
  avif: "image/avif",
  svg: "image/svg+xml",
};

function allowedRoots(): string[] {
  return (process.env.CUEWEB_PREVIEW_ROOTS ?? "")
    .split(":")
    .map((r) => r.trim())
    .filter(Boolean);
}

export async function GET(request: NextRequest) {
  const target = request.nextUrl.searchParams.get("path") ?? "";

  if (!target || target.includes("\0")) {
    return NextResponse.json({ error: "Missing or invalid path" }, { status: 400 });
  }
  if (!path.isAbsolute(target)) {
    return NextResponse.json({ error: "Path must be absolute" }, { status: 400 });
  }
  // Normalize and reject any traversal that escapes the literal path.
  const normalized = path.normalize(target);
  if (normalized.includes("..")) {
    return NextResponse.json({ error: "Path traversal is not allowed" }, { status: 403 });
  }

  const roots = allowedRoots();
  if (roots.length > 0 && !roots.some((r) => normalized === r || normalized.startsWith(r.endsWith("/") ? r : `${r}/`))) {
    return NextResponse.json({ error: "Path is outside the allowed preview roots" }, { status: 403 });
  }

  const ext = fileExtension(normalized);
  if (!isWebRenderableImage(normalized)) {
    // EXR / TIFF / DPX etc. - the browser can't render these inline.
    return NextResponse.json(
      { error: "unsupported", ext, message: "Preview not supported in browser for this format" },
      { status: 415 },
    );
  }

  try {
    const data = await fs.readFile(normalized);
    return new NextResponse(new Uint8Array(data), {
      status: 200,
      headers: {
        "Content-Type": MIME[ext] ?? "application/octet-stream",
        "Cache-Control": "private, max-age=60",
      },
    });
  } catch (error: any) {
    if (error?.code === "ENOENT") {
      return NextResponse.json({ error: "File not found", path: normalized }, { status: 404 });
    }
    if (error?.code === "EACCES") {
      return NextResponse.json({ error: "Permission denied", path: normalized }, { status: 403 });
    }
    return NextResponse.json({ error: "Could not read image", path: normalized }, { status: 500 });
  }
}
