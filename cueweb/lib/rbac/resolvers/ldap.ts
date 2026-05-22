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

import fs from "node:fs";
import ldap from "ldapjs";

import type { GroupsResolver, ResolvedIdentity } from "./types";

/**
 * Resolves groups via a bound LDAP search for the `memberOf` attribute
 * on the user's DN. The same env vars as the existing LDAP provider
 * (LDAP_URI, LDAP_LOGIN_DN, LDAP_CERTIFICATE) are used; the user is
 * resolved from `account.providerAccountId`.
 *
 * The CN portion of each `memberOf` DN is extracted as the group name,
 * which matches how admins usually refer to LDAP groups in conversation
 * and in the legacy CUECOMMANDER_ACCESS_GROUPS list.
 *
 * `LDAP_SEARCH_USER_DN` + `LDAP_SEARCH_USER_PASSWORD` (optional) let
 * the resolver bind as a service account for the memberOf lookup;
 * if absent it falls back to anonymous, then to skipping the lookup.
 */
function escapeLdapDn(str: string): string {
  return str.replace(/[,=+<>#;\\"\x00]/g, (c) => `\\${c}`);
}

function extractCn(dn: string): string | null {
  // memberOf values look like: "CN=gr-render-leads,OU=Groups,DC=acme,DC=local"
  const m = /^CN=([^,]+)/i.exec(dn);
  if (!m) return null;
  return m[1].trim();
}

async function lookupMemberOf(userDn: string): Promise<string[]> {
  const url = process.env.LDAP_URI;
  if (!url) return [];

  const certificatePath = process.env.LDAP_CERTIFICATE;
  const tls: ldap.ClientOptions["tlsOptions"] = certificatePath
    ? {
        rejectUnauthorized: true,
        ca: [fs.readFileSync(certificatePath)],
      }
    : undefined;

  const client = ldap.createClient({
    url,
    timeout: 5000,
    connectTimeout: 3000,
    tlsOptions: tls,
  });

  const bindDn = process.env.LDAP_SEARCH_USER_DN;
  const bindPwd = process.env.LDAP_SEARCH_USER_PASSWORD;
  if (bindDn && bindPwd) {
    await new Promise<void>((resolve, reject) => {
      client.bind(bindDn, bindPwd, (err) =>
        err ? reject(err) : resolve(),
      );
    });
  }

  try {
    return await new Promise<string[]>((resolve) => {
      const groups: string[] = [];
      client.search(
        userDn,
        { scope: "base", attributes: ["memberOf"] },
        (err, res) => {
          if (err) {
            resolve([]);
            return;
          }
          res.on("searchEntry", (entry: any) => {
            const memberOfAttr = entry.attributes?.find(
              (a: any) => String(a.type).toLowerCase() === "memberof",
            );
            const values: string[] = memberOfAttr
              ? Array.isArray(memberOfAttr.values)
                ? memberOfAttr.values
                : [String(memberOfAttr.values)]
              : [];
            for (const v of values) {
              const cn = extractCn(String(v));
              if (cn) groups.push(cn);
            }
          });
          res.on("error", () => resolve([]));
          res.on("end", () => resolve(groups));
        },
      );
    });
  } finally {
    try {
      client.unbind();
    } catch {
      // ignore
    }
  }
}

export const ldapResolver: GroupsResolver = {
  id: "ldap",
  async resolve({ user, account }): Promise<ResolvedIdentity | null> {
    // Only handle the LDAP CredentialsProvider sign-in path. Other
    // provider sign-ins (Okta, local) flow through their own resolvers.
    if (account?.provider !== "credentials") return null;

    // The existing LDAP CredentialsProvider returns `{ id, name }` and
    // does not stash the DN, so we reconstruct it from LDAP_LOGIN_DN.
    const username = (user?.name as string | undefined) || account?.providerAccountId;
    if (!username) return null;

    const loginDnTemplate = process.env.LDAP_LOGIN_DN;
    const userDn = loginDnTemplate
      ? loginDnTemplate.replace("{login}", escapeLdapDn(username))
      : null;

    let groups: string[] = [];
    if (userDn) {
      try {
        groups = await lookupMemberOf(userDn);
      } catch {
        groups = [];
      }
    }

    return {
      source: "ldap",
      externalId: userDn ?? `ldap:${username}`,
      username,
      email: null,
      displayName: username,
      groups,
    };
  },
};
