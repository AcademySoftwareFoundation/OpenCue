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


import { NextAuthOptions } from "next-auth";
import OktaProvider from "next-auth/providers/okta";
import GoogleProvider from "next-auth/providers/google";
import GitHubProvider from "next-auth/providers/github";
import CredentialsProvider from "next-auth/providers/credentials";
import ldap from "ldapjs";
import fs from "fs";

import { buildLocalProvider } from "./rbac/local_provider";
import { authEnabled, hasProvider } from "./rbac/config";
import { upsertProviderIdentity } from "./rbac/identity";
import { resolveAndPersist } from "./rbac/resolvers";
import {
  findUserById,
  isAdmin as isAdminDb,
  listEffectivePermissionsForUser,
  listEffectiveRolesForUser,
  listGroupsForUser,
  markUserLoggedIn,
} from "./rbac/db/dal";

/**
 * Escapes special characters in LDAP DN components to prevent injection attacks.
 * Characters that have special meaning in DNs: , = + < > # ; \ "
 */
function escapeLdapDn(str: string): string {
    return str.replace(/[,=+<>#;\\"\x00]/g, (char) => `\\${char}`);
}

const providerConfigs = [
    {
        type: "Okta",
        provider: OktaProvider,
        envKeys: {
            clientId: "NEXT_AUTH_OKTA_CLIENT_ID",
            clientSecret: "NEXT_AUTH_OKTA_CLIENT_SECRET",
            issuer: "NEXT_AUTH_OKTA_ISSUER",
        },
    },
    {
        type: "Google",
        provider: GoogleProvider,
        envKeys: {
            clientId: "GOOGLE_CLIENT_ID",
            clientSecret: "GOOGLE_CLIENT_SECRET",
        },
    },
    {
        type: "GitHub",
        provider: GitHubProvider,
        envKeys: {
            clientId: "GITHUB_ID",
            clientSecret: "GITHUB_SECRET",
        },
    },
    {
        type: "LDAP",
        envKeys: {
            url: "LDAP_URI",
            login_dn: "LDAP_LOGIN_DN",
            certificate: "LDAP_CERTIFICATE",
        }
    },
];

interface Settings {
  [key: string]: string
}

function loadProviderConfig(type: string, envKeys: any) {
    const settings: Settings = {};
    for (const key in envKeys) {
        const value = process.env[envKeys[key]];
        if (!value) {
            return null;
        }
        settings[key] = value;
    }
    return settings;
}

function buildLdapProvider(settings: Settings) {
    return CredentialsProvider({
        name: "Domain Account",
        credentials: {
            name: { label: "Login", type: "text", placeholder: "" },
            password: { label: "Password", type: "password" },
        },

        async authorize(credentials, req) {
            if (!credentials || !credentials.name || !credentials.password)
                return null;

            // Configure TLS options if certificate is provided
            let tls = {}
            if(settings.certificate){
                tls = {
                    rejectUnauthorized: true,
                    ca: [fs.readFileSync(settings.certificate)],
                }
            }

            const client = ldap.createClient({
                url: settings.url,
                timeout: 5000,
                connectTimeout: 3000,
                tlsOptions: tls,
            })


            return new Promise((resolve, reject) => {
                const dn = settings.login_dn.replace("{login}", escapeLdapDn(credentials.name))
                client.bind(dn, credentials.password, (error: Error | null) => {
                    client.unbind((unbindErr: Error | null) => {
                        if (unbindErr) {
                            console.error(`LDAP unbind error: ${unbindErr.message}`)
                        }
                    })
                    if (error) {
                        console.error(`LDAP bind failed for user: ${error.message}`)
                        resolve(null)
                    } else {
                        resolve({
                            id: credentials.name,
                            name: credentials.name,
                        })
                    }
                })
            })
        },
    });
}

// Configured external providers (Okta, LDAP). The local Credentials
// provider is always added afterwards so the bootstrap admin and any
// other locally-managed users have a way in even when no external IdP
// is configured.
const externalProviders = providerConfigs.map(({ type, envKeys }) => {
    const settings = loadProviderConfig(type, envKeys);
    if (!settings) return null;

    if (type === "Okta") {
        return OktaProvider({
            clientId: settings.clientId,
            clientSecret: settings.clientSecret,
            issuer: settings.issuer,
            authorization: {
                params: { scope: "openid email profile groups" },
            },
        });
    } else if (type === "Google") {
        return GoogleProvider({
            clientId: settings.clientId,
            clientSecret: settings.clientSecret,
        });
    } else if (type === "GitHub") {
        return GitHubProvider({
            clientId: settings.clientId,
            clientSecret: settings.clientSecret,
        });
    } else if (type === "LDAP") {
        return buildLdapProvider(settings);
    }
    return null;
}).filter(provider => provider !== null) as any;

// The local Credentials provider is only enabled when "local" is listed
// in NEXT_PUBLIC_AUTH_PROVIDER. When the env var is empty CueWeb runs
// completely unauthenticated (sandbox mode); no providers are
// registered and the RBAC enforcement layers short-circuit to "allow".
const providers = authEnabled()
    ? hasProvider("local")
        ? [...externalProviders, buildLocalProvider()]
        : externalProviders
    : [];

// Refresh derived state (effective roles/permissions, admin flag) at
// most this often on token reuse. 60s is short enough that an admin
// promotion lights up within a minute without hammering the DB on
// every API request.
const TOKEN_REFRESH_MS = 60 * 1000;

export const authOptions: NextAuthOptions = {
    providers,
    session: { strategy: "jwt" },
    pages: {
        signIn: "/login",
    },
    callbacks: {
        async jwt({ token, user, account, profile, trigger }) {
            const now = Date.now();

            // Sign-in: figure out which row in `users` this session
            // maps to. Local provider already returns it; Okta/LDAP go
            // through the resolver.
            if (trigger === "signIn" || user || account) {
                let userId: number | null = null;

                const cuewebHint = (user as any)?.cueweb as
                    | {
                          source?: "local";
                          externalId?: string;
                          mustChangePassword?: boolean;
                      }
                    | undefined;
                if (cuewebHint?.source === "local" && (user as any)?.id) {
                    userId = Number((user as any).id);
                    token.cuewebSource = "local";
                    token.cuewebMustChangePassword = !!cuewebHint.mustChangePassword;
                } else if (account?.provider === "okta" || account?.provider === "credentials") {
                    const resolved = await resolveAndPersist({
                        profile,
                        account,
                        user,
                        token,
                    });
                    if (resolved) {
                        userId = resolved.userId;
                        token.cuewebSource = resolved.identity.source;
                        markUserLoggedIn(resolved.userId);
                    }
                } else if (
                    account?.provider === "google" ||
                    account?.provider === "github"
                ) {
                    // Identity-only path: Google/GitHub users land in
                    // the users table so admins can attach roles
                    // directly via the Admin UI, even though there is
                    // no native groups source for these providers.
                    const id = upsertProviderIdentity({ profile, account, user });
                    if (id != null) {
                        userId = id;
                        token.cuewebSource = account.provider as "google" | "github";
                        markUserLoggedIn(id);
                    }
                }

                if (userId != null) {
                    token.cuewebUserId = userId;
                    token.cuewebRefreshedAt = 0; // force the refresh block below
                }
            }

            // Refresh derived state from the DB when stale.
            if (
                token.cuewebUserId &&
                (!token.cuewebRefreshedAt ||
                    now - token.cuewebRefreshedAt > TOKEN_REFRESH_MS)
            ) {
                const uid = Number(token.cuewebUserId);
                const row = findUserById(uid);
                if (row) {
                    token.cuewebGroups = listGroupsForUser(uid).map((g) => g.name);
                    token.cuewebRoles = listEffectiveRolesForUser(uid).map(
                        (r) => r.name,
                    );
                    token.cuewebPermissions = listEffectivePermissionsForUser(uid);
                    token.cuewebIsAdmin = isAdminDb(uid);
                    // Local-source rows may flip the mustChangePassword
                    // flag back to 0 after a successful change.
                    if (row.source === "local") {
                        token.cuewebMustChangePassword =
                            row.must_change_password === 1;
                    }
                    token.cuewebRefreshedAt = now;
                }
            }

            return token;
        },

        async session({ session, token }) {
            session.user = session.user ?? ({} as any);
            if (token.cuewebUserId != null) {
                session.user.id = String(token.cuewebUserId);
            }
            session.user.source = (token.cuewebSource as any) ?? null;
            session.user.groups = token.cuewebGroups ?? [];
            session.user.roles = token.cuewebRoles ?? [];
            session.user.permissions = token.cuewebPermissions ?? [];
            session.user.isAdmin = !!token.cuewebIsAdmin;
            session.user.mustChangePassword = !!token.cuewebMustChangePassword;
            return session;
        },
    },
};
