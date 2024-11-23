
import { NextAuthOptions } from "next-auth";
import OktaProvider from "next-auth/providers/okta";
import GoogleProvider from "next-auth/providers/google";
import GitHubProvider from "next-auth/providers/github";

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
    }
    return null;
}).filter(provider => provider !== null) as any;

export const authOptions: NextAuthOptions = {
    providers,
    // Additional NextAuth configurations can be added here
};



