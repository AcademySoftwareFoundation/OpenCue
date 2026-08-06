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

// Shown by middleware.ts when a signed-in user's groups do not satisfy
// CUEWEB_ALLOWED_GROUPS (or CUEWEB_ADMIN_GROUPS for an administration page).
import { signOut } from "next-auth/react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import CueWebIcon from "../../components/ui/cuewebicon";

export default function Page() {
  const router = useRouter();

  return (
    <div className="flex h-screen w-full flex-col items-center justify-center bg-gray-100 dark:bg-gray-800">
      <div className="flex max-w-[100vh] flex-col items-center space-y-4 rounded-xl bg-white px-16 py-10 text-center dark:bg-black">
        <CueWebIcon />
        <h1 className="text-xl font-bold">Access denied</h1>
        <p className="max-w-md text-sm text-muted-foreground">
          Your account is not authorized to access this area of CueWeb. If you
          believe this is a mistake, contact your OpenCue administrator.
        </p>
        <div className="flex gap-3">
          <Button variant="outline" onClick={() => router.push("/")}>
            Back to Monitor Jobs
          </Button>
          <Button variant="outline" onClick={() => signOut({ callbackUrl: "/login" })}>
            Sign out
          </Button>
        </div>
      </div>
    </div>
  );
}
