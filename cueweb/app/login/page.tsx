'use client'

// Custom authentication page
import { signIn } from "next-auth/react";
import React from "react";
import { useRouter } from "next/navigation";
import { GmailSignInButton, OktaSignInButton, GithubSignInButton, CuewebRedirectButton } from "@/components/ui/auth-button"
import CueWebIcon from "../../components/ui/cuewebicon";

export default function Page() {
    const router = useRouter();

    const oktaLogin = async () => {
        signIn("okta", { callbackUrl: "/"});
    };

    const googleLogin = async () => {
        signIn("google", { callbackUrl: "/"});
    };

    const githubLogin = async () => {
        signIn("github", { callbackUrl: "/"});
    };

    const cuewebRedirect = () => {
        router.push('/');
    };

    return (
        <div className="flex flex-col sm:flex-row w-full justify-center items-center h-screen bg-gray-100 
            dark:bg-gray-800">
            <div className="flex flex-col sm:flex-row sm:space-x-20 max-w-[100vh] bg-white dark:bg-black sm:px-16 
                sm:py-8 rounded-xl">
                <div className="flex flex-col justify-center items-center">
                <CueWebIcon/>
                </div>
                <div className="flex flex-col w-full space-y-3 ">
                    <div className="max-w-72 space-y-3">
                        {process.env.NEXT_PUBLIC_AUTH_PROVIDER &&
                            <h1 className="text-xl font-bold">Sign in to CueWeb</h1>
                        }
                        {!process.env.NEXT_PUBLIC_AUTH_PROVIDER &&
                            <CuewebRedirectButton onClick={cuewebRedirect}/>
                        }
                        {process.env.NEXT_PUBLIC_AUTH_PROVIDER && process.env.NEXT_PUBLIC_AUTH_PROVIDER.indexOf('okta') >= 0 && 
                            <OktaSignInButton onClick={oktaLogin}/> 
                        }
                        {process.env.NEXT_PUBLIC_AUTH_PROVIDER && process.env.NEXT_PUBLIC_AUTH_PROVIDER.indexOf('google') >= 0 && 
                            <GmailSignInButton onClick={googleLogin}/> 
                        }
                        {process.env.NEXT_PUBLIC_AUTH_PROVIDER && process.env.NEXT_PUBLIC_AUTH_PROVIDER.indexOf('github') >= 0 && 
                            <GithubSignInButton onClick={githubLogin} /> 
                        }
                    </div>
                </div>
            </div>
        </div>
        
    );
}
