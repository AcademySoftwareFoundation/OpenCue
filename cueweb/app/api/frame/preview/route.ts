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
import { getServerSession } from "next-auth";
import { NextRequest, NextResponse } from "next/server";
import path from "path";
import { authOptions } from "@/lib/auth";
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
  // SVG is intentionally omitted: serving it same-origin would allow script
  // execution, so the route treats .svg as an unsupported format (415).
};

function allowedRoots(): string[] {
  return (process.env.CUEWEB_PREVIEW_ROOTS ?? "")
    .split(":")
    .map((r) => r.trim())
    .filter(Boolean);
}

export async function GET(request: NextRequest) {
  // Respect auth: this route serves filesystem-backed bytes, so require a
  // session when authentication is configured (parity with /api/getlog).
  if ((process.env.NEXT_PUBLIC_AUTH_PROVIDER ?? "").trim().length > 0) {
    const session = await getServerSession(authOptions).catch(() => null);
    if (!session?.user) {
      return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
    }
  }

  const target = request.nextUrl.searchParams.get("path") ?? "";

  if (!target || target.includes("\0")) {
    return NextResponse.json({ error: "Missing or invalid path" }, { status: 400 });
  }
  if (!path.isAbsolute(target)) {
    return NextResponse.json({ error: "Path must be absolute" }, { status: 400 });
  }
  const normalized = path.resolve(target);

  // Canonicalize via realpath before the boundary check: path.resolve is purely
  // lexical, but fs.readFile follows symlinks, so a symlink inside an allowed
  // root could otherwise resolve to a file outside it and still pass. realpath
  // also requires the file to exist, surfacing missing/permission errors here.
  let realTarget: string;
  try {
    realTarget = await fs.realpath(normalized);
  } catch (error: any) {
    console.error(`Frame preview realpath failed for ${normalized}:`, error?.code ?? error);
    if (error?.code === "ENOENT") {
      return NextResponse.json({ error: "File not found" }, { status: 404 });
    }
    if (error?.code === "EACCES") {
      return NextResponse.json({ error: "Permission denied" }, { status: 403 });
    }
    return NextResponse.json({ error: "Could not read image" }, { status: 500 });
  }

  // When preview roots are configured, the canonical target must sit inside one
  // of them (also canonicalized). Roots are an optional per-site allow-list;
  // when unset, reads are not restricted to a root (render output paths are
  // site-specific). A root that can't be resolved is treated as non-matching.
  const rawRoots = allowedRoots();
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
      const rel = path.relative(root, realTarget);
      return rel === "" || (!rel.startsWith("..") && !path.isAbsolute(rel));
    });
    if (!inAllowedRoot) {
      return NextResponse.json({ error: "Path is outside the allowed preview roots" }, { status: 403 });
    }
  }

  const ext = fileExtension(realTarget);
  if (!isWebRenderableImage(realTarget)) {
    // EXR / TIFF / DPX / SVG etc. - the browser can't (safely) render inline.
    return NextResponse.json(
      { error: "unsupported", ext, message: "Preview not supported in browser for this format" },
      { status: 415 },
    );
  }

  try {
    const data = await fs.readFile(realTarget);
    return new NextResponse(new Uint8Array(data), {
      status: 200,
      headers: {
        "Content-Type": MIME[ext] ?? "application/octet-stream",
        "Cache-Control": "private, max-age=60",
      },
    });
  } catch (error: any) {
    // Log the resolved path server-side for diagnostics, but don't echo the
    // server filesystem layout back to the client.
    console.error(`Frame preview read failed for ${realTarget}:`, error?.code ?? error);
    if (error?.code === "ENOENT") {
      return NextResponse.json({ error: "File not found" }, { status: 404 });
    }
    if (error?.code === "EACCES") {
      return NextResponse.json({ error: "Permission denied" }, { status: 403 });
    }
    return NextResponse.json({ error: "Could not read image" }, { status: 500 });
  }
}
