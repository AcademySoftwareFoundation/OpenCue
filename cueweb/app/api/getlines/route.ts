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
