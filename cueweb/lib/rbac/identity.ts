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

import { upsertUser } from "./db/dal";
import type { Source } from "./db/types";

/**
 * Upserts the signed-in user into the local RBAC store regardless of
 * which auth provider authenticated them. Used for providers that do
 * not have a groups resolver (Google, GitHub today): the user lands
 * in the `users` table so an admin can attach roles directly in the
 * Admin UI, but no group membership is synced.
 *
 * Source mapping:
 *   - okta   -> stored as `source=okta`
 *   - google -> stored as `source=imported` (no native source slot)
 *   - github -> stored as `source=imported`
 *   - LDAP   -> handled by the LDAP resolver
 *   - local  -> handled by the local Credentials provider
 *
 * Returns the row id, or null if no usable identity could be derived.
 */
export function upsertProviderIdentity(args: {
  account: any;
  profile: any;
  user: any;
}): number | null {
  const { account, profile, user } = args;
  if (!account?.provider) return null;

  let externalId: string | null = null;
  let username = "";
  let email: string | null = null;
  let displayName: string | null = null;
  let source: Source = "imported";

  switch (account.provider) {
    case "google": {
      const id =
        (profile as any)?.sub ||
        account.providerAccountId ||
        (profile as any)?.email;
      if (!id) return null;
      externalId = `google:${id}`;
      email = ((profile as any)?.email as string | undefined) ?? null;
      username = email ? email.split("@")[0] : String(id);
      displayName = ((profile as any)?.name as string | undefined) ?? null;
      source = "imported";
      break;
    }
    case "github": {
      const id =
        (profile as any)?.id ||
        account.providerAccountId ||
        (profile as any)?.login;
      if (!id) return null;
      externalId = `github:${id}`;
      username =
        ((profile as any)?.login as string | undefined) || String(id);
      email = ((profile as any)?.email as string | undefined) ?? null;
      displayName = ((profile as any)?.name as string | undefined) ?? null;
      source = "imported";
      break;
    }
    default:
      return null;
  }

  if (!externalId || !username) return null;
  return upsertUser({
    externalId,
    username,
    email,
    displayName,
    source,
  });
}
