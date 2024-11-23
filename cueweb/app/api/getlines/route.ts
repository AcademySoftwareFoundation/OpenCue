import { NextRequest, NextResponse } from "next/server";
import { exec as execCallback } from "child_process";
import { promisify } from "util";
import { handleError } from "@/app/utils/notify_utils";

const exec = promisify(execCallback);

async function getLines(filename: string, start: number, end: number) {
  if (start <= 0) {
    return "start cannot be <= 0.";
  }
  const result = await exec(`sed -n '${start},${end}p' ${filename}`);
  //const result = await exec(`cat ${filename}`)
  return result.stdout;
}

//endpoint to retrieve logs for a frame
export async function GET(request: NextRequest) {
  let start = request.nextUrl.searchParams.get("start");
  let end = request.nextUrl.searchParams.get("end");
  let path = request.nextUrl.searchParams.get("path");

  if (!path || !start || !end) {
    handleError("Query paramater not provided to api/getlines");
    return NextResponse.json({ message: "Query parameter not provided" }, { status: 500 });
  }

  let lines = await getLines(path, parseInt(start), parseInt(end));

  return NextResponse.json({ lines });
}
