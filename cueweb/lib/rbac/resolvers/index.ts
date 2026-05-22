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

import { ldapResolver } from "./ldap";
import { noneResolver } from "./none";
import { oktaResolver } from "./okta";
import type { GroupsResolver, ResolvedIdentity } from "./types";

import {
  syncUserGroupMembership,
  upsertGroup,
  upsertUser,
} from "../db/dal";

const RESOLVERS: Record<string, GroupsResolver> = {
  okta: oktaResolver,
  ldap: ldapResolver,
  none: noneResolver,
};

/**
 * Returns the resolver named by CUEWEB_GROUPS_RESOLVER, falling back
 * to `none` when unset or unknown. The CueWeb startup logs the active
 * resolver once via lib/rbac/log.ts.
 */
export function activeResolver(): GroupsResolver {
  const name = (process.env.CUEWEB_GROUPS_RESOLVER || "none").toLowerCase();
  return RESOLVERS[name] ?? noneResolver;
}

/**
 * Convenience: run the active resolver and persist the result. Returns
 * the upserted user id, or null if the resolver returned no identity
 * (e.g. the local Credentials provider path is handled elsewhere).
 */
export async function resolveAndPersist(args: {
  profile: any;
  account: any;
  user: any;
  token: any;
}): Promise<{ userId: number; identity: ResolvedIdentity } | null> {
  const resolver = activeResolver();
  const identity = await resolver.resolve(args);
  if (!identity) return null;

  const userId = upsertUser({
    externalId: identity.externalId,
    username: identity.username,
    email: identity.email,
    displayName: identity.displayName,
    source: identity.source,
  });

  const groupIds: number[] = [];
  for (const name of identity.groups) {
    const gid = upsertGroup({ name, source: identity.source });
    groupIds.push(gid);
  }
  syncUserGroupMembership(userId, groupIds, identity.source);

  return { userId, identity };
}

export type { GroupsResolver, ResolvedIdentity };
