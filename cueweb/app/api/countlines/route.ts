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
