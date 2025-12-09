
import { NextAuthOptions } from "next-auth";
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
            issuer: settings.issuer
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
    // Additional NextAuth configurations can be added here
};

