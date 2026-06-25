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

import { handleRoute } from "@/app/utils/gateway_server";
import { submissionSchema } from "@/app/cuesubmit/lib/schemas";
import { buildJobSpecXml } from "@/app/cuesubmit/lib/spec_xml";

/**
 * Browser endpoint for CueSubmit. Accepts a JSON payload matching
 * {@link submissionSchema}, builds the cuebot job-spec XML, and forwards
 * it to job.JobInterface/LaunchSpecAndWait. The "AndWait" variant
 * returns the resolved job(s) so we can hand the caller something to
 * navigate to (instead of just an opaque "submitted" ack).
 *
 * The submit path is intentionally a single POST: spec construction
 * lives server-side so the browser bundle stays slim and we don't
 * leak the gateway JWT.
 */
export async function POST(request: NextRequest) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { error: "Invalid JSON body." },
      { status: 400 },
    );
  }

  const parsed = submissionSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json(
      {
        error: "Validation failed.",
        details: parsed.error.flatten(),
      },
      { status: 400 },
    );
  }

  let spec: string;
  try {
    spec = buildJobSpecXml(parsed.data.job, parsed.data.layers);
  } catch (err) {
    return NextResponse.json(
      {
        error: err instanceof Error ? err.message : "Failed to build job spec.",
      },
      { status: 400 },
    );
  }

  // LaunchSpecAndWait returns { jobs: JobSeq } so we know which job(s)
  // the spec produced. The REST gateway flattens JobSeq once already;
  // we shape the response further so callers get { jobs: Job[] }.
  const response = await handleRoute(
    "POST",
    "/job.JobInterface/LaunchSpecAndWait",
    JSON.stringify({ spec }),
  );
  // The REST gateway is supposed to return JSON, but a misconfigured or down
  // gateway can answer with empty bodies / HTML / plain text - guard the
  // parse so the handler doesn't crash with an unhandled SyntaxError.
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    return NextResponse.json(
      {
        error: data?.error ?? "Failed to submit job.",
      },
      { status: response.status },
    );
  }

  const jobs =
    data?.data?.jobs?.jobs ??
    data?.data?.jobs ??
    [];
  return NextResponse.json({ jobs });
}
