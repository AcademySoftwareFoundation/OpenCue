"use client";

import Image from "next/image";
import React from "react";
import { Button } from "@/components/ui/button"
import oktaicon from "../../public/okta-logo.png";
import { FaGithub } from "react-icons/fa"
import { FcGoogle } from "react-icons/fc"

export function OktaSignInButton({onClick}: {onClick: ()=> void}) {
    return (
        <Button
            variant="outline" 
            className="w-full bg-white flex justify-center items-center"
            aria-label="Sign in with Okta"
            onClick={onClick}
        >
            <Image className="px-5 block " src={oktaicon} alt="okta logo" height={30} />
        </Button>
    );
}

export function GmailSignInButton({onClick}: {onClick: ()=> void}) {
    return (
        <Button
            className="w-full"
            aria-label="Sign in with Google"
            onClick={onClick}
        >
            <FcGoogle className="mr-2" />
            Google
        </Button>
    );
}

export function GithubSignInButton({onClick}: {onClick: ()=> void}) {
    return (
        <Button
            className="w-full"
            aria-label="Sign in with Github"
            onClick={onClick}
        >
            <FaGithub className="mr-2" />
            Github
        </Button>
    );
}

export function CuewebRedirectButton({onClick}: {onClick: ()=> void}) {
    return (
        <Button
            className="w-full"
            aria-label="Go to CueWeb"
            onClick={onClick}
        >
            CueWeb Home
        </Button>
    );
}
