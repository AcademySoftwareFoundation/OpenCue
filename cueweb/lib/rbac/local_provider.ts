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

import "server-only";

import CredentialsProvider from "next-auth/providers/credentials";

import {
  isBlocked,
  recordFailedAttempt,
  clearAttempts,
} from "./rate_limit";
import { ensureBootstrapAdmin, verifyLocalLogin } from "./bootstrap";
import { hasProvider } from "./config";
import { markUserLoggedIn } from "./db/dal";

/**
 * NextAuth Credentials provider backed by the local `users` table.
 * Always available so an admin can break-glass when the upstream IdP
 * is down. When NEXT_PUBLIC_AUTH_PROVIDER is empty (sandbox mode),
 * this is the only provider; otherwise it sits alongside Okta/LDAP.
 *
 * Rate-limited at 5 failures per 15 minutes, keyed by the requester's
 * IP, to keep credential stuffing slow.
 */
export function buildLocalProvider() {
  return CredentialsProvider({
    id: "local",
    name: "Local account",
    credentials: {
      username: { label: "Username", type: "text" },
      password: { label: "Password", type: "password" },
    },

    async authorize(credentials, req) {
      // Defensive: bail if somehow this provider is invoked with the
      // local mode disabled (shouldn't happen because auth.ts already
      // gates registration on hasProvider("local"), but the cost of
      // the check is negligible and it makes the intent explicit).
      if (!hasProvider("local")) return null;

      // Ensure the bootstrap admin exists on the very first login
      // attempt so the operator never sees an empty user table.
      try {
        await ensureBootstrapAdmin();
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error("CueWeb: bootstrap admin init failed:", err);
      }

      if (!credentials?.username || !credentials?.password) return null;

      const ip =
        (req?.headers?.["x-forwarded-for"] as string | undefined)
          ?.split(",")[0]
          ?.trim() ||
        (req?.headers?.["x-real-ip"] as string | undefined) ||
        "unknown";
      const key = `local:${ip}`;

      const blocked = isBlocked(key);
      if (blocked.blocked) {
        // eslint-disable-next-line no-console
        console.warn(
          `CueWeb: /login/local blocked for ${ip} (retry in ${Math.ceil(
            blocked.retryInMs / 1000,
          )}s)`,
        );
        return null;
      }

      const result = await verifyLocalLogin(
        String(credentials.username),
        String(credentials.password),
      );
      if (!result || !result.user) {
        recordFailedAttempt(key);
        return null;
      }
      clearAttempts(key);
      markUserLoggedIn(result.user.id);

      // Surface flags the JWT callback uses without re-querying.
      // NextAuth's User type doesn't include our custom keys, so we
      // assert to `any` here. The jwt callback reads them as
      // (user as any).cueweb.
      const enriched = {
        id: String(result.user.id),
        name: result.user.display_name || result.user.username,
        email: result.user.email ?? undefined,
        cueweb: {
          source: "local",
          externalId: result.user.external_id,
          mustChangePassword: result.user.must_change_password === 1,
        },
      };
      return enriched as any;
    },
  });
}
