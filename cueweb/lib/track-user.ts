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

// Server-side resolution of the calling user for usage metrics. The user label
// is resolved from the authenticated NextAuth session (never trusted from the
// client request body), falling back to a reverse-proxy identity header and
// finally the ANONYMOUS_USER sentinel when auth is disabled. Mirrors
// asset-search's extract_user(): session -> X-User -> X-Forwarded-User ->
// anonymous.
import type { NextRequest } from "next/server";
import { getServerSession } from "next-auth";

import { authOptions } from "@/lib/auth";
import { ANONYMOUS_USER } from "@/lib/metrics-service";

function localPart(value: string): string {
  return value.includes("@") ? value.split("@")[0] : value;
}

export async function extractUser(request: NextRequest): Promise<string> {
  try {
    const session = await getServerSession(authOptions).catch(() => null);
    const fromSession = session?.user?.name || session?.user?.email;
    if (fromSession) return localPart(fromSession).trim() || ANONYMOUS_USER;
  } catch {
    // Fall through to headers / anonymous.
  }
  const header =
    request.headers.get("X-User") || request.headers.get("X-Forwarded-User");
  if (header) return localPart(header).trim() || ANONYMOUS_USER;
  return ANONYMOUS_USER;
}
