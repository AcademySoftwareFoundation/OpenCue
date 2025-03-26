import { exec as execCallback } from "child_process";
import { promises as fs } from "fs";
import { NextResponse } from "next/server";
import path from "path";
import { promisify } from "util";

// Helper function to get all matching files in the folder
const exec = promisify(execCallback);

async function getLogVersions(filename: string) {
  const logDir = path.dirname(filename);
  const basename = path.basename(filename);

  // Try to check the file, if there's an error finding it, return []
  try {
    await exec(`wc -l ${path.join(logDir, basename)}`);
  } catch (error) {
    return [];
  }

  try {
    // Read the directory and find matching files that start with the same basename
    const files = await fs.readdir(logDir);
    const matchingFiles = files.filter((file) =>
      file === basename || file.startsWith(`${basename}.`)
    );

    // Sort the files: base file first, then by decreasing version number
    matchingFiles.sort((a, b) => {
      const versionA = a === basename ? Number.MAX_SAFE_INTEGER : parseInt(a.split('.').pop() || "0", 10);
      const versionB = b === basename ? Number.MAX_SAFE_INTEGER : parseInt(b.split('.').pop() || "0", 10);
      return versionB - versionA;
    });

    return matchingFiles;
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
