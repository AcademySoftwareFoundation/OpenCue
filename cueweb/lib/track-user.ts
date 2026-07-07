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

// The X-User / X-Forwarded-User identity headers are forgeable by any client,
// so they are only honored when the operator explicitly opts in - i.e. the
// deployment sits behind a trusted reverse proxy / auth gateway that strips
// inbound copies and injects the authenticated identity. Off by default; the
// authenticated NextAuth session is always preferred and is non-forgeable.
const TRUST_IDENTITY_HEADER =
  (process.env.CUEWEB_TRUST_IDENTITY_HEADER ?? "").toLowerCase() === "true";

export async function extractUser(request: NextRequest): Promise<string> {
  // Authoritative source: the signed-in session (cannot be spoofed).
  try {
    const session = await getServerSession(authOptions).catch(() => null);
    const fromSession = session?.user?.name || session?.user?.email;
    if (fromSession) return localPart(fromSession).trim() || ANONYMOUS_USER;
  } catch {
    // Fall through to the (opt-in) proxy header / anonymous.
  }

  // Only trust the proxy-injected identity header when explicitly enabled.
  if (TRUST_IDENTITY_HEADER) {
    const header =
      request.headers.get("X-User") || request.headers.get("X-Forwarded-User");
    if (header) return localPart(header).trim() || ANONYMOUS_USER;
  }

  return ANONYMOUS_USER;
}
