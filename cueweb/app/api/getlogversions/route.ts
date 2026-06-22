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
import { NextResponse } from "next/server";
import path from "path";

// One log version (the active log + its rotated retries), with the metadata the
// version dropdown shows: byte size and last-modified time (epoch ms).
interface LogVersion {
  name: string;
  size: number;
  mtime: number;
}

async function getLogVersions(filename: string): Promise<LogVersion[]> {
  const logDir = path.dirname(filename);
  const basename = path.basename(filename);

  // Bail out if the base log file isn't readable.
  try {
    await fs.stat(path.join(logDir, basename));
  } catch (error) {
    return [];
  }

  try {
    // Find matching files: the base log and its rotated versions (basename.N).
    const files = await fs.readdir(logDir);
    const matchingFiles = files.filter(
      (file) => file === basename || file.startsWith(`${basename}.`),
    );

    // stat each to get size + mtime (tolerate a file vanishing between readdir
    // and stat, e.g. mid-rotation).
    const versions = await Promise.all(
      matchingFiles.map(async (name): Promise<LogVersion> => {
        try {
          const stat = await fs.stat(path.join(logDir, name));
          return { name, size: stat.size, mtime: stat.mtimeMs };
        } catch {
          return { name, size: 0, mtime: 0 };
        }
      }),
    );

    // Newest first by modified time; tie-break by version number (base log,
    // treated as the highest, then decreasing .N) for stable ordering.
    versions.sort((a, b) => {
      if (b.mtime !== a.mtime) return b.mtime - a.mtime;
      const va = a.name === basename ? Number.MAX_SAFE_INTEGER : parseInt(a.name.split(".").pop() || "0", 10);
      const vb = b.name === basename ? Number.MAX_SAFE_INTEGER : parseInt(b.name.split(".").pop() || "0", 10);
      return vb - va;
    });

    return versions;
  } catch (error) {
    console.error("Error reading directory:", error);
    return [];
  }
}

// Endpoint to get the different versions of logs if they have been retried
export async function GET(request: Request) {
  // Validate the method, only allow GET
  if (request.method !== "GET") {
    return NextResponse.json({ error: "Method Not Allowed" }, { status: 405 });
  }

  const { searchParams } = new URL(request.url);
  const filename = searchParams.get("filename");

  // Validate the filename parameter
  if (!filename) {
    return NextResponse.json({ error: "Filename is required" }, { status: 400 });
  }

  try {
    const versions = await getLogVersions(filename);

    // If no versions were found, return a 404 response
    if (versions.length === 0) {
      return NextResponse.json({ error: "No log versions found" }, { status: 404 });
    }

    return NextResponse.json({ versions });
  } catch (error) {
    // Handle any unexpected errors during the process
    return NextResponse.json({ error: "Error retrieving log versions" }, { status: 500 });
  }
}
