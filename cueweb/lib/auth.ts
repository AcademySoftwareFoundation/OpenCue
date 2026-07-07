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
import { extractGroups, getUserGroups, isEffectiveAdmin } from "@/lib/authz";
// Import the store directly (not lib/audit) to avoid a require cycle: lib/audit
// imports authOptions from here for getServerSession.
import { recordAudit } from "@/lib/audit-store";
import OktaProvider from "next-auth/providers/okta";
import GoogleProvider from "next-auth/providers/google";
import GitHubProvider from "next-auth/providers/github";
import CredentialsProvider from "next-auth/providers/credentials";
import ldap from "ldapjs";
import fs from "fs";

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

const providers = providerConfigs.map(({ type, provider, envKeys }) => {
    const settings = loadProviderConfig(type, envKeys);
    if (!settings) return null;
    
    if (type === "Okta") {
        return OktaProvider({
          clientId: settings.clientId,
          clientSecret: settings.clientSecret,
          issuer: settings.issuer,
          // Request the `groups` claim alongside the standard OIDC scopes so
          // the ID token carries the user's group memberships (consumed by
          // extractGroups in lib/authz.ts). Note: with Okta's Org
          // Authorization Server, groups are emitted by the app's ID-token
          // "Groups claim" filter and this scope is a no-op; it becomes
          // required only when using a custom Okta Authorization Server.
          authorization: { params: { scope: "openid email profile groups" } },
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

export const authOptions: NextAuthOptions = {
    providers,
    callbacks: {
        // Resolve the user's groups once, at sign-in (this runs in Node and so
        // can reach the identity provider), and stamp them on the JWT. The
        // Edge middleware later reads token.groups to enforce access. The
        // OIDC `profile` is only present on the initial sign-in; `user` covers
        // credentials/LDAP providers that attach a `groups` field in authorize.
        async jwt({ token, profile, user }) {
            if (profile || user) {
                // Always set (even to []) so a user whose groups were cleared
                // doesn't keep stale memberships from a previous token. This
                // branch only runs at sign-in; later requests leave it intact.
                token.groups = extractGroups(
                    profile as unknown as Record<string, unknown> | undefined,
                    user as unknown as Record<string, unknown> | undefined,
                );
            }
            return token;
        },
        // Expose the groups on the session so client/server components can
        // tailor the UI (e.g. hide admin-only controls). `isAdmin` is the
        // effective decision (true for everyone when the authz gate is
        // inactive) so the AppHeader/AppSidebar can show or hide the Admin ->
        // CueWeb Audit entry without re-deriving the policy.
        async session({ session, token }) {
            const groups = getUserGroups(token as { groups?: unknown });
            (session as { groups?: string[] }).groups = groups;
            (session as { isAdmin?: boolean }).isAdmin = isEffectiveAdmin(groups);
            return session;
        },
    },
    // Audit authentication events into the CueWeb Audit trail (Admin -> CueWeb
    // Audit). Best-effort: a logging failure must never block sign-in/out.
    events: {
        async signIn({ user }) {
            await recordAudit({
                at: new Date().toISOString(),
                actor: user?.email || user?.name || "anonymous",
                category: "auth",
                action: "Sign in",
                result: "success",
            }).catch(() => undefined);
        },
        async signOut({ token }) {
            const actor =
                (token as { email?: string; name?: string })?.email ||
                (token as { name?: string })?.name ||
                "anonymous";
            await recordAudit({
                at: new Date().toISOString(),
                actor,
                category: "auth",
                action: "Sign out",
                result: "success",
            }).catch(() => undefined);
        },
    },
};

