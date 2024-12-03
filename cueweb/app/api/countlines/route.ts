import { NextRequest, NextResponse } from "next/server";
import { exec as execCallback } from "child_process";
import { promisify } from "util";
import { handleError } from "@/app/utils/notify_utils";

const exec = promisify(execCallback);
async function countLines(filename: string | null) {
  try {
    const result = await exec(`wc -l ${filename}`);
    if (result.stdout.includes("No such file or directory")) {
      return -1;
    }
    return parseInt(result.stdout.trim().split(" ")[0]);
  } catch (error) {
    handleError(`Error reading logfile: ${error}`);
    return -1;
  }
}
// end point to count lines for a given file. returns -1 if file does not exist
export async function GET(request: NextRequest) {
  let path = request.nextUrl.searchParams.get("path");
  let count = await countLines(path);
  return NextResponse.json({ count });
}
