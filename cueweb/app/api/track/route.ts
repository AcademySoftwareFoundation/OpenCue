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

import MetricsService from "@/lib/metrics-service";
import { extractUser } from "@/lib/track-user";

// POST /api/track - usage beacon from the client. The client sends only the
// kind + a coarse name; the USER is resolved server-side from the session, so
// it can't be spoofed. Increments the matching Prometheus counter.
//   { kind: "page",     name: "<route-or-page>" }
//   { kind: "action",   name: "<action-key>" }
//   { kind: "facility", name: "<facility>" }
//   { kind: "login" }
export async function POST(request: NextRequest): Promise<NextResponse> {
  let body: { kind?: string; name?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const kind = String(body?.kind ?? "");
  const name = String(body?.name ?? "").slice(0, 64); // cap length defensively
  const user = await extractUser(request);
  const metrics = MetricsService.getInstance();

  switch (kind) {
    case "page":
      metrics.recordPageView(user, name);
      break;
    case "action":
      metrics.recordAction(user, name);
      break;
    case "facility":
      metrics.recordFacility(user, name || "unknown");
      break;
    case "login":
      metrics.recordLogin(user);
      break;
    default:
      return NextResponse.json({ error: "Unknown kind" }, { status: 400 });
  }

  // 204: fire-and-forget beacon, nothing to return.
  return new NextResponse(null, { status: 204 });
}
