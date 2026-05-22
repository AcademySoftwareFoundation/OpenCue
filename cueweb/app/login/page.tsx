'use client'

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


// Custom authentication page
import { signIn } from "next-auth/react";
import React from "react";
import { useRouter } from "next/navigation";
import { OktaSignInButton, GmailSignInButton, GithubSignInButton, LdapSignInButton, CuewebRedirectButton } from "@/components/ui/auth-button"
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import CueWebIcon from "../../components/ui/cuewebicon";

export default function Page() {
    const router = useRouter();
    const authProviders = (process.env.NEXT_PUBLIC_AUTH_PROVIDER || "")
        .split(",")
        .map((s) => s.trim().toLowerCase())
        .filter(Boolean);

    const hasLocal = authProviders.includes("local");
    const hasOkta = authProviders.includes("okta");
    const hasGoogle = authProviders.includes("google");
    const hasGithub = authProviders.includes("github");
    const hasLdap = authProviders.includes("ldap");
    const authEnabled = authProviders.length > 0;

    const [username, setUsername] = React.useState("");
    const [password, setPassword] = React.useState("");
    const [error, setError] = React.useState<string | null>(null);
    const [submitting, setSubmitting] = React.useState(false);

    const oktaLogin = async () => {
        signIn("okta", { callbackUrl: "/"});
    };

    const googleLogin = async () => {
        signIn("google", { callbackUrl: "/"});
    };

    const githubLogin = async () => {
        signIn("github", { callbackUrl: "/"});
    };

    const ldapLogin = async () => {
        router.push('/login/ldap');
    };

    const cuewebRedirect = () => {
        router.push('/');
    };

    const localLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setSubmitting(true);
        const result = await signIn("local", {
            username,
            password,
            redirect: false,
            callbackUrl: "/",
        });
        setSubmitting(false);
        if (!result || result.error) {
            setError("Invalid username or password.");
            return;
        }
        // The session callback writes mustChangePassword onto the JWT;
        // re-fetch the session and decide where to land.
        try {
            const res = await fetch("/api/auth/session", { cache: "no-store" });
            const session = await res.json();
            if (session?.user?.mustChangePassword) {
                router.push("/login/change-password");
                return;
            }
        } catch {
            // fall through to default
        }
        router.push(result.url || "/");
    };

    return (
        <div className="relative flex flex-col sm:flex-row w-full justify-center items-center h-screen bg-gray-100
            dark:bg-gray-800">
            <div className="absolute top-4 right-4">
                <ThemeToggle />
            </div>
            <div className="flex flex-col sm:flex-row sm:space-x-20 max-w-[100vh] bg-white dark:bg-black sm:px-16
                sm:py-8 rounded-xl">
                <div className="flex flex-col justify-center items-center">
                <CueWebIcon/>
                </div>
                <div className="flex flex-col w-full space-y-3 ">
                    <div className="max-w-72 space-y-3">
                        {authEnabled && (
                            <h1 className="text-xl font-bold">Sign in</h1>
                        )}
                        {!authEnabled && <CuewebRedirectButton onClick={cuewebRedirect}/>}

                        {hasLocal && (
                            <form onSubmit={localLogin} className="space-y-2">
                                <div className="space-y-1">
                                    <label htmlFor="local-username" className="text-sm font-medium">
                                        Username
                                    </label>
                                    <input
                                        id="local-username"
                                        type="text"
                                        autoComplete="username"
                                        required
                                        value={username}
                                        onChange={(e) => setUsername(e.target.value)}
                                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                                    />
                                </div>
                                <div className="space-y-1">
                                    <label htmlFor="local-password" className="text-sm font-medium">
                                        Password
                                    </label>
                                    <input
                                        id="local-password"
                                        type="password"
                                        autoComplete="current-password"
                                        required
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                                    />
                                </div>
                                {error && (
                                    <p className="text-sm text-red-600" role="alert">
                                        {error}
                                    </p>
                                )}
                                <Button type="submit" disabled={submitting} className="w-full">
                                    {submitting ? "Signing in…" : "Sign in"}
                                </Button>
                            </form>
                        )}

                        {hasOkta && <OktaSignInButton onClick={oktaLogin}/> }
                        {hasGoogle && <GmailSignInButton onClick={googleLogin}/> }
                        {hasGithub && <GithubSignInButton onClick={githubLogin}/> }
                        {hasLdap && <LdapSignInButton onClick={ldapLogin} /> }
                    </div>
                </div>
            </div>
        </div>

    );
}
