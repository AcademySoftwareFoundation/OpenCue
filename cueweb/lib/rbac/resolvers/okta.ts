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

import type { GroupsResolver, ResolvedIdentity } from "./types";

/**
 * Reads the user's groups from the `groups` claim on the Okta ID token.
 *
 * The Okta application must be configured to include a `groups` claim
 * in the ID token (Okta admin -> Applications -> <app> -> Sign On ->
 * OpenID Connect ID Token -> "Groups claim type" set to "Filter" with
 * a regex matching the groups you want to expose, e.g. `gr-render-.*`).
 * Without that configuration the claim is absent and this resolver
 * returns an empty groups list.
 */
export const oktaResolver: GroupsResolver = {
  id: "okta",
  async resolve({ profile, account, token }): Promise<ResolvedIdentity | null> {
    if (account?.provider !== "okta") return null;

    // The `groups` claim ships as `string[]` per OIDC convention.
    const rawGroups =
      (profile && (profile as any).groups) ||
      (token && (token as any).groups) ||
      [];
    const groups: string[] = Array.isArray(rawGroups)
      ? rawGroups.filter((g): g is string => typeof g === "string")
      : [];

    const sub =
      (profile as any)?.sub ||
      account?.providerAccountId ||
      (token as any)?.sub;
    if (!sub) return null;

    const email = ((profile as any)?.email as string | undefined) ?? null;
    const preferredUsername =
      ((profile as any)?.preferred_username as string | undefined) ||
      (email ? email.split("@")[0] : null) ||
      sub;

    return {
      source: "okta",
      externalId: String(sub),
      username: preferredUsername,
      email,
      displayName: ((profile as any)?.name as string | undefined) ?? null,
      groups,
    };
  },
};
