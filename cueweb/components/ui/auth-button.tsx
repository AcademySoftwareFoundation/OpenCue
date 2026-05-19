"use client";

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


import Image from "next/image";
import React from "react";
import { Button } from "@/components/ui/button"
import oktaicon from "../../public/okta-logo.png";
import { FaGithub, FaAddressBook } from "react-icons/fa"
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

export function LdapSignInButton({onClick}: {onClick: ()=> void}) {
    return (
        <Button
            className="w-full"
            aria-label="Sign in with Domain Account"
            onClick={onClick}
        >
            <FaAddressBook className="mr-2" />
            LDAP
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
